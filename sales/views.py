from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, F
from django.forms import inlineformset_factory
from django.urls import reverse_lazy
from django.contrib import messages

from django.utils import timezone
from datetime import timedelta

# We assume these models and forms are defined and imported correctly
from .models import Sale, SaleItem, InstallmentPlan, InstallmentPayment
from .forms import SaleForm, SaleItemForm, InstallmentPlanForm, InstallmentPaymentForm 
from products.models import Product # Crucial for stock management

# Define the SaleItem Formset (to add multiple products to one sale)
SaleItemFormSet = inlineformset_factory(
    Sale, 
    SaleItem, 
    fields=('product', 'quantity', 'unit_price', 'subtotal'),
    extra=1, 
    can_delete=True
)

# --- 1. Sale Views (Main Transactions) ---

class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'sales/sale_list.html'
    context_object_name = 'sales'
    ordering = ['-sale_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get the filter parameter from the URL (e.g., ?filter=today)
        time_filter = self.request.GET.get('filter')
        
        # Define current time boundaries
        now = timezone.now()
        
        if time_filter == 'today':
            # Filter for sales made today (from midnight to midnight)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            queryset = queryset.filter(sale_date__gte=start_of_day)

        elif time_filter == 'week':
            # Filter for sales made in the current week (e.g., last 7 days or start of week)
            # Using the last 7 days is often more reliable than timezone-dependent start-of-week logic
            last_week = now - timedelta(days=7)
            queryset = queryset.filter(sale_date__gte=last_week)

        elif time_filter == 'month':
            # Filter for sales made in the current calendar month
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            queryset = queryset.filter(sale_date__gte=start_of_month)
        
        # Add the current filter to context so the template can highlight the active button
        # 1. Initialize self.extra_context to an empty dictionary if it is None or unset.
        #    We must check if it is None, not just if it exists.
        if not hasattr(self, 'extra_context') or self.extra_context is None:
            self.extra_context = {}
            
        # 2. Safely add the filter variable
        self.extra_context['active_filter'] = time_filter
        
        # --- END OF CORRECTION ---
        
        return queryset.order_by(self.ordering[0])

class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = 'sales/sale_detail.html'
    context_object_name = 'sale'

# The complex view handling Sale, SaleItem Formset, and Stock Management
class SaleCreateView(LoginRequiredMixin, CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sales/sale_form.html'
    success_url = reverse_lazy('sales:sale_list')

    def get_context_data(self, **kwargs):
        # Pass the formsets to the template
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = SaleItemFormSet(self.request.POST, prefix='items')
            data['installment'] = InstallmentPlanForm(self.request.POST, prefix='installment')
        else:
            data['items'] = SaleItemFormSet(prefix='items')
            data['installment'] = InstallmentPlanForm(prefix='installment')
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items']
        installment_form = context['installment']
        
        # Crucial check: all components must be valid
        if items_formset.is_valid() and installment_form.is_valid():
            
            with transaction.atomic():
                # 1. Save the main Sale object
                self.object = form.save()
                total_sale_amount = 0
                
                # 2. Process Sale Items, Reduce Stock, and Calculate Total
                for item_form in items_formset:
                    if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                        sale_item = item_form.save(commit=False)
                        sale_item.sale = self.object
                        sale_item.save()
                        
                        total_sale_amount += sale_item.subtotal
                        
                        # --- STOCK MANAGEMENT (Core Logic) ---
                        product = sale_item.product
                        product.stock_quantity -= sale_item.quantity
                        product.save()
                
                # Update total_amount on the Sale object
                self.object.total_amount = total_sale_amount
                self.object.save()
                
                # 3. Handle Installment Plan
                if self.request.POST.get('is_installment_sale') == 'on':
                    installment_plan = installment_form.save(commit=False)
                    installment_plan.sale = self.object
                    installment_plan.save()
                    
                messages.success(self.request, f"Sale #{self.object.pk} created successfully and stock updated.")
                return redirect(self.get_success_url())
        else:
            # Re-render with errors if any form/formset is invalid
            return self.render_to_response(self.get_context_data(form=form))

# --- 2. Installment Views (Payment Tracking) ---

class InstallmentListView(LoginRequiredMixin, ListView):
    model = InstallmentPlan
    template_name = 'sales/installment_list.html'
    context_object_name = 'plans'

    def get_queryset(self):
        # Annotate queryset to calculate remaining balance
        return InstallmentPlan.objects.annotate(
            total_paid=Sum('payments__amount_paid')
        ).annotate(
            remaining_balance=F('sale__total_amount') - F('total_paid')
        ).all()

# View for Creating a Payment against an Installment Plan
class InstallmentPaymentCreateView(LoginRequiredMixin, CreateView):
    model = InstallmentPayment
    form_class = InstallmentPaymentForm
    template_name = 'sales/installment_pay_form.html'
    success_url = reverse_lazy('sales:installment_list')

    def get_initial(self):
        initial = super().get_initial()
        initial['installment_plan'] = get_object_or_404(InstallmentPlan, pk=self.kwargs['pk'])
        return initial
    
    def form_valid(self, form):
        payment = form.save(commit=False)
        # Link the payment to the correct plan based on the URL
        payment.installment_plan = get_object_or_404(InstallmentPlan, pk=self.kwargs['pk'])
        payment.save()
        messages.success(self.request, f"Payment of ${payment.amount_paid} recorded successfully.")
        return redirect(self.get_success_url())
    


@login_required
def sale_receipt_view(request, pk):
    """Generates a simplified, print-friendly receipt view for a Sale."""
    sale = get_object_or_404(Sale, pk=pk)
    
    context = {
        'sale': sale,
    }
    # Renders the new, simple receipt template
    return render(request, 'sales/sale_receipt.html', context)
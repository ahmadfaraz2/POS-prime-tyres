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
from decimal import Decimal

# We assume these models and forms are defined and imported correctly
from .models import Sale, SaleItem, InstallmentPlan, InstallmentPayment, Return, ReturnItem
from .forms import SaleForm, SaleItemForm, InstallmentPlanForm, InstallmentPaymentForm, ReturnCreateForm
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
        now = timezone.now()
        
        if time_filter == 'today':
            # Filter for sales made today (from midnight to midnight)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            queryset = queryset.filter(sale_date__gte=start_of_day)

        elif time_filter == 'week':
            # Filter for sales made in the current week (e.g., last 7 days or start of week)
            last_week = now - timedelta(days=7)
            queryset = queryset.filter(sale_date__gte=last_week)

        elif time_filter == 'month':
            # Filter for sales made in the current calendar month
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            queryset = queryset.filter(sale_date__gte=start_of_month)
        
        if not hasattr(self, 'extra_context') or self.extra_context is None:
            self.extra_context = {}
            
        # 2. Safely add the filter variable
        self.extra_context['active_filter'] = time_filter
        
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


@transaction.atomic
def process_return(request, sale_pk):
    # This is simplified. In a real app, you'd handle form submission here.
    
    # 1. Fetch the original sale and form data (e.g., which items and how many)
    sale = get_object_or_404(Sale, pk=sale_pk)
    
    # 2. Create the main Return object
    new_return = Return.objects.create(
        sale=sale,
        reason='DEFECTIVE', # Replace with form data
    )
    
    # Mock data for demonstration: return 1 unit of the first item
    first_sale_item = sale.items.first()
    
    if first_sale_item:
        # 3. Create the ReturnItem
        return_item = ReturnItem.objects.create(
            return_obj=new_return,
            product=first_sale_item.product,
            quantity=1, # Replace with form data
            unit_price=first_sale_item.unit_price
        )
        
        # 4. CRITICAL STEP: INCREMENT INVENTORY STOCK
        product = return_item.product
        
        # Use F-expression for safe, concurrent update
        from django.db.models import F
        product.stock_quantity = F('stock_quantity') + return_item.quantity
        product.save(update_fields=['stock_quantity'])
    
    # 5. Update the total refund amount (done automatically by ReturnItem save)
    
    # return redirect('sales:return_detail', pk=new_return.pk)
    return redirect('sales:sale_detail', pk=sale.pk)



@login_required
@transaction.atomic
def return_create_view(request, sale_pk):
    """
    Handles the creation of a Return and atomically updates inventory stock.
    Includes logic to refresh the Product instance after the database update.
    """
    # Fetch the sale with related items and products for efficiency
    sale = get_object_or_404(Sale.objects.prefetch_related('items__product'), pk=sale_pk)
    
    # ------------------------------------------------------------------
    # 1. CALCULATE AVAILABLE QUANTITIES (FOR TEMPLATE)
    # Get total quantity already returned for each product in this sale
    returned_quantities = (
        ReturnItem.objects
        .filter(return_obj__sale=sale)
        .values('product')
        .annotate(total_returned=Sum('quantity'))
    )
    returned_qty_map = {item['product']: item['total_returned'] for item in returned_quantities}

    return_items_data = []
    for item in sale.items.all():
        already_returned = returned_qty_map.get(item.product.pk, 0)
        available_to_return = item.quantity - already_returned
        
        return_items_data.append({
            'product_name': item.product.name,
            'max_quantity': item.quantity,
            'available_to_return': available_to_return, # Use this in template
            'unit_price': item.unit_price,
            'sale_item_id': item.id,
            'product_pk': item.product.pk,
        })
    # ------------------------------------------------------------------
        
    form = ReturnCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        
        new_return = form.save(commit=False)
        new_return.sale = sale
        new_return.save()
        
        total_refund = Decimal('0.00')
        successful_return_items = []
        
        # 2. Process all submitted return item quantities
        for item_data in sale.items.all():
            quantity_key = f'quantity_returned_{item_data.id}'
            
            try:
                quantity_returned = int(request.POST.get(quantity_key, 0))
            except ValueError:
                quantity_returned = 0
            
            already_returned = returned_qty_map.get(item_data.product.pk, 0)
            available_to_return = item_data.quantity - already_returned

            # Validation: Must be a positive quantity and not exceed remaining available quantity
            if quantity_returned > 0 and quantity_returned <= available_to_return:
                
                # 3. Create the ReturnItem object
                ReturnItem.objects.create(
                    return_obj=new_return,
                    product=item_data.product,
                    quantity=quantity_returned,
                    unit_price=item_data.unit_price,
                )
                
                # 4. CRITICAL FIX: INCREMENT INVENTORY STOCK ATOMICALLY
                # Use the imported Product model directly for the QuerySet update
                Product.objects.filter(pk=item_data.product.pk).update(
                    stock_quantity=F('stock_quantity') + quantity_returned
                )
                
                # 5. FIX: REFRESH THE PRODUCT INSTANCE TO SEE NEW STOCK VALUE
                # This ensures the stock is updated if you access it later in the view
                item_data.product.refresh_from_db()
                
                total_refund += (item_data.unit_price * Decimal(quantity_returned))
                successful_return_items.append(item_data)

        # Final checks and save for Return object
        if total_refund > 0:
            new_return.total_refund_amount = total_refund
            new_return.save(update_fields=['total_refund_amount'])
            
            # SUCCESS: Redirect to the detail page
            return redirect('sales:sale_detail', pk=sale.pk)
        
        else:
            # Clean up the empty Return record if no items were validly returned
            new_return.delete()
            form.add_error(None, "No items were selected for return or quantities exceeded the available amount.")

    context = {
        'form': form,
        'sale': sale,
        'return_items_data': return_items_data,
    }
    return render(request, 'sales/return_create.html', context)
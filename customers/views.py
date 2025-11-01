from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Customer

# List View
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'

# Create View
class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    template_name = 'customers/customer_form.html'
    fields = ['name', 'phone', 'email', 'address']
    success_url = reverse_lazy('customers:customer_list')

    def form_valid(self, form):
        messages.success(self.request, f"Customer '{form.instance.name}' created successfully.")
        return super().form_valid(form)

# Update View
class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    template_name = 'customers/customer_form.html'
    fields = ['name', 'phone', 'email', 'address']
    success_url = reverse_lazy('customers:customer_list')

    def form_valid(self, form):
        messages.info(self.request, f"Customer '{form.instance.name}' updated successfully.")
        return super().form_valid(form)

# Delete View
class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customers/customer_confirm_delete.html'
    context_object_name = 'customer'
    success_url = reverse_lazy('customers:customer_list')

    def form_valid(self, form):
        messages.error(self.request, f"Customer '{self.object.name}' deleted.")
        # Need to call delete directly in CBV DeleteView
        return super().delete(self.request)
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Product

# List View (Read)
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 15

# Create View (Create)
class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    template_name = 'products/product_form.html'
    fields = ['name', 'brand', 'size', 'type', 'price', 'stock_quantity', 'description']
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.name}' added successfully.")
        return super().form_valid(form)

# Update View (Update)
class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    template_name = 'products/product_form.html'
    fields = ['name', 'brand', 'size', 'type', 'price', 'stock_quantity', 'description']
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        messages.info(self.request, f"Product '{form.instance.name}' updated.")
        return super().form_valid(form)

# Delete View (Delete)
class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'products/product_confirm_delete.html'
    context_object_name = 'product'
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        messages.error(self.request, f"Product '{self.object.name}' deleted.")
        return super().delete(self.request)
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Product

from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.db.models import F
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Product, Cart, CartItem
# Import models we need from other apps
from customers.models import Customer 
from sales.models import Sale, SaleItem # Assuming we convert to Sale/SaleItem

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
    


# Utility function to get or create the user's active cart
def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user, defaults={'customer': None})
    return cart


# products/views.py (Cart Management View)
@require_POST
@login_required
def add_to_cart(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)
    cart = get_user_cart(request.user)
    
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        messages.error(request, "Invalid quantity.")
        return redirect('products:product_list')
    
    if quantity <= 0:
        messages.warning(request, "Please enter a valid quantity.")
        return redirect('products:product_list')

    # Find existing item or create new one
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        # If item already exists, increase quantity
        cart_item.quantity = F('quantity') + quantity
        cart_item.save()
        cart_item.refresh_from_db() # Refresh to see the new quantity

    messages.success(request, f"{quantity} x {product.name} added to cart.")
    return redirect('products:cart_detail') # Redirect to the cart view

# ... (Optional: View to remove item or clear cart) ...

@login_required
def remove_from_cart(request, item_pk):
    cart = get_user_cart(request.user)
    item = get_object_or_404(CartItem, pk=item_pk, cart=cart)
    item.delete()
    messages.warning(request, f"Item removed from cart.")
    return redirect('products:cart_detail')

@login_required
def clear_cart(request):
    cart = get_user_cart(request.user)
    cart.items.all().delete()
    messages.info(request, "Cart cleared.")
    return redirect('products:cart_detail')


# products/views.py (Cart Detail View)
@login_required
def cart_detail(request):
    cart = get_user_cart(request.user)
    customers = Customer.objects.all() # Used to select customer during checkout
    
    context = {
        'cart': cart,
        'items': cart.items.select_related('product'),
        'customers': customers,
    }
    return render(request, 'products/cart_detail.html', context)

# products/views.py (Checkout View)
@require_POST
@login_required
# @transaction.atomic # Ensure all database operations succeed or fail together
def cart_checkout(request):
    cart = get_user_cart(request.user)
    
    if not cart.items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('products:cart_detail')

    customer_id = request.POST.get('customer_id')
    payment_method = request.POST.get('payment_method', 'CASH') # Default to CASH
    
    customer = get_object_or_404(Customer, pk=customer_id)
    
    # 1. Create the main Sale object
    sale = Sale.objects.create(
        customer=customer,
        payment_method=payment_method,
        # total_amount will be updated below
    )

    total_amount = 0
    
    # 2. Process Cart Items, Create SaleItems, and Reduce Stock
    for cart_item in cart.items.all():
        product = cart_item.product
        quantity = cart_item.quantity
        
        # Perform final stock check
        if product.stock_quantity < quantity:
            messages.error(request, f"Insufficient stock for {product.name}. Only {product.stock_quantity} available.")
            raise Exception("Stock check failed during checkout.") # Rollback transaction
            
        # Create SaleItem
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            unit_price=product.price,
            subtotal=cart_item.subtotal
        )
        
        total_amount += cart_item.subtotal
        
        # Reduce Stock
        product.stock_quantity -= quantity
        product.save()
        
    # 3. Update Sale total and clear cart
    sale.total_amount = total_amount
    sale.save()
    cart.items.all().delete() # Clear the temporary cart

    messages.success(request, f"Checkout successful! Sale #{sale.pk} recorded for {customer.name}.")
    return redirect('sales:sale_detail', pk=sale.pk)
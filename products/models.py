from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from customers.models import Customer

User = get_user_model()


class Product(models.Model):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100)
    size = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., L, XL, 32/32")
    type = models.CharField(max_length=100, help_text="e.g., Shirt, Electronics, Grocery")
    description = models.TextField(blank=True)
    
    # Financial/Stock fields
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.brand})"

    def get_absolute_url(self):
        return reverse('products:product_list')
    


class Cart(models.Model):
    # Links the cart to the salesperson (logged-in user)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts') 
    # Optional: Link to a specific customer being served
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_total_items(self):
        """Calculates the total number of unique items in the cart."""
        return self.items.count()
    
    def get_total_price(self):
        """Calculates the total price of all items in the cart."""
        total = sum(item.subtotal for item in self.items.all())
        return total

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    @property
    def subtotal(self):
        return self.quantity * self.product.price
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
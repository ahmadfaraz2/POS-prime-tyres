from django.db import models
from django.urls import reverse

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
    



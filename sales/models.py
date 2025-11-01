from django.db import models
from django.urls import reverse
from customers.models import Customer
from products.models import Product
from django.db.models import Sum


CASH = 'CASH'
CARD = 'CARD'
TRANSFER = 'TRANSFER'
METHOD_CHOICES = [ 
    (CASH, 'Cash'),
    (CARD, 'Credit/Debit Card'),
    (TRANSFER, 'Bank Transfer'),
]

class Sale(models.Model):
    # Choices for payment type (Full vs. Installment)
    PAYMENT_CHOICES = [
        ('FULL', 'Full Payment'),
        ('INST', 'Installment Plan'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    sale_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=10, choices=METHOD_CHOICES, default=CASH) 
    payment_type = models.CharField(max_length=4, choices=PAYMENT_CHOICES, default='FULL')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) # Price at time of sale
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} on Sale {self.sale.id}"



class InstallmentPlan(models.Model):
    # OneToOne relationship with Sale, using related_name 'installment_plan'
    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name='installment_plan') 
    initial_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    num_installments = models.IntegerField(default=1)
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Plan for Sale {self.sale.id} ({self.num_installments} payments)"


class InstallmentPayment(models.Model):
    PAID = 'PAID'
    PENDING = 'PENDING'
    LATE = 'LATE'

    INSTALLMENT_STATUS_CHOICES = [
        (PAID, 'Paid'),
        (PENDING, 'Pending'),
        (LATE, 'Late'),
    ]
    # ForeignKey to the plan, using related_name 'payments'
    plan = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=7, choices=INSTALLMENT_STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"Payment {self.id} for Plan {self.plan.sale.id}"
    



# --- Sales Returns System ---

class Return(models.Model):
    RETURN_REASONS = [
        ('DEFECTIVE', 'Defective Product'),
        ('WRONG_ITEM', 'Wrong Item Shipped'),
        ('CUSTOMER_CHANGE', 'Customer Changed Mind'),
        ('OTHER', 'Other'),
    ]

    sale = models.ForeignKey(
        'Sale', 
        on_delete=models.PROTECT, 
        related_name='returns',
        help_text="The original sale transaction being returned."
    )
    return_date = models.DateTimeField(auto_now_add=True)
    total_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reason = models.CharField(max_length=50, choices=RETURN_REASONS, default='CUSTOMER_CHANGE')
    
    def __str__(self):
        return f"Return #{self.id} for Sale #{self.sale.id}"
    
    def calculate_total(self):
        """Calculates and updates the total refund amount based on items."""
        total = self.items.aggregate(Sum('subtotal_refund'))['subtotal_refund__sum'] or 0.00
        self.total_refund_amount = total
        self.save()


class ReturnItem(models.Model):
    return_obj = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity = models.IntegerField(help_text="Quantity of this product being returned.")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price at time of original sale.")
    subtotal_refund = models.DecimalField(max_digits=10, decimal_places=2, help_text="Calculated amount to refund for this item.")

    def __str__(self):
        return f"{self.quantity} returned of {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Calculate the subtotal refund before saving
        self.subtotal_refund = self.quantity * self.unit_price
        super().save(*args, **kwargs)

        # After saving the item, update the parent Return's total
        self.return_obj.calculate_total()
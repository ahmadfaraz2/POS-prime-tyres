from django.db import models
from django.urls import reverse
from customers.models import Customer
from products.models import Product

# Constants for payment status

class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('FULL', 'Full Payment'),
        ('INST', 'Installment Plan'),
    ]
    INSTALLMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('LATE', 'Late'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    sale_date = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=4, choices=PAYMENT_CHOICES)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"Sale {self.id} to {self.customer.name}"

    def get_absolute_url(self):
        return reverse('sales:sale_detail', kwargs={'pk': self.pk})

    @property
    def is_installment(self):
        return self.payment_type == 'INST'


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) # Price at time of sale
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} on Sale {self.sale.id}"

    # Important: Logic to decrement stock will happen in the View/Form processing layer, not here.


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
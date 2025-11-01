from django import forms
from django.urls import reverse
from django.forms.models import inlineformset_factory
from .models import Sale, SaleItem, InstallmentPlan, Product, InstallmentPayment, Return, ReturnItem

# Form for the main Sale details

# Define the payment choices as constants first
class SaleForm(forms.ModelForm):
    # Use a RadioSelect widget for clarity between Full and Installment payment
    payment_type = forms.ChoiceField(
        choices=Sale.PAYMENT_CHOICES, 
        widget=forms.RadioSelect(attrs={'class': 'inline-block mr-4'})
    )

    class Meta:
        model = Sale
        fields = ['customer', 'payment_type']
        # Note: total_amount and sale_date are calculated/auto-added

# Form for an individual SaleItem
class SaleItemForm(forms.ModelForm):
    # Display the current product price for reference in the form
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.initial.get('product'):
            # Set the unit_price field to read-only based on the product's current price
            self.fields['unit_price'].initial = Product.objects.get(pk=self.initial['product']).price
            self.fields['unit_price'].widget.attrs['readonly'] = 'readonly' # User shouldn't change this manually
        
        # Add 'data-product-price' to the product field for JavaScript to read the price on change
        self.fields['product'].widget.attrs['data-product-price-url'] = reverse('sales:get_product_price')

    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'unit_price']
        # Note: subtotal is calculated via JavaScript/View logic

# Formset for handling multiple SaleItems
# extra=1 means one empty form is shown by default
SaleItemFormSet = inlineformset_factory(
    Sale, # Parent model
    SaleItem, # Child model
    form=SaleItemForm,
    fields=['product', 'quantity', 'unit_price'],
    extra=1,
    can_delete=True
)

# Form for Installment Plan details (created only if payment_type is 'INST')
class InstallmentPlanForm(forms.ModelForm):
    class Meta:
        model = InstallmentPlan
        fields = ['initial_payment', 'num_installments', 'installment_amount', 'start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }

# Form for making an individual payment
class InstallmentPaymentForm(forms.ModelForm):
    class Meta:
        model = InstallmentPayment
        fields = ['amount_paid', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly'}),
        }


class ReturnCreateForm(forms.ModelForm):
    """
    Form for creating the main Return object, primarily selecting the reason.
    """
    class Meta:
        model = Return
        # We only need the reason from the form, sale is passed in the view
        fields = ['reason'] 
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-control'}),
        }
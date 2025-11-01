from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='add_class')
def add_class(value, css_class):
    """
    Adds a CSS class to a Django form field.
    Usage: {{ form.username|add_class:"tailwind-class-list" }}
    """
    return value.as_widget(attrs={'class': css_class})



@register.filter(name='dict_sum')
def dict_sum(dictionary):
    """Sums the values of a dictionary."""
    if not isinstance(dictionary, dict):
        return 0
    # Assumes dictionary values are numeric
    return sum(dictionary.values())



@register.filter(name='sub')
def sub(value, arg):
    """Subtracts the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        # Handle cases where value or arg aren't numbers gracefully
        return ''
    


@register.filter
def get_total_refunds(returns_queryset):
    """
    Calculates the sum of total_refund_amount for a queryset of Return objects.
    """
    total = Decimal('0.00')
    
    # Ensure returns_queryset is iterable and contains return objects
    if returns_queryset is not None:
        for return_obj in returns_queryset:
            # Safely add the total_refund_amount
            total += return_obj.total_refund_amount
    
    return total
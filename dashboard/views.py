from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from datetime import date
# Import models from other apps
from customers.models import Customer
from products.models import Product
from sales.models import Sale, InstallmentPlan

@login_required
def dashboard_view(request):
    # --- 1. Core Financial and Entity Metrics ---
    
    # Total Revenue (All Time)
    total_revenue_query = Sale.objects.aggregate(total=Sum('total_amount'))
    total_revenue = total_revenue_query['total'] or 0.00
    
    # Today's Sales Count
    today = date.today()
    today_sales_count = Sale.objects.filter(sale_date__date=today).count()
    
    # Entity Counts
    total_products = Product.objects.count()
    total_customers = Customer.objects.count()
    
    # --- 2. Advanced Financial Metrics (Outstanding Balance) ---
    
    # Calculate the remaining balance for all installment plans
    outstanding_plans = InstallmentPlan.objects.annotate(
        # Calculate total paid by summing amounts from all related payments
        total_paid=Sum('payments__amount_paid')
    ).annotate(
        # Calculate remaining balance: Sale Total - Total Paid (coalesce total_paid to 0 if null)
        remaining_balance=F('sale__total_amount') - F('total_paid')
    ).filter(
        remaining_balance__gt=0 # Filter only plans that still owe money
    )
    
    outstanding_installments_count = outstanding_plans.count()
    # Sum the remaining_balance from the filtered set to get the total amount owed
    outstanding_balance_sum = outstanding_plans.aggregate(total_outstanding=Sum('remaining_balance'))['total_outstanding'] or 0.00
    
    # --- 3. Inventory Warnings ---
    
    # Low Stock Warning (products with stock between 1 and 9)
    low_stock_count = Product.objects.filter(stock_quantity__lt=10, stock_quantity__gt=0).count()
    
    context = {
        'total_revenue': total_revenue,
        'today_sales_count': today_sales_count,
        'total_products': total_products,
        'total_customers': total_customers,
        'outstanding_installments_count': outstanding_installments_count,
        'outstanding_balance_sum': outstanding_balance_sum,
        'low_stock_count': low_stock_count,
    }
    
    return render(request, 'dashboard/dashboard.html', context)
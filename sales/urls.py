from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Sale List, Creation, and Detail
    path('', views.SaleListView.as_view(), name='sale_list'),
    path('create/', views.SaleCreateView.as_view(), name='sale_create'), 
    path('<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    
    # Installment and Payment Flow
    path('installments/', views.InstallmentListView.as_view(), name='installment_list'),
    # Route to pay against a specific InstallmentPlan (uses its PK)
    path('installments/<int:pk>/pay/', views.InstallmentPaymentCreateView.as_view(), name='installment_pay'),
]
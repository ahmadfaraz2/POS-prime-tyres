from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Sale List, Creation, and Detail
    path('', views.SaleListView.as_view(), name='sale_list'),
    path('create/', views.SaleCreateView.as_view(), name='sale_create'), 
    path('<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('<int:pk>/receipt/', views.sale_receipt_view, name='sale_receipt'),
    path('<int:sale_pk>/return/create/', views.return_create_view, name='return_create'),
    # Installment and Payment Flow
    path('installments/', views.InstallmentListView.as_view(), name='installment_list'),
    # Route to pay against a specific InstallmentPlan (uses its PK)
    path('installments/<int:pk>/pay/', views.InstallmentPaymentCreateView.as_view(), name='installment_pay'),
]
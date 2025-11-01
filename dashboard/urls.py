from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # This is the single entry point for the dashboard
    path('', views.dashboard_view, name='dashboard_view'),
]
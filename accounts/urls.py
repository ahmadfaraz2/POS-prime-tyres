from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth Views
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    # Note: Logout requires a POST request by default for security
    path('logout/', views.logout_view, name='logout'),
    # Root path redirects to login if not authenticated (handled by LOGIN_URL in settings)
]
from django.urls import path
from .views import SuperAdminDashboard
urlpatterns = [
    path('admin-dashboard/', SuperAdminDashboard.as_view(), name="super_admin_dashboard")
]
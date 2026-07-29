from django.urls import path
from .views import SuperAdminDashboard, branch_detail
urlpatterns = [
    path('admin-dashboard/', SuperAdminDashboard.as_view(), name="super_admin_dashboard"),
    path('branch/<int:pk>/', branch_detail, name='branch_detail'),
]
from django.urls import path
from .views import SuperAdminDashboard, BranchDetailView
urlpatterns = [
    path('admin-dashboard/', SuperAdminDashboard.as_view(), name="super_admin_dashboard"),
    path('branch/<int:branch_id>/', BranchDetailView.as_view(), name='branch_detail'),
]
from django.urls import path
from .views import (
    BranchDetailView,
    MonthlyAnalyticsView,
    SuperAdminDashboard,
    employee_dashboard,
)
urlpatterns = [
    path('admin-dashboard/', SuperAdminDashboard.as_view(), name="super_admin_dashboard"),
    path('monthly-analytics/', MonthlyAnalyticsView.as_view(), name="monthly_analytics"),
    path('branch/<int:branch_id>/', BranchDetailView.as_view(), name='branch_detail'),
    path('employee-dashboard/', employee_dashboard, name='employee_dashboard'),
]
from django.urls import path
from . import views
urlpatterns = [
    path('', views.login_view, name='login'),
    path('attendance_check_in/', views.attendance_check_in, name='attendance_check_in'),
    path('branch-manager-dashboard/', views.branch_manager_dashboard, name='branch_manager_dashboard'),
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
]


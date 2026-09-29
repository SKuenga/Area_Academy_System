from django.urls import path
from . import views
urlpatterns = [
    path('', views.login_view, name='login'),
    path('attendance_check_in/', views.attendance_check_in, name='attendance_check_in'),
    path('passkeys/enroll/', views.passkey_enrollment, name='passkey_enrollment'),
    path(
        'passkeys/enroll/options/',
        views.passkey_enrollment_options,
        name='passkey_enrollment_options',
    ),
    path(
        'passkeys/enroll/complete/',
        views.passkey_enrollment_complete,
        name='passkey_enrollment_complete',
    ),
    path(
        'passkeys/login/complete/',
        views.passkey_login_complete,
        name='passkey_login_complete',
    ),
    path('branch-manager-dashboard/', views.branch_manager_dashboard, name='branch_manager_dashboard'),
]

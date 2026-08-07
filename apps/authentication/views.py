from .forms import LoginForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import HttpResponse, HttpResponseForbidden
from .models import User
from apps.branch.models import Branch
from apps.authentication.utils import haversion_algo
from django.utils import timezone
from apps.attendance.models import Attendance
from .services.attendance_status_service import status_check


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            role = getattr(user, 'role', None)
            if role == User.Role.SUPER_ADMIN:
                return redirect('super_admin_dashboard')
            else: 
                return redirect("attendance_check_in")
    else:
        form = LoginForm()
    return render(request, 'authentication/login.html', {'form': form})


@login_required
def attendance_check_in(request):
    if request.method == "POST":
        user_latitude = request.POST.get('latitude')
        user_longitude = request.POST.get('longitude')
        branches = list(Branch.objects.all())

        if not user_latitude or not user_longitude:
            return render(request, "authentication/attendance_check_in.html", {"error": "Location coordinates were not received."})

        if not branches:
            return render(request, "authentication/attendance_check_in.html", {"error": "No branches are configured yet."})

        try:
            nearest_branch, distance = haversion_algo.check_distance(user_latitude, user_longitude, branches)
        except (TypeError, ValueError):
            return render(request, "authentication/attendance_check_in.html", {"error": "Invalid location coordinates received."})
        
        if distance > nearest_branch.geofencing_radius:
            return render(request, "authentication/attendance_check_in.html", {"error": "You are outside the allowed radius."})

        user_check_in_time = timezone.now()
        status_returned = status_check(
            user_check_in_time=user_check_in_time,
            user_branch=nearest_branch,
            username=request.user.username,
        )

        attendance_record = Attendance.objects.filter(
            user=request.user,
            check_in_time__date=timezone.localdate(user_check_in_time),
        ).order_by("check_in_time").first()

        if attendance_record:
            attendance_record.branch = nearest_branch
            attendance_record.status = status_returned
            attendance_record.is_verified = True
            attendance_record.save(update_fields=["branch", "status", "is_verified"])
        else:
            Attendance.objects.create(
                user=request.user,
                branch=nearest_branch,
                status=status_returned,
                is_verified=True,
            )

        if request.user.role == User.Role.BRANCH_MANAGER:
            return redirect("branch_manager_dashboard")
        else:
            return redirect("employee_dashboard")

    return render(request, 'authentication/attendance_check_in.html')


@login_required
def branch_manager_dashboard(request):
    if request.user.role != User.Role.BRANCH_MANAGER:
        return HttpResponseForbidden("Only branch managers can access this dashboard.")

    if not request.user.branch_id:
        return HttpResponse(
            "Your account is not assigned to a branch yet. Please contact the administrator.",
            status=400,
        )

    return redirect("branch_detail", branch_id=request.user.branch_id)




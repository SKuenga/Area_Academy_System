from .forms import LoginForm
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.http import HttpResponse
from django.shortcuts import redirect
from .models import User
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            role = getattr(user, 'role', None)
            if role == User.Role.SUPER_ADMIN:
                return redirect('super_admin_dashboard')
            elif role == User.Role.BRANCH_MANAGER:
                return HttpResponse("Branch Manager login successful")
            else:
                return HttpResponse("Login successful")
    else:
        form = LoginForm()
    return render(request, 'authentication/login.html', {'form': form})
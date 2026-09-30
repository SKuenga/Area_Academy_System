from django.contrib import admin
from .models import Class_Session

@admin.register(Class_Session)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ('session_name', 'day', 'start_time', 'end_time', 'instructor', 'branch')
    list_filter = ('instructor', 'branch')

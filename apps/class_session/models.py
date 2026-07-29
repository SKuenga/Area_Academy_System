from django.db import models
from apps.authentication.models import User
from apps.branch.models import Branch
# Create your models here.
class Class_Session(models.Model):
    session_name = models.CharField(max_length=100)
    day = models.CharField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey(Branch, on_delete = models.CASCADE)
    
    def __str__(self):
        pass
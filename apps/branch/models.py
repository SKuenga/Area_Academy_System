from django.db import models

class Branch(models.Model):
    name = models.CharField(max_length=255, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    geofencing_radius = models.PositiveIntegerField(
        help_text="Radius in meters"
    )

    def __str__(self):
        return self.name
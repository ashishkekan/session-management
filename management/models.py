from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

STATUSES = [
    ("Pending", "Pending"),
    ("Completed", "Completed"),
    ("Cancelled", "Cancelled"),
]


class SessionTopic(models.Model):
    topic = models.CharField(max_length=255)
    conducted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=50,
        choices=STATUSES,
        default="Pending",
    )


class ExternalTopic(models.Model):
    coming_soon = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Learning Topic"
    )
    created_at = models.DateField(auto_now_add=True, null=True, blank=True)

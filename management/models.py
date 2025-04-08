from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class SessionTopic(models.Model):
    topic = models.CharField(max_length=255)
    conducted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=50,
        choices=[("Pending", "Pending"), ("Completed", "Completed")],
        default="Pending",
    )

    def __str__(self):
        return self.topic

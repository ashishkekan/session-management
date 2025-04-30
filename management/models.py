from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

STATUSES = [
    ("Pending", "Pending"),
    ("Completed", "Completed"),
    ("Cancelled", "Cancelled"),
]


class SessionTopic(models.Model):
    """
    Represents a session topic for a learning event.

    Fields:
        topic (CharField): The name of the topic being discussed.
        conducted_by (ForeignKey): The user who is conducting the session.
        date (DateTimeField): The date and time when the session is scheduled to occur.
        status (CharField): The status of the session (e.g., Pending, Completed, Cancelled).
        cancelled_reason (CharField, optional): The reason for cancellation, if applicable.
    """
    topic = models.CharField(max_length=255)
    conducted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=50,
        choices=STATUSES,
        default="Pending",
    )
    cancelled_reason = models.CharField(max_length=255, null=True, blank=True, verbose_name="Cancelled Reason")

    def __str__(self):
        """
        String representation of the session topic, showing the topic name and its status.
        """
        return f"{self.topic} ' - ' {self.status}"


class ExternalTopic(models.Model):
    """
    Represents an external topic that is upcoming or being offered externally for learning.

    Fields:
        coming_soon (CharField, optional): The name of the topic that is upcoming.
        url (URLField, optional): A URL link to an external resource for the topic.
        created_at (DateField): The date when the external topic was created.
        is_active (BooleanField): A flag indicating whether the external topic is active.
    """
    coming_soon = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Learning Topic"
    )

    url = models.URLField(
        max_length=2000,
        null=True,
        blank=True,
        verbose_name="URL"
    )

    created_at = models.DateField(auto_now_add=True, null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True)

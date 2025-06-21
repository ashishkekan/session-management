from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

STATUSES = [
    ("Pending", "Pending"),
    ("Completed", "Completed"),
    ("Cancelled", "Cancelled"),
]

PLACE_CHOICES = [
    ("--- Select Place ---", "--- Select Place ---"),
    ("Customer Lounge", "Customer Lounge"),
    ("Auditorium", "Auditorium"),
]

# management/models.py
ROLES = [
    ('Employee', 'Employee'),
    ('HR', 'HR'),
    ('Manager', 'Manager'),
]

class Department(models.Model):
    """
    Represents a department within the organization.

    Fields:
        name (CharField): The name of the department.
        description (TextField, optional): A brief description of the department.
        created_at (DateTimeField): The date and time when the department was created.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        String representation of the department, showing the department name.
        """
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=50, choices=ROLES, default='Employee')

    def __str__(self):
        return f"{self.user.username} - {self.department.name if self.department else 'No Department'} - {self.role}"

class SessionTopic(models.Model):
    """
    Represents a session topic for a learning event.

    Fields:
        topic (CharField): The name of the topic being discussed.
        conducted_by (ForeignKey): The user who is conducting the session.
        date (DateTimeField): The date and time when the session is scheduled to occur.
        status (CharField): The status of the session (e.g., Pending, Completed, Cancelled).
        place (CharField): The location where the session will take place.
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
    place = models.CharField(
        max_length=50,
        choices=PLACE_CHOICES,
        default="--- Select Place ---",
    )
    cancelled_reason = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Cancelled Reason"
    )

    def __str__(self):
        """
        String representation of the session topic, showing the topic name and its status.
        """
        return f"{self.topic} - {self.status}"


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
    url = models.URLField(max_length=2000, null=True, blank=True, verbose_name="URL")
    created_at = models.DateField(auto_now_add=True, null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        """
        String representation of the external topic, showing the topic name or 'No Topic' if not set.
        """
        return self.coming_soon or "No Topic"


# management/models.py
ACTION_TYPES = [
    ('CREATE', 'Create'),
    ('UPDATE', 'Update'),
    ('DELETE', 'Delete'),
    ('LOGIN', 'Login'),
    ('LOGOUT', 'Logout'),
]

class RecentActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    details = models.JSONField(null=True, blank=True)  # Store additional data

    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.description[:30]}"


class CompanyProfile(models.Model):
    name = models.CharField(max_length=100, default="SessionXpert")
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profiles"
        
        
# management/models.py
class SetupChecklist(models.Model):
    task = models.CharField(max_length=100)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task} - {'Completed' if self.completed else 'Pending'}"
    

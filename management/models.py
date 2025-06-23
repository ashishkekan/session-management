from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Company(models.Model):
    """
    Represents a company in the system.

    Fields:
        name (CharField): The name of the company.
        logo (ImageField): The company's logo.
        created_at (DateTimeField): The date and time when the company was created.
    """

    name = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


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


class Department(models.Model):
    """
    Represents a department within the organization.

    Fields:
        name (CharField): The name of the department.
        description (TextField, optional): A brief description of the department.
        created_at (DateTimeField): The date and time when the department was created.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    # Making company non-nullable for Department
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'company') # Department name should be unique within a company

    def __str__(self):
        """
        String representation of the department, showing the department name and company.
        """
        return f"{self.name} ({self.company.name})"


class UserProfile(models.Model):
    """
    Extends the User model to include a department.

    Fields:
        user (OneToOneField): The associated user.
        department (ForeignKey): The department the user belongs to.
    """

    USER_ROLE_CHOICES = [
        ('ADMIN', 'Company Admin'),
        ('MANAGER', 'Manager'),
        ('EMPLOYEE', 'Employee'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=50, choices=USER_ROLE_CHOICES, null=True, blank=True)


    def __str__(self):
        """
        String representation of the user profile, showing the username and department.
        """
        company_name = self.company.name if self.company else "No Company"
        department_name = self.department.name if self.department else "No Department"
        role_display = self.get_role_display() if self.role else "No Role"
        return f"{self.user.username} - {company_name} - {department_name} ({role_display})"


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
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='sessions') # Making non-nullable
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
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='external_topics') # Making non-nullable
    created_at = models.DateField(auto_now_add=True, null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        """
        String representation of the external topic, showing the topic name or 'No Topic' if not set.
        """
        return self.coming_soon or "No Topic"


class RecentActivity(models.Model):
    """
    Represents recent activities performed by users.

    Fields:
        user (ForeignKey): The user who performed the activity.
        description (TextField): A description of the activity.
        timestamp (DateTimeField): The date and time when the activity occurred.
        read (BooleanField): A flag indicating whether the activity has been read.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='activities', null=True) # Allow null temporarily

    def __str__(self):
        """
        String representation of the activity, showing the username and a snippet of the description.
        """
        return f"{self.user.username} - {self.description[:30]}"

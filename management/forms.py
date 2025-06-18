from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.forms import DateTimeInput

from .models import Department, ExternalTopic, SessionTopic, UserProfile


class DepartmentForm(forms.ModelForm):
    """
    Form for creating and editing Department instances.
    """

    class Meta:
        model = Department
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "custom-input"})


class SessionTopicForm(forms.ModelForm):
    """
    Form for creating and editing SessionTopic instances.
    Includes custom widgets for date fields and filters conducted_by
    to exclude staff users.
    """

    class Meta:
        model = SessionTopic
        fields = [
            "topic",
            "conducted_by",
            "date",
            "status",
            "place",
            "cancelled_reason",
        ]
        widgets = {
            "date": DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            )
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["conducted_by"].queryset = User.objects.exclude(is_staff=True)
        self.fields["conducted_by"].label_from_instance = (
            lambda obj: f"{obj.first_name} {obj.last_name} ({obj.username})"
        )
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M"]

        for field in self.fields.values():
            field.widget.attrs.update({"class": "custom-input"})


class UserCreationForm(forms.ModelForm):
    """
    Form for creating a new User, including fields for setting a password
    and selecting a department.
    """

    password = forms.CharField(widget=forms.PasswordInput)
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(), required=True
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "custom-input"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user, department=self.cleaned_data["department"]
            )
        return user


class UserEditForm(forms.ModelForm):
    """
    Form for editing an existing User, including department field with custom styling.
    """

    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=True,
        empty_label="Select a department",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If editing an existing user who already has a department
        if self.instance and hasattr(self.instance, "userprofile"):
            current_dept = self.instance.userprofile.department
            if current_dept:
                # Lock the dropdown to only the current department
                self.fields["department"].queryset = Department.objects.filter(
                    id=current_dept.id
                )
                self.fields["department"].initial = current_dept
                self.fields["department"].disabled = True  # makes field non-editable

        # Apply styling
        for field in self.fields.values():
            field.widget.attrs.update({"class": "custom-input"})

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            # If department field is disabled, use initial (since cleaned_data won't include disabled fields)
            profile.department = (
                self.cleaned_data.get("department") or self.fields["department"].initial
            )
            profile.save()
        return user


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom form for changing the user's password, with custom placeholders
    and styling for the old and new password fields.
    """

    old_password = forms.CharField(
        label="Old Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter old password"}
        ),
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter new password"}
        ),
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm new password"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "custom-input"})


class ExternalTopicForm(forms.ModelForm):
    """
    Form for creating and editing ExternalTopic instances, including fields
    for the 'coming_soon' status and 'url' for the external topic.
    """

    class Meta:
        model = ExternalTopic
        fields = ["coming_soon", "url"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "custom-input"})


class SessionUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Upload Excel File",
        help_text="Upload an Excel file (.xlsx) containing session data.",
        widget=forms.FileInput(attrs={"accept": ".xlsx"}),
    )

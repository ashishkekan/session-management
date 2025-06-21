from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.forms import DateTimeInput

from management.models import CompanyProfile, Department, ExternalTopic, SessionTopic, UserProfile


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

# management/models.py
ROLES = [
    ('Employee', 'Employee'),
    ('HR', 'HR'),
    ('Manager', 'Manager'),
]

# management/forms.py
class UserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
    is_staff = forms.BooleanField(required=False, label="Is Admin?")
    role = forms.ChoiceField(choices=ROLES, required=True)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password", "is_staff", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "custom-input"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_staff = self.cleaned_data["is_staff"]
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                department=self.cleaned_data["department"],
                role=self.cleaned_data["role"]
            )
        return user

class UserEditForm(forms.ModelForm):
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
    role = forms.ChoiceField(choices=ROLES, required=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, "userprofile"):
            current_dept = self.instance.userprofile.department
            current_role = self.instance.userprofile.role
            if current_dept:
                self.fields["department"].queryset = Department.objects.filter(id=current_dept.id)
                self.fields["department"].initial = current_dept
                self.fields["department"].disabled = True
            self.fields["role"].initial = current_role
            self.fields["role"].disabled = True
        for field in self.fields.values():
            field.widget.attrs.update({"class": "custom-input"})

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data.get("department") or self.fields["department"].initial
            profile.role = self.cleaned_data["role"]
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


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ['name', 'logo', 'contact_email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'custom-input'})
            
            
# management/forms.py
class InviteAdminForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}))
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'custom-input'})


# management/forms.py
class SupportForm(forms.Form):
    subject = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter subject'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your issue'}))
    priority = forms.ChoiceField(choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'custom-input'})
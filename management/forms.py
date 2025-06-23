from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.forms import DateTimeInput

from management.models import (
    Company,
    Department,
    ExternalTopic,
    SessionTopic,
    UserProfile,
)


class CompanyForm(forms.ModelForm):
    """
    Form for creating and editing Company instances.
    """

    class Meta:
        model = Company
        fields = ["name", "logo"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'logo':
                # ClearableFileInput doesn't play well with 'custom-input' for styling by default
                # but we can keep form-control-file for Bootstrap-like styling
                continue
            field.widget.attrs.update({"class": "custom-input"})


class DepartmentForm(forms.ModelForm):
    """
    Form for creating and editing Department instances.
    """

    class Meta:
        model = Department
        fields = ["name", "description", "company"] # Added company
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            # Company will be hidden or read-only depending on user role in the view
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None) # Get user if passed
        super().__init__(*args, **kwargs)

        if self.user and not self.user.is_staff: # For non-staff, company is fixed
            if hasattr(self.user, 'userprofile') and self.user.userprofile.company:
                self.fields['company'].queryset = Company.objects.filter(pk=self.user.userprofile.company.pk)
                self.fields['company'].initial = self.user.userprofile.company
                self.fields['company'].widget = forms.HiddenInput() # Or forms.Select(attrs={'readonly': 'readonly'})
            else:
                # Handle case where non-staff user has no company (should not happen ideally)
                self.fields['company'].queryset = Company.objects.none()
        elif self.user and self.user.is_staff: # Staff can choose company
             self.fields['company'].queryset = Company.objects.all()
        else: # No user context (e.g. admin direct add)
            self.fields['company'].queryset = Company.objects.all()


        for field_name, field in self.fields.items():
            if field_name != 'company' or (self.user and self.user.is_staff): # Apply custom-input unless it's a hidden company field
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
            ),
            # Company will be hidden or selectable based on user role
        }
        # Add 'company' to fields
        fields = [
            "topic",
            "conducted_by",
            "company",
            "date",
            "status",
            "place",
            "cancelled_reason",
        ]


    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        # Filter 'conducted_by' to users within the same company if user is not staff
        # or if a company is already set on the instance (editing)
        company_context = None
        if hasattr(self.user, 'userprofile') and self.user.userprofile.company:
            company_context = self.user.userprofile.company

        if self.instance and self.instance.pk and self.instance.company:
             company_context = self.instance.company

        if company_context:
            self.fields["conducted_by"].queryset = User.objects.filter(
                userprofile__company=company_context, is_staff=False
            ).select_related('userprofile')
        elif self.user and self.user.is_staff: # Staff creating a session can pick any non-staff user initially
            self.fields["conducted_by"].queryset = User.objects.exclude(is_staff=True)
        else: # Non-staff, no company context (should ideally not happen for creation)
            self.fields["conducted_by"].queryset = User.objects.none()


        self.fields["conducted_by"].label_from_instance = (
            lambda obj: f"{obj.first_name} {obj.last_name} ({obj.username})"
        )
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M"]

        # Handle Company field based on user type
        if self.user and not self.user.is_staff:
            if hasattr(self.user, 'userprofile') and self.user.userprofile.company:
                self.fields['company'].queryset = Company.objects.filter(pk=self.user.userprofile.company.pk)
                self.fields['company'].initial = self.user.userprofile.company
                self.fields['company'].widget = forms.HiddenInput()
            else:
                self.fields['company'].queryset = Company.objects.none()
        elif self.user and self.user.is_staff:
            self.fields['company'].queryset = Company.objects.all()
            if company_context: # If editing, default to instance's company
                 self.fields['company'].initial = company_context
        else: # No user context
            self.fields['company'].queryset = Company.objects.all()


        for field_name, field in self.fields.items():
            if field_name != 'company' or (self.user and self.user.is_staff):
                field.widget.attrs.update({"class": "custom-input"})


class UserCreationForm(forms.ModelForm):
    """
    Form for creating a new User, including fields for setting a password
    and selecting a department.
    """

    password = forms.CharField(widget=forms.PasswordInput)
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=True,
        empty_label="Select a company"
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),  # Populate based on selected company
        required=False # Or True if department is mandatory; adjust based on requirements
    )
    role = forms.ChoiceField(
        choices=UserProfile.USER_ROLE_CHOICES,
        required=True
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password", "company", "department", "role"]

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None) # User performing the action
        super().__init__(*args, **kwargs)

        request_user_profile = getattr(self.request_user, 'userprofile', None)

        if self.request_user and not self.request_user.is_staff and request_user_profile and request_user_profile.role == 'ADMIN': # Company admin creating user
            user_company = request_user_profile.company
            if user_company:
                self.fields['company'].queryset = Company.objects.filter(pk=user_company.pk)
                self.fields['company'].initial = user_company
                self.fields['company'].widget = forms.HiddenInput() # Company is fixed
                self.fields['department'].queryset = Department.objects.filter(company=user_company).order_by('name')
                # Company Admin can assign Manager or Employee roles
                self.fields['role'].choices = [choice for choice in UserProfile.USER_ROLE_CHOICES if choice[0] != 'ADMIN']
            else: # Should not happen: company admin without company
                self.fields['company'].queryset = Company.objects.none()
                self.fields['department'].queryset = Department.objects.none()
                self.fields['role'].choices = []
        elif self.request_user and self.request_user.is_staff: # Super admin creating user
            self.fields['company'].queryset = Company.objects.all().order_by('name')
            self.fields['department'].queryset = Department.objects.all().order_by('company__name', 'name')
            self.fields['role'].choices = UserProfile.USER_ROLE_CHOICES # Super admin can assign any role
        else: # Other users (e.g. manager, employee) should not be able to access this form for creation
            self.fields['company'].queryset = Company.objects.none()
            self.fields['department'].queryset = Department.objects.none()
            self.fields['role'].choices = []


        for field_name, field in self.fields.items():
            if field_name != 'company' or (self.request_user and self.request_user.is_staff):
                 field.widget.attrs.update({"class": "custom-input"})
            if field_name == 'role' and not (self.request_user and (self.request_user.is_staff or (request_user_profile and request_user_profile.role == 'ADMIN'))):
                field.widget = forms.HiddenInput() # Hide role if not admin


    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            # UserProfile creation/update should handle company and department
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'company': self.cleaned_data.get('company'),
                    'department': self.cleaned_data.get('department'),
                    'role': self.cleaned_data.get('role')
                }
            )
        return user


class UserEditForm(forms.ModelForm):
    """
    Form for editing an existing User, including department field with custom styling.
    """
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=False, # Company is usually fixed, made required=False to allow it to be disabled.
        widget=forms.Select(attrs={'disabled': 'disabled'}) # Company generally not editable here by default
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(), # Populate based on user's company
        required=False, # Department might not be mandatory
        empty_label="Select a department",
    )
    role = forms.ChoiceField(
        choices=UserProfile.USER_ROLE_CHOICES,
        required=True # Making it required if field is editable
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "company", "department", "role"]

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None) # User performing the edit
        super().__init__(*args, **kwargs)

        edited_user_profile = getattr(self.instance, 'userprofile', None)
        request_user_profile = getattr(self.request_user, 'userprofile', None)

        current_company = edited_user_profile.company if edited_user_profile else None
        current_department = edited_user_profile.department if edited_user_profile else None
        current_role = edited_user_profile.role if edited_user_profile else None

        # Initialize company field
        if current_company:
            self.fields['company'].initial = current_company
            self.fields['company'].queryset = Company.objects.filter(pk=current_company.pk)
        else: # User being edited has no company (e.g. superadmin)
            self.fields['company'].queryset = Company.objects.all().order_by('name')

        # Initialize department field
        if current_company:
            self.fields['department'].queryset = Department.objects.filter(company=current_company).order_by('name')
        else: # If no company for user being edited, show all departments (relevant if superadmin is assigning company)
            self.fields['department'].queryset = Department.objects.all().order_by('company__name', 'name')
        if current_department:
            self.fields['department'].initial = current_department

        # Initialize role field
        self.fields['role'].initial = current_role
        self.fields['role'].choices = UserProfile.USER_ROLE_CHOICES # Default full list
        self.fields['role'].widget.attrs['disabled'] = 'disabled' # Disable by default

        # PERMISSION LOGIC FOR FIELDS:
        # Editing a staff user (potentially self if request_user is staff and is instance)
        if self.instance and self.instance.is_staff:
            self.fields['company'].widget.attrs['disabled'] = 'disabled'
            self.fields['department'].widget.attrs['disabled'] = 'disabled'
            self.fields['role'].widget.attrs['disabled'] = 'disabled'

        # Super Admin editing any user (is_staff=True for request_user)
        elif self.request_user and self.request_user.is_staff:
            self.fields['company'].widget.attrs.pop('disabled', None) # Enable company change
            self.fields['company'].queryset = Company.objects.all().order_by('name')
            self.fields['role'].widget.attrs.pop('disabled', None) # Enable role change
            # Department queryset should update if company changes (JS ideal)

        # Company Admin editing a user in their own company
        elif request_user_profile and request_user_profile.role == 'ADMIN' and \
             current_company and request_user_profile.company == current_company:
            self.fields['company'].widget.attrs['disabled'] = 'disabled' # Cannot change company

            if edited_user_profile and edited_user_profile.role != 'ADMIN': # Can change roles of non-admins
                self.fields['role'].widget.attrs.pop('disabled', None)
                self.fields['role'].choices = [r for r in UserProfile.USER_ROLE_CHOICES if r[0] != 'ADMIN'] # Cannot make another admin
            else: # Editing another admin or self (if logic allowed self-edit here)
                 self.fields['role'].widget.attrs['disabled'] = 'disabled'


        # User editing their own profile (my_profile)
        elif self.request_user == self.instance:
            self.fields['company'].widget.attrs['disabled'] = 'disabled'
            self.fields['role'].widget.attrs['disabled'] = 'disabled'
            # Department can be editable if not staff
            if self.instance.is_staff:
                 self.fields['department'].widget.attrs['disabled'] = 'disabled'

        # Apply common styling
        for field_name, field in self.fields.items():
            is_disabled = field.widget.attrs.get('disabled', False)
            if not is_disabled:
                 field.widget.attrs.update({"class": "custom-input"})

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, created = UserProfile.objects.get_or_create(user=user)

            original_company = profile.company

            # Only SuperAdmins can change company
            if self.request_user and self.request_user.is_staff and 'company' in self.cleaned_data:
                new_company = self.cleaned_data.get('company')
                if new_company != profile.company:
                    profile.company = new_company
                    # If company changed, department might be invalid. Clear it.
                    # User should re-select department if company changes.
                    if original_company != new_company:
                         profile.department = None

            # Handle department (only if not disabled)
            if 'department' in self.cleaned_data and not self.fields['department'].widget.attrs.get('disabled'):
                profile.department = self.cleaned_data.get('department')

            # Handle role (only if not disabled)
            if 'role' in self.cleaned_data and not self.fields['role'].widget.attrs.get('disabled'):
                profile.role = self.cleaned_data.get('role')

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
        fields = ["coming_soon", "url", "company"] # Added company

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Handle Company field based on user type
        if self.user and not self.user.is_staff:
            if hasattr(self.user, 'userprofile') and self.user.userprofile.company:
                self.fields['company'].queryset = Company.objects.filter(pk=self.user.userprofile.company.pk)
                self.fields['company'].initial = self.user.userprofile.company
                self.fields['company'].widget = forms.HiddenInput()
            else:
                self.fields['company'].queryset = Company.objects.none()
        elif self.user and self.user.is_staff:
            self.fields['company'].queryset = Company.objects.all()
            if self.instance and self.instance.pk and self.instance.company: # If editing, default to instance's company
                 self.fields['company'].initial = self.instance.company
        else: # No user context
            self.fields['company'].queryset = Company.objects.all()

        for field_name, field in self.fields.items():
            if field_name != 'company' or (self.user and self.user.is_staff):
                 field.widget.attrs.update({"class": "custom-input"})


class SessionUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Upload Excel File",
        help_text="Upload an Excel file (.xlsx) containing session data.",
        widget=forms.FileInput(attrs={"accept": ".xlsx"}),
    )

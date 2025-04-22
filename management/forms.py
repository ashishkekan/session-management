from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.forms import DateTimeInput

from .models import ExternalTopic, SessionTopic


class SessionTopicForm(forms.ModelForm):
    class Meta:
        model = SessionTopic
        fields = ["topic", "conducted_by", "date", "status", "cancelled_reason"]
        widgets = {
            "date": DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
        }

    def __init__(self, *args, user=None, **kwargs):
        super(SessionTopicForm, self).__init__(*args, **kwargs)
        self.fields["conducted_by"].queryset = User.objects.exclude(is_staff=True)
        self.fields["conducted_by"].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} ({obj.username})"
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M"]


class UserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    is_staff = forms.BooleanField(required=False, label="Is Admin?")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password", "is_staff"]

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Old Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter old password'})
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'})
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'})
    )


class ExternalTopicForm(forms.ModelForm):
    class Meta:
        model = ExternalTopic
        fields = ["coming_soon", "url"]

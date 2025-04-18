from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now

from .forms import (
    CustomPasswordChangeForm,
    ExternalTopicForm,
    SessionTopicForm,
    UserCreationForm,
    UserEditForm,
)
from .models import ExternalTopic, SessionTopic


@login_required
def create_topic(request):
    if request.method == "POST":
        form = SessionTopicForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("session_list")
    else:
        form = SessionTopicForm()
    return render(request, "session/create_topic.html", {"form": form})


@login_required
def home(request):
    user = request.user
    latest_topic = ExternalTopic.objects.order_by("-created_at").first()

    context = {
        "learning_topic": latest_topic,
    }

    if user.is_staff:
        top_sessions = SessionTopic.objects.filter(
            date__gt=now(),
        ).exclude(status="Completed").order_by("date")[:3]
        completed = SessionTopic.objects.filter(
            status="Completed"
        ).order_by("date")[:3]
        pending = SessionTopic.objects.filter(
            status="Pending"
        ).order_by("date")[:3]

        context.update(
            {
                "is_admin": True,
                "total_users": User.objects.count(),
                "total_sessions": SessionTopic.objects.count(),
                "all_sessions": SessionTopic.objects.order_by("-date"),
                "top_sessions": top_sessions,
                "completed": completed,
                "pending": pending,
            }
        )
    else:
        sessions = SessionTopic.objects.filter(conducted_by=user)
        upcoming_sessions = sessions.filter(
            status="Pending", date__gte=now()
        ).order_by("date")

        context.update(
            {
                "is_admin": False,
                "total_sessions": sessions.count(),
                "upcoming_sessions": upcoming_sessions,
            }
        )

    return render(request, "session/home.html", context)


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "session/login.html")


def user_logout(request):
    logout(request)
    return redirect("login")


def is_admin(user):
    return user.is_staff


@login_required
@user_passes_test(is_admin)
def add_user(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST or None)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect("home")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, "session/add_user.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    user = User.objects.get(id=user_id)

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated successfully.")
            return redirect("user_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserEditForm(instance=user)

    return render(request, "session/edit_user.html", {"form": form, "user_obj": user})


@login_required
def my_profile(request):
    employee = request.user

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("my_profile")
        else:
            messages.error(request, "There was an error updating your profile.")
    else:
        form = UserEditForm(instance=employee)

    return render(request, "session/my_profile.html", {"form": form})


@login_required
@user_passes_test(lambda u: u.is_staff)
def user_list(request):
    users = User.objects.all().order_by("username")
    paginator = Paginator(users, 10)  # Show 10 users per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "session/user_list.html", {"users": page_obj})

@login_required
def all_sessions_view(request):
    if request.user.is_staff:
        sessions = SessionTopic.objects.select_related("conducted_by").order_by("date")
    else:
        sessions = SessionTopic.objects.select_related("conducted_by").filter(conducted_by=request.user).order_by("date")

    paginator = Paginator(sessions, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "session/all_sessions.html", {"sessions": page_obj})


@login_required
def edit_session_view(request, session_id):
    session = get_object_or_404(SessionTopic, id=session_id)

    if request.method == "POST":
        form = SessionTopicForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, "Session updated successfully.")
            return redirect("session_list")
    else:
        form = SessionTopicForm(instance=session)

    return render(request, "session/edit_session.html", {"form": form, "session": session})


@login_required
def delete_session_view(request, session_id):
    session = get_object_or_404(SessionTopic, id=session_id)
    session.delete()
    messages.success(request, "Session deleted successfully.")
    return redirect("session_list")



@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after password change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('my_profile')  # Update with your profile page name
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'session/change_password.html', {'form': form})


@login_required
def create_external_topic(request):
    if request.method == "POST":
        form = ExternalTopicForm(request.POST)
        if form.is_valid:
            form.save()
            messages.success(request, "New topic create succussfully.")
    else:
        form = ExternalTopicForm()

    return render(request, "session/create_external_topic.html", {"form": form})


@login_required
def learning_view(request):
    sessions = ExternalTopic.objects.all()
    paginator = Paginator(sessions, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "session/learning-topic-list.html", {"sessions": page_obj})

from datetime import datetime

import openpyxl
import pandas as pd
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from django.core.mail import send_mail
from django.conf import settings

from management.forms import (
    CompanyProfileForm,
    CustomPasswordChangeForm,
    DepartmentForm,
    ExternalTopicForm,
    InviteAdminForm,
    SessionTopicForm,
    SessionUploadForm,
    SupportForm,
    UserCreationForm,
    UserEditForm,
)
from management.models import (
    ACTION_TYPES,
    PLACE_CHOICES,
    STATUSES,
    CompanyProfile,
    Department,
    ExternalTopic,
    RecentActivity,
    SessionTopic,
    SetupChecklist,
    UserProfile,
)
from management.utils import log_activity
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO


def is_admin(user):
    """
    Check if the user is an admin (staff).
    """
    return user.is_staff


@login_required
@user_passes_test(is_admin)
def export_sessions_pdf(request):
    """
    Generate and download a PDF file containing all session data.

    Creates a PDF with details of all sessions, including topic, conductor,
    date, status, and place, and logs the export activity.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: A response containing the generated PDF file for download.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    p.drawString(100, 800, "SessionXpert - All Sessions")
    y = 750
    sessions = SessionTopic.objects.all()
    for session in sessions:
        p.drawString(100, y, f"Topic: {session.topic}")
        p.drawString(100, y-20, f"Conducted By: {session.conducted_by.get_full_name}")
        p.drawString(100, y-40, f"Date: {session.date.strftime('%Y-%m-%d %H:%M')}")
        p.drawString(100, y-60, f"Status: {session.status}")
        p.drawString(100, y-80, f"Place: {session.place}")
        p.drawString(100, y-100, "-"*50)
        y -= 120
        if y < 100:
            p.showPage()
            y = 800
    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sessions.pdf"'
    log_activity(request.user, description="Exported sessions as PDF",action_type="CREATE")
    return response


@login_required
def create_topic(request):
    """
    Create a new session topic.

    Staff users can create sessions for others and notify normal users.
    Normal users creating a session notify staff users.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered page with the topic form or redirect to session list on success.
    """
    if request.method == "POST":
        form = SessionTopicForm(request.POST or None, user=request.user)
        if form.is_valid():
            session = form.save()
            if request.user.is_staff:
                normal_users = User.objects.filter(is_staff=False)
                log_activity(
                    request.user,
                    description=f"Admin created a new session: '{session.topic}'.",
                    action_type="CREATE SESSION",
                    target_users=normal_users,
                )
            else:
                # Normal user action, log_activity will notify admins automatically
                log_activity(request.user, description=f"Created a new session: '{session.topic}'.", action_type="CREATE SESSION")
            return redirect("session_list")
    else:
        form = SessionTopicForm(user=request.user)
    return render(request, "session/create_topic.html", {"form": form})


# management/views.py
from django.utils import timezone


# management/views.py
def home(request):
    """
    Display the dashboard for authenticated and unauthenticated users.

    For admins, includes a setup checklist and additional statistics.
    For regular users, displays role-specific content such as upcoming sessions.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered dashboard page with context.
    """
    company_profile = CompanyProfile.objects.first()
    is_admin = request.user.is_staff
    checklist = None
    if is_admin:
        checklist = SetupChecklist.objects.all()
        # Auto-check tasks
        if CompanyProfile.objects.filter(logo__isnull=False).exists():
            SetupChecklist.objects.filter(task='Set company logo and name').update(completed=True)
        if User.objects.filter(is_staff=True).exists():
            SetupChecklist.objects.filter(task='Add first admin user').update(completed=True)
        if SessionTopic.objects.exists():
            SetupChecklist.objects.filter(task='Create first session').update(completed=True)
        if Department.objects.exists():
            SetupChecklist.objects.filter(task='Add first department').update(completed=True)
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.get(user=request.user)
        role = user_profile.role
        total_users = User.objects.count() if is_admin else None
        total_sessions = SessionTopic.objects.count() if is_admin else None
        learning_topics = ExternalTopic.objects.filter(is_active=True)[:3]
        top_sessions = SessionTopic.objects.filter(date__gte=timezone.now(), status='Pending').order_by('date')[:3]
        completed = SessionTopic.objects.filter(status='Completed').order_by('-date')[:3] if is_admin else None
        pending = SessionTopic.objects.filter(status='Pending').order_by('date')[:3] if is_admin else None
        cancelled = SessionTopic.objects.filter(status='Cancelled').order_by('-date')[:3] if is_admin else None
        upcoming_sessions = SessionTopic.objects.filter(
            conducted_by=request.user, date__gte=timezone.now(), status='Pending'
        ).order_by('date')[:3] if not is_admin else None
        context = {
            'company_profile': company_profile,
            'is_admin': is_admin,
            'role': role,
            'total_users': total_users,
            'total_sessions': total_sessions,
            'learning_topics': learning_topics,
            'top_sessions': top_sessions,
            'completed': completed,
            'pending': pending,
            'cancelled': cancelled,
            'upcoming_sessions': upcoming_sessions,
            'checklist': checklist,
        }
        return render(request, 'session/home.html', context)
    else:
        return render(request, 'session/home.html', {'company_profile': company_profile})


def user_login(request):
    """
    Handle user login.

    Authenticates credentials and logs the user in, redirecting to the home page
    upon success. Displays error messages for invalid credentials.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Login form or redirect to home page on success.
    """
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_activity(request.user, description="Logged in successfully.", action_type="LOGGED IN")
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "session/login.html", {"form": form})


def user_logout(request):
    """
    Log out the current user and redirect to the login page.

    Logs the logout activity if the user is authenticated.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponseRedirect: Redirect to the login page.
    """
    if request.user.is_authenticated:
        log_activity(request.user, description="Logged out.", action_type="LOGGED OUT")
    logout(request)
    return redirect("login")


def is_admin(user):
    """
    Check if the user is an admin.

    Args:
        user: The User object to check.

    Returns:
        bool: True if the user is a staff member (admin), False otherwise.
    """
    return user.is_staff


@login_required
@user_passes_test(is_admin)
def add_user(request):
    """
    Allow admins to add a new user to the system.

    Creates a new user and logs the activity, notifying non-admin users.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: User creation form or redirect to home page on success.
    """
    if request.method == "POST":
        form = UserCreationForm(request.POST or None)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            log_activity(
                request.user,
                description=f"Admin added new user '{user.username}'.",
                action_type="Add user",
                target_users=User.objects.filter(is_staff=False),
            )
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "session/add_user.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    """
    Allow admins to edit a user's profile.

    Updates user details and logs the activity, notifying the edited user.

    Args:
        request: The HTTP request object.
        user_id (int): ID of the user to edit.

    Returns:
        HttpResponse: Edit form or redirect to user list on success.
    """
    user = User.objects.get(id=user_id)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            log_activity(request.user, description="Admin edited your profile.", action_type="Edit User", edited_user=user)
            messages.success(request, "User updated successfully.")
            return redirect("user_list")
    else:
        form = UserEditForm(instance=user)
    return render(request, "session/edit_user.html", {"form": form, "user_obj": user})


@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """
    Allow admins to delete a user from the system.

    Prevents deletion of superusers and logs the activity.

    Args:
        request: The HTTP request object.
        user_id (int): ID of the user to delete.

    Returns:
        HttpResponseRedirect: Redirect to user list.
    """
    user = get_object_or_404(User, id=user_id)
    if user.is_staff:
        messages.error(request, "You cannot delete a superuser.")
        return redirect("user_list")
    user.delete()
    log_activity(
        request.user,
        f"Admin deleted user with ID {user_id}.",
        target_users=User.objects.filter(is_staff=False),
    )
    messages.success(request, "User deleted successfully.")
    return redirect("user_list")


@login_required
def my_profile(request):
    """
    Allow the logged-in user to view and update their profile.

    Updates the user's profile and logs the activity.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Profile page with edit form or redirect on success.
    """
    employee = request.user
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=employee)
        if not form.is_valid():
            messages.error(request, "There was an error updating your profile.")
        form.save()
        log_activity(employee, "Updated their profile.")
        messages.success(request, "Profile updated successfully.")
        return redirect("my_profile")
    form = UserEditForm(instance=employee)
    return render(request, "session/my_profile.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def user_list(request):
    """
    Display a paginated list of registered users for admin users.

    Allows filtering users by department via a dropdown selection.
    If a department is selected (via GET parameter), only users associated
    with that department are displayed.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered template showing the list of users with pagination and filters.
    """
    department_id = request.GET.get("department")
    departments = Department.objects.all()

    users = User.objects.all().order_by("username").select_related("userprofile")

    if department_id:
        users = users.filter(userprofile__department_id=department_id)

    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "session/user_list.html",
        {
            "users": page_obj,
            "departments": departments,
            "selected_department": department_id,
        },
    )


@login_required
def all_sessions_view(request):
    """
    Display all sessions for admins or user-specific sessions for regular users.

    Admins see all sessions, while regular users see only their own sessions.
    Sessions are paginated.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered page with a paginated list of sessions.
    """
    if request.user.is_staff:
        sessions = SessionTopic.objects.select_related("conducted_by").order_by("date")
    else:
        sessions = (
            SessionTopic.objects.select_related("conducted_by")
            .filter(conducted_by=request.user)
            .order_by("date")
        )
    paginator = Paginator(sessions, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "session/all_sessions.html", {"sessions": page_obj})


@login_required
def edit_session_view(request, session_id):
    """
    Allow editing of an existing session.

    Updates session details and logs the activity, notifying relevant users.

    Args:
        request: The HTTP request object.
        session_id (int): ID of the session to edit.

    Returns:
        HttpResponse: Edit form or redirect to session list on success.
    """
    session = get_object_or_404(SessionTopic, id=session_id)
    if request.method == "POST":
        form = SessionTopicForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            if request.user.is_staff:
                log_activity(
                    request.user,
                    f"Admin updated session: '{session.topic}'.",
                    target_users=User.objects.filter(is_staff=False),
                )
            else:
                log_activity(request.user, f"Updated session: '{session.topic}'.")
            messages.success(request, "Session updated successfully.")
            return redirect("session_list")
    else:
        form = SessionTopicForm(instance=session)
    return render(
        request, "session/edit_session.html", {"form": form, "session": session}
    )


@login_required
def delete_session_view(request, session_id):
    """
    Allow deletion of a session.

    Deletes the specified session and logs the activity.

    Args:
        request: The HTTP request object.
        session_id (int): ID of the session to delete.

    Returns:
        HttpResponseRedirect: Redirect to session list.
    """
    session = get_object_or_404(SessionTopic, id=session_id)
    if request.user.is_staff:
        log_activity(
            request.user,
            description=f"Admin deleted session: '{session.topic}'.",
            action_type="DELETE SESSION",
            target_users=User.objects.filter(is_staff=False),
        )
    else:
        log_activity(request.user, f"Deleted session: '{session.topic}'.")
    session.delete()
    messages.success(request, "Session deleted successfully.")
    return redirect("session_list")


@login_required
def change_password(request):
    """
    Allow the current user to change their password.

    Updates the password and maintains the session, logging the activity.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Password change form or redirect to profile on success.
    """
    if request.method == "POST":
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_activity(request.user, "Changed their password.")
            messages.success(request, "Your password was successfully updated!")
            return redirect("my_profile")
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, "session/change_password.html", {"form": form})


@login_required
def create_external_topic(request):
    """
    Create a new external learning topic.

    Saves the topic and logs the activity, notifying relevant users.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Form or redirect to learning topics list on success.
    """
    if request.method == "POST":
        form = ExternalTopicForm(request.POST)
        if form.is_valid():
            topic = form.save()
            if request.user.is_staff:
                log_activity(
                    request.user,
                    f"Admin added new learning topic: '{topic.coming_soon}'.",
                    target_users=User.objects.filter(is_staff=False),
                )
            else:
                log_activity(
                    request.user, f"Added new learning topic: '{topic.coming_soon}'."
                )
            messages.success(request, "New topic created successfully.")
            return redirect("learning-view")
    else:
        form = ExternalTopicForm()
    return render(request, "session/create_external_topic.html", {"form": form})


@login_required
def learning_view(request):
    """
    Display all external learning topics.

    Shows a paginated list of external topics ordered by creation date.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered page with a paginated list of external topics.
    """
    sessions = ExternalTopic.objects.all().order_by("-created_at")
    paginator = Paginator(sessions, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "session/learning-topic-list.html", {"sessions": page_obj})


@login_required
def edit_learning(request, learning_id):
    """
    Allow editing of an existing external learning topic.

    Updates the topic and logs the activity, notifying relevant users.

    Args:
        request: The HTTP request object.
        learning_id (int): ID of the external topic to edit.

    Returns:
        HttpResponse: Edit form or redirect to learning topics list on success.
    """
    learning = get_object_or_404(ExternalTopic, id=learning_id)
    if request.method == "POST":
        form = ExternalTopicForm(request.POST, instance=learning)
        if form.is_valid():
            form.save()
            if request.user.is_staff:
                log_activity(
                    user=request.user,
                    description=f"Admin updated learning topic: '{learning.coming_soon}'.",
                    action_type='UPDATE',
                    target_users=User.objects.filter(is_staff=False),
                )
            else:
                log_activity(
                    user=request.user, 
                    description=f"Updated learning topic: '{learning.coming_soon}'."
                )
            messages.success(request, "Learning updated successfully.")
            return redirect("learning-view")
    else:
        form = ExternalTopicForm(instance=learning)
    return render(
        request, "session/edit_learning.html", {"form": form, "learning": learning}
    )


@login_required
def delete_learning(request, learning_id):
    """
    Allow deletion of an external learning topic.

    Deletes the specified topic and logs the activity.

    Args:
        request: The HTTP request object.
        learning_id (int): ID of the external topic to delete.

    Returns:
        HttpResponseRedirect: Redirect to learning topics list.
    """
    learning = get_object_or_404(ExternalTopic, id=learning_id)
    if request.user.is_staff:
        log_activity(
            user=request.user,
            description=f"Admin deleted learning topic: '{learning.coming_soon}'.",
            target_users=User.objects.filter(is_staff=False),
        )
    else:
        log_activity(
            user=request.user,
            description=f"Deleted learning topic: '{learning.coming_soon}'.",
        )
    learning.delete()
    messages.success(request, "Learning deleted successfully.")
    return redirect("learning-view")


@login_required
def recent_activities(request):
    """
    Display recent activities for the logged-in user.

    Shows a paginated list of activities, with optional filtering by action type.
    Marks activities as read when viewed.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered page with a paginated list of recent activities.
    """
    action_type = request.GET.get('action_type', '')
    activities = RecentActivity.objects.filter(user=request.user)
    if action_type:
        activities = activities.filter(action_type=action_type)
    activities = activities.order_by('-timestamp')
    activities.update(read=True)  # Mark as read
    paginator = Paginator(activities, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "session/recent_activities.html", {"activities": page_obj, 'action_types': ACTION_TYPES,
        'selected_action_type': action_type})


@login_required
def department_list(request):
    """
    Display a list of all departments.

    Shows departments ordered by creation date.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered page with a list of departments.
    """
    departments = Department.objects.all().order_by("-created_at")
    return render(request, "session/department_list.html", {"departments": departments})


@login_required
def department_create(request):
    """
    Allow creation of a new department.

    Saves the department and logs the activity, notifying non-admin users.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Department creation form or redirect to department list on success.
    """
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            log_activity(
                user=request.user,
                description=f"Admin created new department: '{department.name}'.",
                action_type='CREATE',
                target_users=User.objects.filter(is_staff=False),
            )
            messages.success(request, "Department created successfully.")
            return redirect("department-list")
    else:
        form = DepartmentForm()
    return render(request, "session/department_form.html", {"form": form})


@login_required
def department_edit(request, pk):
    """
    Allow editing of an existing department.

    Updates the department and logs the activity, notifying non-admin users.

    Args:
        request: The HTTP request object.
        pk (int): Primary key of the department to edit.

    Returns:
        HttpResponse: Edit form or redirect to department list on success.
    """
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            log_activity(
                user=request.user,
                description=f"Admin edited department: '{department.name}'.",
                action_type='UPDATE',
                target_users=User.objects.filter(is_active=True, is_staff=False),
            )
            messages.success(request, "Department updated successfully.")
            return redirect("department-list")
    else:
        form = DepartmentForm(instance=department)
    return render(request, "session/department_form.html", {"form": form})


@login_required
def department_delete(request, pk):
    """
    Allow deletion of a department.

    Deletes the specified department and logs the activity.

    Args:
        request: The HTTP request object.
        pk (int): Primary key of the department to delete.

    Returns:
        HttpResponseRedirect: Redirect to department list.
    """
    department = get_object_or_404(Department, pk=pk)
    department.delete()
    log_activity(
        request.user,
        f"Admin deleted department: '{department.name}'.",
        action_type='DELETE',
        target_users=User.objects.filter(is_active=True, is_staff=False),
    )
    messages.success(request, "Department deleted successfully.")
    return redirect("department-list")


@staff_member_required
def export_sessions(_request):
    """
    Generate and download an Excel file containing all 'Pending' session data.

    Creates an Excel file with session details, sorted by date, for download.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: A response containing the generated Excel file for download.
    """
    # Fetch all pending sessions and convert to list of dicts
    sessions = SessionTopic.objects.filter(status="Pending").select_related(
        "conducted_by"
    )

    session_data = []
    for i, s in enumerate(sessions, 1):
        session_data.append(
            {
                "No.": i,
                "Date": s.date,
                "Topic": s.topic,
                "Status": s.status,
                "Assigned To": s.conducted_by.get_full_name()
                or s.conducted_by.username,
                "Place": s.place,
            }
        )

    # Create DataFrame and sort by Date
    df = pd.DataFrame(session_data)
    df.sort_values(by="Date", inplace=True)

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Sessions"

    # Write headers
    for col_num, column in enumerate(df.columns, 1):
        col_letter = get_column_letter(col_num)
        ws[f"{col_letter}1"] = column
        ws[f"{col_letter}1"].font = openpyxl.styles.Font(bold=True)

    # Write data rows
    for row_num, row in enumerate(df.itertuples(index=False), start=2):
        for col_num, value in enumerate(row, start=1):
            ws.cell(
                row=row_num,
                column=col_num,
                value=(
                    value.strftime("%Y/%m/%d")
                    if isinstance(value, pd.Timestamp)
                    else value
                ),
            )

    # Auto-adjust column widths
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2

    # Prepare response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="sessions.xlsx"'

    # Save workbook to response
    wb.save(response)
    return response


@staff_member_required
def upload_sessions_excel(request):
    """
    Handle Excel file upload to create or update SessionTopic records.

    Processes an Excel file to create new sessions or update existing ones
    based on topic and user. Validates headers, dates, users, status, and place.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponseRedirect: Redirect to session list with success/error messages.
    """
    if request.method == "POST":
        form = SessionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES["excel_file"]
            try:
                wb = load_workbook(excel_file)
                ws = wb.active

                # Check headers
                expected_headers = [
                    "No.",
                    "Topic",
                    "Date",
                    "Status",
                    "Assigned To",
                    "Place",
                    "Cancelled Reason",
                ]
                headers = [cell.value for cell in ws[1]]
                if headers != expected_headers:
                    messages.error(
                        request,
                        "Invalid Excel file format. Expected headers: "
                        + ", ".join(expected_headers),
                    )
                    return redirect("session_list")

                # Process rows (skip header)
                for row in ws.iter_rows(min_row=2, values_only=True):
                    (
                        _,
                        topic,
                        date_str,
                        status,
                        assigned_to,
                        place,
                        cancelled_reason,
                    ) = row

                    # Skip empty rows
                    if not topic or not assigned_to:
                        continue

                    # Parse date
                    try:
                        date = datetime.strptime(date_str, "%Y/%m/%d").date()
                    except (ValueError, TypeError):
                        messages.error(
                            request,
                            f"Invalid date format for topic '{topic}'. Expected YYYY/MM/DD.",
                        )
                        continue

                    # Find user by full name
                    try:
                        first_name, last_name = assigned_to.split(" ", 1)
                        user = User.objects.get(
                            first_name=first_name, last_name=last_name
                        )
                    except (ValueError, User.DoesNotExist):
                        messages.error(
                            request,
                            f"User '{assigned_to}' not found for topic '{topic}'.",
                        )
                        continue

                    # Validate status and place
                    valid_statuses = [choice[0] for choice in STATUSES]
                    valid_places = [choice[0] for choice in PLACE_CHOICES]
                    if status not in valid_statuses:
                        messages.error(
                            request, f"Invalid status '{status}' for topic '{topic}'."
                        )
                        continue
                    if place not in valid_places:
                        messages.error(
                            request, f"Invalid place '{place}' for topic '{topic}'."
                        )
                        continue

                    # Check for existing session by topic and user
                    session, created = SessionTopic.objects.get_or_create(
                        topic=topic,
                        conducted_by=user,
                        defaults={
                            "date": date,
                            "status": status,
                            "place": place,
                            "cancelled_reason": cancelled_reason or None,
                        },
                    )

                    if not created:
                        # Update existing session
                        session.date = date
                        session.status = status
                        session.place = place
                        session.cancelled_reason = cancelled_reason or None
                        session.save()
                        messages.info(
                            request, f"Updated session: {topic} for {assigned_to}"
                        )

                    else:
                        messages.success(
                            request, f"Created session: {topic} for {assigned_to}"
                        )

                messages.success(request, "Excel file processed successfully.")
                return redirect("session_list")

            except (openpyxl.utils.exceptions.InvalidFileException, ValueError) as e:
                messages.error(request, f"Error processing Excel file: {str(e)}")
                return redirect("session_list")

        else:
            messages.error(request, "Invalid file upload.")
            return redirect("session_list")

    return redirect("session_list")


@login_required
@user_passes_test(is_admin)
def company_profile(request):
    """
    Allow admins to update the company profile.

    Manages the single instance of the company profile (name, logo, email)
    and logs the update activity.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Company profile form or redirect to home page on success.
    """
    profile, _ = CompanyProfile.objects.get_or_create(id=1)  # Single instance
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            log_activity(request.user, description=f"Updated company profile: {profile.name}", action_type="Edit Company")
            messages.success(request, "Company profile updated successfully.")
            return redirect('company_profile')
    else:
        form = CompanyProfileForm(instance=profile)
    return render(request, 'session/company_profile.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def invite_admin(request):
    """
    Allow admins to invite new admin users via email.

    Creates a new admin user with a temporary password, sends an invitation email,
    and logs the activity.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Invitation form or redirect to user list on success.
    """
    if request.method == 'POST':
        form = InviteAdminForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            department = form.cleaned_data['department']
            # Generate a temporary password
            temp_password = User.objects.make_random_password()
            user = User.objects.create_user(
                username=email.split('@')[0],
                email=email,
                password=temp_password,
                is_staff=True
            )
            UserProfile.objects.create(user=user, department=department)
            # Send email
            send_mail(
                subject='SessionXpert Admin Invitation',
                message=f'You have been invited as an admin. Your credentials:\nUsername: {user.username}\nPassword: {temp_password}\nPlease change your password after logging in.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            log_activity(
                user=request.user,
                description=f"Invited admin: {user.username}",
                action_type='INVITE',
                target_users=User.objects.filter(is_active=True, is_staff=True),
            )
            return redirect('user_list')
    else:
        form = InviteAdminForm()
    return render(request, 'session/invite_admin.html', {'form': form})


@login_required
def faq(request):
    """
    Display the FAQ page and handle question submissions.

    Allows users to submit questions via a form, which are sent to the admin via email.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: FAQ page or redirect to FAQ page on submission.
    """
    if request.method == 'POST':
        question = request.POST.get('question')
        if question:
            send_mail(
                subject='New FAQ Submission',
                message=f'Question from {request.user.username}: {question}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
            )
            log_activity(
                user=request.user,
                description=f"User submitted FAQ: {question[:30]}...",
                action_type='FAQ'
            )
            return redirect('faq')
    return render(request, 'session/faq.html')


@login_required
def support(request):
    """
    Handle support request submissions.

    Allows users to submit support requests with a subject, message, and priority,
    which are sent to the admin via email.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Support form or redirect to support page on success.
    """
    if request.method == 'POST':
        form = SupportForm(request.POST or None)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            priority = form.cleaned_data['priority']
            full_message = f"Support Request from {request.user.username} ({request.user.email})\nPriority: {priority}\n\n{message}"
            send_mail(
                subject=f"Support: {subject}",
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
            )
            log_activity(request.user, description=f"Submitted support request: {subject}", action_type='SUPPORT')
            return redirect('support')
    else:
        form = SupportForm()
    return render(request, 'session/support.html', {'form': form})

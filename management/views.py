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

from management.forms import (
    CustomPasswordChangeForm,
    DepartmentForm,
    ExternalTopicForm,
    SessionTopicForm,
    SessionUploadForm,
    UserCreationForm,
    UserEditForm,
    CompanyForm, # Added CompanyForm
)
from management.models import (
    PLACE_CHOICES,
    STATUSES,
    Company, # Added Company
    Department,
    ExternalTopic,
    RecentActivity,
    SessionTopic,
)
from management.utils import (
    log_activity,
    is_super_admin,
    is_company_admin,
    is_manager,
    # is_employee will be added if needed
)
# Consider adding from django.urls import reverse_lazy for success_urls in generic views if used


def public_landing_page(request):
    """
    Display the public landing page.
    This page is accessible without login and shows project features.
    """
    return render(request, "public_home.html")


@login_required
def create_topic(request):
    """
    Authenticated users (Super Admin, Company Admin, Manager, Employee) can create a new session topic.
    Company context is derived from user profile or selected by Super Admin.

    - Staff users can create sessions for others and notify normal users.
    - Normal users creating a session notify staff users.

    Returns:
        HttpResponse: Rendered page with the topic form.
    """
    if request.method == "POST":
        form = SessionTopicForm(request.POST or None, user=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            # Ensure company is set, especially if hidden in form for non-staff
            if not session.company_id and hasattr(request.user, 'userprofile') and request.user.userprofile.company:
                session.company = request.user.userprofile.company

            if not session.company_id: # Still no company
                 messages.error(request, "Could not determine company for the session.")
                 return render(request, "session/create_topic.html", {"form": form})

            # Ensure conducted_by user belongs to the session's company if session company is now set
            if session.company and session.conducted_by.userprofile.company != session.company:
                messages.error(request, f"Selected user '{session.conducted_by}' does not belong to the company '{session.company}'.")
                return render(request, "session/create_topic.html", {"form": form})

            session.save()

            log_message = f"Created a new session: '{session.topic}' for company '{session.company.name}'."
            if request.user.is_staff:
                # Notify users within that company, or company admins?
                # For now, generic log for staff, specific for user's company
                target_users = User.objects.filter(userprofile__company=session.company, is_staff=False)
                log_activity(request.user, f"Admin {log_message}", target_users=target_users, company_obj=session.company)
            else:
                log_activity(request.user, log_message, company_obj=session.company)
            return redirect("session_list")
    else:
        form = SessionTopicForm(user=request.user)
    return render(request, "session/create_topic.html", {"form": form})


def home(request):
    """
    Display the home page.

    - For staff: shows user/session stats and upcoming sessions.
    - For regular users: shows user's upcoming sessions.

    Returns:
        HttpResponse: Rendered home page with context.
    """
    user = request.user
    user_company = None
    if hasattr(user, 'userprofile') and user.userprofile:
        user_company = user.userprofile.company

    context = {}

    # Default to global queries for staff, or filter by company for non-staff
    if user.is_staff: # Super Admin view
        latest_topics_qs = ExternalTopic.objects.all()
        top_sessions_qs = SessionTopic.objects.all()
        all_sessions_qs = SessionTopic.objects.all() # For general stats

        context.update({
            "is_admin": True,
            "total_users": User.objects.count(), # Global user count
            "total_sessions": all_sessions_qs.count(), # Global session count
            # For specific lists like completed, pending, cancelled, superadmin sees global for now
            "completed": all_sessions_qs.filter(status="Completed").order_by("-date")[:3],
            "pending": all_sessions_qs.filter(status="Pending").order_by("date")[:3],
            "cancelled": all_sessions_qs.filter(status="Cancelled").order_by("-date")[:3],
        })

    elif user_company: # Company user view
        latest_topics_qs = ExternalTopic.objects.filter(company=user_company)
        top_sessions_qs = SessionTopic.objects.filter(company=user_company)

        # Sessions specific to the user (e.g., conducted by them within their company)
        user_specific_sessions = top_sessions_qs.filter(conducted_by=user)
        upcoming_sessions = user_specific_sessions.filter(status="Pending", date__gte=now()).order_by("date")

        context.update({
            "is_admin": False, # Company user is not a super admin
            "company_name": user_company.name,
            "total_sessions": user_specific_sessions.count(), # Or top_sessions_qs.count() for all in company
            "upcoming_sessions": upcoming_sessions,
        })
    else: # Authenticated user but no company (should ideally not happen for non-staff)
        latest_topics_qs = ExternalTopic.objects.none()
        top_sessions_qs = SessionTopic.objects.none()
        messages.warning(request, "Your profile is not associated with a company. Dashboard data may be limited.")

    # Common context elements, potentially filtered by company
    context["learning_topics"] = latest_topics_qs.order_by("-created_at")[:5] # Show top 5 learning topics
    context["top_sessions"] = (
        top_sessions_qs.filter(date__gt=now())
        .exclude(status__in=["Completed", "Cancelled"])
        .select_related("conducted_by", "company")
        .order_by("date")[:3]
    )

    # If staff, they see all sessions in their list. If not, it's already filtered by company.
    if user.is_staff:
         context["all_sessions_list"] = SessionTopic.objects.order_by("-date").select_related('company')[:10] # Example: recent 10 global sessions
    elif user_company:
         context["all_sessions_list"] = SessionTopic.objects.filter(company=user_company).order_by("-date").select_related('company')[:10]


    return render(request, "session/home.html", context)


def user_login(request):
    """
    Handle user login.

    Authenticates credentials and redirects to home upon success.

    Returns:
        HttpResponse: Login form or redirect on success.
    """
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            user_company = user.userprofile.company if hasattr(user, 'userprofile') and user.userprofile else None
            log_activity(request.user, "Logged in successfully.", company_obj=user_company)
            return redirect("dashboard")  # Updated redirect
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "session/login.html", {"form": form})


def user_logout(request):
    """
    Log the user out and redirect to login.

    Returns:
        HttpResponseRedirect: Redirect to login page.
    """
    if request.user.is_authenticated:
        user_company = request.user.userprofile.company if hasattr(request.user, 'userprofile') and request.user.userprofile else None
        log_activity(request.user, "Logged out.", company_obj=user_company)
    logout(request)
    return redirect("login")


def is_admin(user):
    """Check if the user is an admin."""
    return user.is_staff


@login_required
# @user_passes_test(is_admin) # Custom check
def add_user(request):
    """
    Super Admins or Company Admins can add a new user to the system.

    Returns:
        HttpResponse: User creation form or redirect on success.
    """
    # Permission Check: Must be Super Admin or a Company Admin
    acting_user_profile = getattr(request.user, 'userprofile', None)
    if not (is_super_admin(request.user) or (acting_user_profile and acting_user_profile.role == 'ADMIN')):
        messages.error(request, "You do not have permission to add users.")
        return redirect("dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST or None, request_user=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save() # This should also create UserProfile with company via the form's save method
            # Assuming user.userprofile and user.userprofile.company are set by the form's save method
            new_user_company = user.userprofile.company if hasattr(user, 'userprofile') and user.userprofile else None
            log_activity(
                request.user,
                f"Admin added new user '{user.username}'.",
                target_users=[user], # Typically log for the admin and the new user
                company_obj=new_user_company
            )
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect("dashboard") # Redirect to dashboard
    else:
        form = UserCreationForm(request_user=request.user)
    return render(request, "session/add_user.html", {"form": form})


@login_required
# @user_passes_test(is_admin) # Custom check
def edit_user(request, user_id):
    """
    Super Admins or Company Admins can edit a user’s profile.

    Args:
        user_id (int): ID of the user to edit.

    Returns:
        HttpResponse: Edit form or redirect on success.
    """
    user_to_edit = get_object_or_404(User, id=user_id) # Renamed for clarity
    acting_user = request.user
    acting_user_profile = getattr(acting_user, 'userprofile', None)
    user_to_edit_profile = getattr(user_to_edit, 'userprofile', None)

    # Permission checks
    can_edit = False
    if is_super_admin(acting_user):
        if not user_to_edit.is_staff or user_to_edit == acting_user : # Superadmin can edit non-staff, or themselves (though my_profile is better for self)
            can_edit = True
    elif acting_user_profile and acting_user_profile.role == 'ADMIN':
        if user_to_edit_profile and user_to_edit_profile.company == acting_user_profile.company and \
           not user_to_edit.is_staff and user_to_edit_profile.role != 'ADMIN':
            can_edit = True

    if not can_edit:
        messages.error(request, "You do not have permission to edit this user.")
        return redirect("user_list" if is_super_admin(acting_user) else "dashboard")


    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user_to_edit, request_user=acting_user)
        if form.is_valid():
            saved_user = form.save()
            # Assuming UserEditForm's save() updates/maintains userprofile.company
            edited_user_company = saved_user.userprofile.company if hasattr(saved_user, 'userprofile') and saved_user.userprofile else None
            log_activity(request.user, "Admin edited your profile.", edited_user=saved_user, company_obj=edited_user_company)
            messages.success(request, "User updated successfully.")
            return redirect("user_list")
    else:
        form = UserEditForm(instance=user_to_edit, request_user=acting_user)
    return render(request, "session/edit_user.html", {"form": form, "user_obj": user_to_edit})


@login_required
# @user_passes_test(is_admin) # Custom check
def delete_user(request, user_id):
    """
    Super Admins or Company Admins can delete a user from the system.

    Args:
        user_id (int): ID of the user to delete.

    Returns:
        HttpResponseRedirect: Redirect to user list.
    """
    user_to_delete = get_object_or_404(User, id=user_id)
    acting_user = request.user
    acting_user_profile = getattr(acting_user, 'userprofile', None)
    user_to_delete_profile = getattr(user_to_delete, 'userprofile', None)

    # Permission checks
    can_delete = False
    if is_super_admin(acting_user):
        if not user_to_delete.is_staff: # Superadmin can delete non-staff
            can_delete = True
    elif acting_user_profile and acting_user_profile.role == 'ADMIN':
        if user_to_delete_profile and user_to_delete_profile.company == acting_user_profile.company and \
           not user_to_delete.is_staff and user_to_delete_profile.role != 'ADMIN':
            can_delete = True

    if not can_delete:
        messages.error(request, "You do not have permission to delete this user.")
        return redirect("user_list" if is_super_admin(acting_user) else "dashboard")

    # Proceed with deletion
    deleted_user_company = user_to_delete_profile.company if user_to_delete_profile else None
    deleted_username = user_to_delete.username # Capture before delete
    user_to_delete.delete()

    log_activity(
        acting_user,
        f"Deleted user '{deleted_username}' (ID: {user_id}).",
        company_obj=deleted_user_company
    )
    messages.success(request, "User deleted successfully.")
    return redirect("user_list")


@login_required
def my_profile(request):
    """
    View and update the logged-in user's profile.

    Returns:
        HttpResponse: Profile page.
    """
    employee = request.user # User editing their own profile
    if request.method == "POST":
        # Pass employee as request_user, as they are initiating the edit on themselves
        form = UserEditForm(request.POST, instance=employee, request_user=employee)
        if not form.is_valid():
            messages.error(request, "There was an error updating your profile.")
        else: # only save and log if form is valid
            form.save()
            user_company = employee.userprofile.company if hasattr(employee, 'userprofile') and employee.userprofile else None
            log_activity(employee, "Updated their profile.", company_obj=user_company)
            messages.success(request, "Profile updated successfully.")
            return redirect("my_profile")
    # Pass employee as request_user for initial form rendering as well
    form = UserEditForm(instance=employee, request_user=employee)
    return render(request, "session/my_profile.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def user_list(request):
    """
    Display a paginated list of registered users for admin users.

    Allows filtering users by department via a dropdown selection.
    If a department is selected (via GET parameter), only users associated
    with that department will be displayed.

    Context passed to template:
        - users: Paginated queryset of users.
        - departments: All departments for the dropdown filter.
        - selected_department: Currently selected department ID (if any).

    Template:
        session/user_list.html

    Returns:
        HttpResponse: Rendered template showing the list of users.
    """
    department_id = request.GET.get("department")
    company_id = request.GET.get("company") # New company filter

    # Querysets for filters
    # Super admin sees all companies and all departments for filtering
    companies = Company.objects.all().order_by('name')
    departments = Department.objects.all().order_by('company__name', 'name').select_related('company')


    users_qs = User.objects.all().order_by("userprofile__company__name", "username").select_related("userprofile__department", "userprofile__company")

    if company_id:
        users_qs = users_qs.filter(userprofile__company_id=company_id)
        # If a company is selected, narrow down department choices for the filter
        departments = departments.filter(company_id=company_id)

    if department_id:
        users_qs = users_qs.filter(userprofile__department_id=department_id)

    paginator = Paginator(users_qs, 10) # Use users_qs
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "session/user_list.html",
        {
            "users": page_obj,
            "companies": companies, # Add companies to context
            "departments": departments,
            "selected_company": company_id, # Add selected company
            "selected_department": department_id,
        },
    )


@login_required
def all_sessions_view(request):
    """
    View all sessions.

    - Admins see all sessions.
    - Regular users see only their own.

    Returns:
        HttpResponse: List of sessions.
    """
    user = request.user
    if user.is_staff: # Superuser/admin sees all sessions from all companies
        sessions = SessionTopic.objects.select_related("conducted_by", "company").order_by("company__name", "date")
    elif hasattr(user, 'userprofile') and user.userprofile.company:
        # Company user sees sessions for their company
        sessions = (
            SessionTopic.objects.filter(company=user.userprofile.company)
            .select_related("conducted_by", "company")
            .order_by("date")
        )
        # Further filter: if the user is a manager, they see all in their company.
        # If they are an employee, they only see sessions they conduct or are part of (if participant model existed)
        # For now, let's assume non-staff see all sessions in their company.
        # If you want to restrict to only sessions conducted_by the user:
        # sessions = sessions.filter(conducted_by=user)
    else: # User not staff and no company assigned
        sessions = SessionTopic.objects.none()
        messages.warning(request, "You are not associated with a company, so no sessions can be shown.")

    paginator = Paginator(sessions, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "session/all_sessions.html", {"sessions": page_obj})


@login_required
def edit_session_view(request, session_id):
    """
    Edit an existing session.

    Args:
        session_id (int): ID of the session.

    Returns:
        HttpResponse: Form or redirect.
    """
    session = get_object_or_404(SessionTopic, id=session_id)
    acting_user = request.user

    # Permission Check
    can_edit = False
    if is_super_admin(acting_user):
        can_edit = True
    elif is_company_admin(acting_user, company_obj=session.company) or \
         is_manager(acting_user, company_obj=session.company):
        can_edit = True
    elif is_employee(acting_user, company_obj=session.company) and session.conducted_by == acting_user:
        can_edit = True

    if not can_edit:
        messages.error(request, "You do not have permission to edit this session.")
        return redirect("session_list")

    if request.method == "POST":
        form = SessionTopicForm(request.POST, instance=session, user=acting_user)
        if form.is_valid():
            updated_session = form.save(commit=False)

            # Ensure company is not changed by non-staff, or if changed by staff, conducted_by is valid
            if not is_super_admin(acting_user) and updated_session.company != session.company: # Non-super_admin cannot change company
                messages.error(request, "You cannot change the company of the session.")
                return render(request, "session/edit_session.html", {"form": form, "session": session})

            if updated_session.company and updated_session.conducted_by.userprofile.company != updated_session.company:
                messages.error(request, f"Selected user '{updated_session.conducted_by}' does not belong to the company '{updated_session.company}'.")
                return render(request, "session/edit_session.html", {"form": form, "session": session})

            updated_session.save()
            log_message = f"Updated session: '{updated_session.topic}' in company '{updated_session.company.name}'."
            if is_super_admin(acting_user): # Logged as super_admin action
                target_users = User.objects.filter(userprofile__company=updated_session.company, is_staff=False)
                log_activity(acting_user, f"Admin {log_message}", target_users=target_users, company_obj=updated_session.company)
            else: # Logged as company user action
                log_activity(acting_user, log_message, company_obj=updated_session.company)
            messages.success(request, "Session updated successfully.")
            return redirect("session_list")
    else:
        form = SessionTopicForm(instance=session, user=acting_user)
    return render(
        request, "session/edit_session.html", {"form": form, "session": session}
    )


@login_required
def delete_session_view(request, session_id):
    """
    Delete a session.

    Args:
        session_id (int): ID of the session.

    Returns:
        HttpResponseRedirect: Redirect to session list.
    """
    session = get_object_or_404(SessionTopic, id=session_id)
    session_company = session.company # Get company before deleting session
    session_topic_name = session.topic
    acting_user = request.user

    # Permission Check
    can_delete = False
    if is_super_admin(acting_user):
        can_delete = True
    elif is_company_admin(acting_user, company_obj=session_company) or \
         is_manager(acting_user, company_obj=session_company): # Managers can delete sessions in their company
        can_delete = True
    elif is_employee(acting_user, company_obj=session_company) and session.conducted_by == acting_user: # Employees can delete sessions they conduct
        can_delete = True

    if not can_delete:
        messages.error(request, "You do not have permission to delete this session.")
        return redirect("session_list")

    log_message = f"Deleted session: '{session_topic_name}' from company '{session_company.name if session_company else 'N/A'}'."

    if is_super_admin(acting_user):
        target_users = User.objects.filter(userprofile__company=session_company, is_staff=False) if session_company else User.objects.none()
        log_activity(acting_user, f"Admin {log_message}", target_users=target_users, company_obj=session_company)
    else:
        # Notify company admins (if acting user is not a super admin)
        target_admins = User.objects.filter(is_staff=True, userprofile__company=session_company) if session_company else User.objects.filter(is_staff=True)
        # Also log for the user themselves if they are not an admin being notified
        current_targets = list(target_admins)
        if acting_user not in current_targets:
             current_targets.append(acting_user)
        log_activity(acting_user, log_message, target_users=list(set(current_targets)), company_obj=session_company)


    session.delete()
    messages.success(request, "Session deleted successfully.")
    return redirect("session_list")


# Company CRUD Views
@login_required
@user_passes_test(is_admin) # Assuming only super admins can manage companies
def company_list_view(request):
    companies = Company.objects.all().order_by("name")
    return render(request, "session/company/company_list.html", {"companies": companies})

@login_required
@user_passes_test(is_admin)
def company_create_view(request):
    if request.method == "POST":
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save()
            # Activity is about a specific company, so log it with that company context
            # Target users for this might be other super admins, or just the acting admin.
            log_activity(request.user, f"Created new company: '{company.name}'.", company_obj=company)
            messages.success(request, f"Company '{company.name}' created successfully.")
            return redirect("company_list")
    else:
        form = CompanyForm()
    return render(request, "session/company/company_form.html", {"form": form, "action": "Create"})

@login_required
@user_passes_test(is_admin)
def company_detail_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    # Add more context if needed, e.g., users in this company, departments, etc.
    return render(request, "session/company/company_detail.html", {"company": company})

@login_required
# @user_passes_test(is_admin) # Removing this, custom check below
def company_edit_view(request, pk):
    company = get_object_or_404(Company, pk=pk)

    # Permission Check: Super admin OR Company admin of THIS company
    if not (is_super_admin(request.user) or is_company_admin(request.user, company_obj=company)):
        messages.error(request, "You do not have permission to edit this company.")
        return redirect("company_list" if is_super_admin(request.user) else "dashboard")

    if request.method == "POST":
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            updated_company = form.save()
            log_activity(request.user, f"Updated company: '{updated_company.name}'.", company_obj=updated_company)
            messages.success(request, f"Company '{updated_company.name}' updated successfully.")
            if is_super_admin(request.user):
                return redirect("company_list")
            else: # Company Admin edited their own company
                return redirect(reverse("company_detail", args=[updated_company.pk])) # Redirect to company detail
    else:
        form = CompanyForm(instance=company)
    return render(request, "session/company/company_form.html", {"form": form, "company": company, "action": "Edit"})

@login_required
@user_passes_test(is_admin)
def company_delete_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == "POST":
        company_name = company.name
        # Pass the company object itself before it's deleted
        log_activity(request.user, f"Deleted company: '{company_name}'.", company_obj=company)
        # Consider implications of deleting a company - e.g., what happens to associated users, data?
        # For now, a simple delete. Add more sophisticated handling if needed.
        company.delete()
        messages.success(request, f"Company '{company_name}' deleted successfully.")
        return redirect("company_list")
    return render(request, "session/company/company_confirm_delete.html", {"company": company})


@login_required
def change_password(request):
    """
    Change the current user's password.

    Returns:
        HttpResponse: Password change form or redirect.
    """
    if request.method == "POST":
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            user_company = user.userprofile.company if hasattr(user, 'userprofile') and user.userprofile else None
            log_activity(request.user, "Changed their password.", company_obj=user_company)
            messages.success(request, "Your password was successfully updated!")
            return redirect("my_profile")
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, "session/change_password.html", {"form": form})


@login_required
def create_external_topic(request):
    """
    Super Admins, Company Admins, or Managers can create a new external learning topic.

    Returns:
        HttpResponse: Form or redirect.
    """
    user = request.user # acting_user
    # Permission Check
    if not (is_super_admin(user) or is_company_admin(user) or is_manager(user)): # Check if admin/manager in their own company
        messages.error(request, "You do not have permission to create external learning topics.")
        return redirect("dashboard")

    if request.method == "POST":
        form = ExternalTopicForm(request.POST, user=user)
        if form.is_valid():
            topic = form.save(commit=False)
            if not topic.company_id and hasattr(user, 'userprofile') and user.userprofile.company:
                topic.company = user.userprofile.company

            if not topic.company_id:
                 messages.error(request, "Could not determine company for the learning topic.")
                 return render(request, "session/create_external_topic.html", {"form": form})

            topic.save()
            log_message = f"Added new learning topic: '{topic.coming_soon}' for company '{topic.company.name}'."
            if user.is_staff:
                target_users = User.objects.filter(userprofile__company=topic.company, is_staff=False)
                log_activity(request.user, f"Admin {log_message}", target_users=target_users, company_obj=topic.company)
            else:
                log_activity(request.user, log_message, company_obj=topic.company)
            messages.success(request, "New topic created successfully.")
            return redirect("learning-view")
    else:
        form = ExternalTopicForm(user=user)
    return render(request, "session/create_external_topic.html", {"form": form})


@login_required
def learning_view(request):
    """
    View all external learning topics.

    Returns:
        HttpResponse: List of topics.
    """
    user = request.user
    if user.is_staff: # Superuser/admin sees all topics from all companies
        topics = ExternalTopic.objects.all().order_by("company__name", "-created_at").select_related('company')
    elif hasattr(user, 'userprofile') and user.userprofile.company:
        # Company user sees topics for their company
        topics = (
            ExternalTopic.objects.filter(company=user.userprofile.company)
            .order_by("-created_at").select_related('company')
        )
    else: # User not staff and no company assigned
        topics = ExternalTopic.objects.none()
        messages.warning(request, "You are not associated with a company, so no learning topics can be shown.")

    paginator = Paginator(topics, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "session/learning-topic-list.html", {"sessions": page_obj}) # "sessions" key should be "topics"


@login_required
def edit_learning(request, learning_id):
    """
    Edit an existing learning topic.

    Args:
        learning_id (int): ID of the topic.

    Returns:
        HttpResponse: Form or redirect.
    """
    learning = get_object_or_404(ExternalTopic, id=learning_id)
    acting_user = request.user

    # Permission Check
    can_edit = False
    if is_super_admin(acting_user):
        can_edit = True
    elif is_company_admin(acting_user, company_obj=learning.company) or \
         is_manager(acting_user, company_obj=learning.company):
        can_edit = True

    if not can_edit:
        messages.error(request, "You do not have permission to edit this learning topic.")
        return redirect("learning-view")

    if request.method == "POST":
        form = ExternalTopicForm(request.POST, instance=learning, user=acting_user)
        if form.is_valid():
            updated_learning = form.save(commit=False)
            # Company change by non-superadmin is prevented by form logic if company field is hidden/disabled
            # Or if superadmin changes it, it's allowed.
            if not is_super_admin(acting_user) and updated_learning.company != learning.company:
                 messages.error(request, "You cannot change the company of the learning topic.")
                 return render(request, "session/edit_learning.html", {"form": form, "learning": learning})

            updated_learning.save()
            log_message = f"Updated learning topic: '{updated_learning.coming_soon}' in company '{updated_learning.company.name}'."
            if is_super_admin(acting_user):
                target_users = User.objects.filter(userprofile__company=updated_learning.company, is_staff=False)
                log_activity(acting_user, f"Admin {log_message}", target_users=target_users, company_obj=updated_learning.company)
            else:
                log_activity(acting_user, log_message, company_obj=updated_learning.company)
            messages.success(request, "Learning updated successfully.")
            return redirect("learning-view")
    else:
        form = ExternalTopicForm(instance=learning, user=acting_user)
    return render(
        request, "session/edit_learning.html", {"form": form, "learning": learning}
    )


@login_required
def delete_learning(request, learning_id):
    """
    Delete a learning topic.

    Args:
        learning_id (int): ID of the topic.

    Returns:
        HttpResponseRedirect: Redirect to learning view.
    """
    learning = get_object_or_404(ExternalTopic, id=learning_id)
    learning_company = learning.company
    learning_topic_name = learning.coming_soon
    acting_user = request.user

    # Permission Check
    can_delete = False
    if is_super_admin(acting_user):
        can_delete = True
    elif is_company_admin(acting_user, company_obj=learning_company) or \
         is_manager(acting_user, company_obj=learning_company):
        can_delete = True

    if not can_delete:
        messages.error(request, "You do not have permission to delete this learning topic.")
        return redirect("learning-view")

    log_message = f"Deleted learning topic: '{learning_topic_name}' from company '{learning_company.name if learning_company else 'N/A'}'."

    if is_super_admin(acting_user):
        target_users = User.objects.filter(userprofile__company=learning_company, is_staff=False) if learning_company else User.objects.none()
        log_activity(acting_user, f"Admin {log_message}", target_users=target_users, company_obj=learning_company)
    else:
        target_admins = User.objects.filter(is_staff=True, userprofile__company=learning_company) if learning_company else User.objects.filter(is_staff=True)
        current_targets = list(target_admins)
        if acting_user not in current_targets: # Log for self if not part of admin group already
            current_targets.append(acting_user)
        log_activity(acting_user, log_message, target_users=list(set(current_targets)), company_obj=learning_company)

    learning.delete()
    messages.success(request, "Learning deleted successfully.")
    return redirect("learning-view")


@login_required
def recent_activities(request):
    """
    View recent activities for the logged-in user.

    Returns:
        HttpResponse: List of recent activity logs.
    """
    RecentActivity.objects.filter(user=request.user, read=False).update(read=True)
    activities = RecentActivity.objects.filter(user=request.user).order_by(
        "-timestamp"
    )[:20]
    paginator = Paginator(activities, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "session/recent_activities.html", {"activities": page_obj})


@login_required
def department_list(request):
    user = request.user
    if user.is_staff: # Superuser/admin sees all departments
        departments = Department.objects.all().order_by("company__name", "name").select_related('company')
    elif hasattr(user, 'userprofile') and user.userprofile.company: # Company user sees their company's departments
        departments = Department.objects.filter(company=user.userprofile.company).order_by("name").select_related('company')
    else: # User not staff and no company assigned
        departments = Department.objects.none()
        messages.warning(request, "You are not associated with a company, so no departments can be shown.")

    return render(request, "session/department_list.html", {"departments": departments})


@login_required
def department_create(request):
    # Permission Check: Must be Super Admin or a Company Admin
    acting_user_profile = getattr(request.user, 'userprofile', None)
    if not (is_super_admin(request.user) or (acting_user_profile and acting_user_profile.role == 'ADMIN')):
        messages.error(request, "You do not have permission to create departments.")
        return redirect("dashboard")

    if request.method == "POST":
        form = DepartmentForm(request.POST, user=request.user)
        if form.is_valid():
            department = form.save(commit=False)
            if not department.company_id and hasattr(request.user, 'userprofile') and request.user.userprofile.company:
                department.company = request.user.userprofile.company
            # Ensure company is set, especially if hidden in form for non-staff
            # Or raise error if company cannot be determined
            if not department.company_id and request.user.is_staff:
                 messages.error(request, "Company must be selected for the department by an admin.")
                 return render(request, "session/department_form.html", {"form": form, "action": "Create"})
            elif not department.company_id and not request.user.is_staff:
                 messages.error(request, "Cannot create department: your user profile is not associated with a company.")
                 return render(request, "session/department_form.html", {"form": form, "action": "Create"})

            department.save()
            log_activity(
                request.user,
                f"Created new department: '{department.name}'.", # Log message is now simpler as company is in activity record
                company_obj=department.company
            )
            messages.success(request, "Department created successfully.")
            return redirect("department-list")
    else:
        form = DepartmentForm(user=request.user)
    return render(request, "session/department_form.html", {"form": form, "action": "Create"})


@login_required
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)

    # Permission Check: Super Admin OR Company Admin of THIS department's company
    if not (is_super_admin(request.user) or is_company_admin(request.user, company_obj=department.company)):
        messages.error(request, "You do not have permission to edit this department.")
        return redirect("department-list")

    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department, user=request.user)
        if form.is_valid():
            updated_department = form.save()
            log_activity(
                request.user,
                f"Edited department: '{updated_department.name}'.",
                company_obj=updated_department.company
            )
            messages.success(request, "Department updated successfully.")
            return redirect("department-list")
    else:
        form = DepartmentForm(instance=department, user=request.user)
    return render(request, "session/department_form.html", {"form": form, "department": department, "action": "Edit"})


@login_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    department_company = department.company
    department_name = department.name

    # Permission Check: Super Admin OR Company Admin of THIS department's company
    if not (is_super_admin(request.user) or is_company_admin(request.user, company_obj=department_company)):
        messages.error(request, "You do not have permission to delete this department.")
        return redirect("department-list")

    department.delete()
    log_activity(
        request.user,
        f"Deleted department: '{department_name}'.",
        company_obj=department_company
    )
    messages.success(request, "Department deleted successfully.")
    return redirect("department-list")


@staff_member_required
def export_sessions(request):
    """
    Generate and download an Excel file containing all 'Pending' session data, sorted by date.
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
    Updates existing topics for the same user; creates new ones if no match.
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
                        no,
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

            except Exception as e:
                messages.error(request, f"Error processing Excel file: {str(e)}")
                return redirect("session_list")

        else:
            messages.error(request, "Invalid file upload.")
            return redirect("session_list")

    return redirect("session_list")

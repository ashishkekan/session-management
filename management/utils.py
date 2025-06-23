from django.contrib.auth.models import User

from management.models import RecentActivity, Company


def log_activity(user, description, target_users=None, edited_user=None, company_obj=None):
    """
    Log a new activity to RecentActivity model, associating with a company.

    Parameters:
    - user: The user performing the action.
    - description: The activity description.
    - target_users: List of users to notify (default: None, meaning only the user themselves).
    - edited_user: Specific user to notify in case of edit actions (default: None).
    - company_obj: The Company instance this activity pertains to. If None, tries to infer.
    """

    def get_company_for_activity(u, company_param):
        if company_param:
            return company_param
        if hasattr(u, 'userprofile') and u.userprofile and u.userprofile.company:
            return u.userprofile.company
        return None

    # Determine the primary company context for the activity
    # This logic might need refinement based on specific use cases
    activity_company = company_obj
    if not activity_company:
        # If an admin is acting, the company might be from target_users or edited_user if they all belong to the same one
        # Or it could be a system-level action without a specific company.
        # For now, let's try to infer from the acting user first.
        if hasattr(user, 'userprofile') and user.userprofile and user.userprofile.company:
            activity_company = user.userprofile.company
        elif edited_user and hasattr(edited_user, 'userprofile') and edited_user.userprofile and edited_user.userprofile.company:
            activity_company = edited_user.userprofile.company
        # If still no company, the activity might be system-wide (e.g. superadmin actions not tied to a company)
        # In this case, RecentActivity.company will remain null if the field allows it.

    # If edited_user is provided (e.g., admin editing a user), notify only that user
    if edited_user:
        company_for_log = get_company_for_activity(edited_user, activity_company)
        RecentActivity.objects.create(user=edited_user, description=description, company=company_for_log)
        return

    # If target_users is None, default to the user performing the action
    if target_users is None:
        target_users = [user]

    processed_users = set()

    # If the user is not staff (normal user), notify the admins of their company and super admins
    if not user.is_staff:
        user_company = get_company_for_activity(user, activity_company)

        # Notify admins of the user's company
        if user_company:
            company_admins = User.objects.filter(is_staff=True, userprofile__company=user_company)
            for admin in company_admins:
                if admin.id not in processed_users:
                    RecentActivity.objects.create(
                        user=admin, description=f"{user.username} - {description}", company=user_company
                    )
                    processed_users.add(admin.id)

        # Notify super admins (staff without a specific company or if different from user_company)
        super_admins = User.objects.filter(is_staff=True).exclude(userprofile__company=user_company if user_company else None)
        for admin in super_admins:
             if admin.id not in processed_users:
                RecentActivity.objects.create(
                    user=admin, description=f"{user.username} (from {user_company.name if user_company else 'N/A'}) - {description}", company=None # Or admin's company if relevant
                )
                processed_users.add(admin.id)

    # Notify the specified target users (typically for admin actions or self-actions)
    for u in target_users:
        if u.id not in processed_users: # Avoid duplicate notifications if user is also an admin
            company_for_log = get_company_for_activity(u, activity_company)
            RecentActivity.objects.create(user=u, description=description, company=company_for_log)
            processed_users.add(u.id)

# RBAC Helper Functions

def is_super_admin(user):
    """Checks if the user is a Super Admin."""
    return user.is_authenticated and user.is_staff

def get_user_role_in_company(user, company_obj=None):
    """
    Returns the user's role if they belong to the specified company_obj
    or their general role if no specific company_obj is given (but they have one).
    Returns None if user has no profile, no role, or doesn't match company_obj.
    """
    if not user.is_authenticated or not hasattr(user, 'userprofile') or not user.userprofile:
        return None

    user_profile = user.userprofile
    if company_obj:
        if user_profile.company == company_obj:
            return user_profile.role
        else: # User does not belong to the specified company for role check
            return None
    return user_profile.role # General role in their assigned company

def is_company_admin(user, company_obj=None):
    """
    Checks if the user is an Admin for the given company_obj.
    If company_obj is None, checks if they are an Admin in *any* company.
    """
    if not user.is_authenticated or user.is_staff: # Superadmins are not company admins in this context
        return False
    role = get_user_role_in_company(user, company_obj)
    return role == 'ADMIN'

def is_manager(user, company_obj=None):
    """Checks if the user is a Manager for the given company_obj or any company."""
    if not user.is_authenticated or user.is_staff:
        return False
    role = get_user_role_in_company(user, company_obj)
    return role == 'MANAGER'

def is_employee(user, company_obj=None):
    """Checks if the user is an Employee for the given company_obj or any company."""
    if not user.is_authenticated or user.is_staff:
        return False
    role = get_user_role_in_company(user, company_obj)
    return role == 'EMPLOYEE'

# More specific permission helpers could be added here, e.g.:
# def can_edit_company_settings(user, company_to_edit):
#     return is_super_admin(user) or (is_company_admin(user, company_to_edit))

# def can_manage_users_in_company(user, company_to_manage):
#     return is_super_admin(user) or (is_company_admin(user, company_to_manage))

from django.contrib.auth.models import User
from management.models import RecentActivity

def log_activity(user, action_type, description, target_users=None, edited_user=None, details=None):
    # Case: log activity for a user being edited directly
    if edited_user:
        RecentActivity.objects.create(
            user=edited_user,
            action_type=action_type,
            description=description,
            details=details
        )
        return

    # If user is None (e.g., from a signal), treat it as a system-level action
    if user is None:
        # Log activity for all admins
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            RecentActivity.objects.create(
                user=admin,
                action_type=action_type,
                description=f"[SYSTEM] {description}",
                details=details
            )
        return

    # If no target users specified, default to the acting user
    if target_users is None:
        target_users = [user]

    # If user is a normal user, notify admins
    if not user.is_staff:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            RecentActivity.objects.create(
                user=admin,
                action_type=action_type,
                description=f"{user.username} - {description}",
                details=details
            )
    else:
        # User is staff → notify target users (usually non-staff)
        for u in target_users:
            RecentActivity.objects.create(
                user=u,
                action_type=action_type,
                description=description,
                details=details
            )

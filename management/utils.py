from django.contrib.auth.models import User

from management.models import RecentActivity


def log_activity(user, description, target_users=None, edited_user=None):
    """
    Log a new activity to RecentActivity model.

    Parameters:
    - user: The user performing the action.
    - description: The activity description.
    - target_users: List of users to notify (default: None, meaning only the user themselves).
    - edited_user: Specific user to notify in case of edit actions (default: None).
    """
    # If edited_user is provided (e.g., admin editing a user), notify only that user
    if edited_user:
        RecentActivity.objects.create(user=edited_user, description=description)
        return

    # If target_users is None, default to the user performing the action
    if target_users is None:
        target_users = [user]

    # If the user is not staff (normal user), notify the admins
    if not user.is_staff:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            RecentActivity.objects.create(
                user=admin, description=f"{user.username} - {description}"
            )
    else:
        # If the user is an admin, notify the specified target users
        for u in target_users:
            RecentActivity.objects.create(user=u, description=description)

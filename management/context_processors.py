from datetime import date

from management.models import RecentActivity, Company, UserProfile


def today_notifications_count(request):
    """
    Context processor to count today's unread notifications for the authenticated user.
    Returns a dictionary with the count of unread notifications.
    """
    user = request.user
    if user.is_authenticated:
        count = RecentActivity.objects.filter(
            user=user, read=False, timestamp__date=date.today()
        ).count()
        return {"today_notification_count": count}
    return {"today_notification_count": 0}


def company_logo_processor(request):
    company_logo_url = None
    company_name = None
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        user_profile = request.user.userprofile
        if user_profile and user_profile.company and user_profile.company.logo:
            company_logo_url = user_profile.company.logo.url
            company_name = user_profile.company.name
        elif user_profile and user_profile.company: # Company exists but no logo
            company_name = user_profile.company.name

    # RBAC flags
    is_profile_super_admin = request.user.is_authenticated and request.user.is_staff

    user_profile_role = None
    user_profile_company_id = None # For specific company related links if needed
    if request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile:
        user_profile_role = request.user.userprofile.role
        if request.user.userprofile.company:
            user_profile_company_id = request.user.userprofile.company.id

    return {
        'company_logo_url': company_logo_url,
        'current_company_name': company_name,
        'is_profile_super_admin': is_profile_super_admin,
        'is_profile_company_admin': not is_profile_super_admin and user_profile_role == 'ADMIN',
        'is_profile_manager': not is_profile_super_admin and user_profile_role == 'MANAGER',
        'is_profile_employee': not is_profile_super_admin and user_profile_role == 'EMPLOYEE',
        'profile_company_id': user_profile_company_id, # Can be used to build company specific URLs
    }

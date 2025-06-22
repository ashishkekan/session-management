from datetime import date

from management.models import CompanyProfile, RecentActivity


def today_notifications_count(request):
    """
    Returns count of today's unread notifications for non-admin users only.
    Admins don't get highlighted notification badges.
    """
    user = request.user
    if user.is_authenticated and not user.is_staff:
        count = RecentActivity.objects.filter(
            user=user, read=False, timestamp__date=date.today()
        ).count()
        return {"today_notification_count": count}
    return {"today_notification_count": 0}


def company_profile(request):
    return {'company_profile': CompanyProfile.objects.first()}

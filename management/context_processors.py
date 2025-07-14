from datetime import date

from management.models import RecentActivity


def today_notifications_count(request):
    """
    Returns count of today's unread notifications for non-admin users only.
    Admins don't get highlighted notification badges.
    """
    user = request.user
    if user.is_authenticated:
        count = RecentActivity.objects.filter(
            user=user, read=False, timestamp__date=date.today()
        ).count()
        return {"today_notification_count": count}
    return {"today_notification_count": 0}

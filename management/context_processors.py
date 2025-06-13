from datetime import date

from management.models import RecentActivity


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

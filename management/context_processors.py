from datetime import date

from management.models import RecentActivity


def today_notifications_count(request):
    if request.user.is_authenticated:
        count = RecentActivity.objects.filter(
            user=request.user, read=False, timestamp__date=date.today()
        ).count()
        return {"today_notification_count": count}
    return {"today_notification_count": 0}

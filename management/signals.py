from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import SessionTopic, Department, UserProfile, ExternalTopic
from .utils import log_activity

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    log_activity(user, 'LOGIN', f"{user.username} logged in", details={'ip': request.META.get('REMOTE_ADDR')})

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    log_activity(user, 'LOGOUT', f"{user.username} logged out", details={'ip': request.META.get('REMOTE_ADDR')})

@receiver(post_save, sender=SessionTopic)
def log_session_save(sender, instance, created, **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    description = f"{'Created' if created else 'Updated'} session: {instance.topic}"
    log_activity(instance.conducted_by, action, description, details={'session_id': instance.id})

@receiver(post_delete, sender=SessionTopic)
def log_session_delete(sender, instance, **kwargs):
    log_activity(instance.conducted_by, 'DELETE', f"Deleted session: {instance.topic}", details={'session_id': instance.id})

@receiver(post_save, sender=Department)
def log_department_save(sender, instance, created,  **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    log_activity(None, action, f"{'Created' if created else 'Updated'} department: {instance.name}", details={'department_id': instance.id})

@receiver(post_delete, sender=Department)
def log_department_delete(sender, instance, **kwargs):
    log_activity(None, 'DELETE', f"Deleted department: {instance.name}", details={'department_id': instance.id})
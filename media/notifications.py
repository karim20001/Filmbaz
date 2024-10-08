from .models import Notification

def create_notification(user, message, content_type, object_id, notification_type=None):
    Notification.objects.create(
        user=user,
        message=message,
        content_type=content_type,
        object_id=object_id,
        notification_type=notification_type,
    )
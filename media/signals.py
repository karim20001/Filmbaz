import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from .models import Episode, UserShow, Show
from .notifications import create_notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Episode)
def episode_update_notification(sender, instance, created, **kwargs):
    """
    Signal to send notification when an episode is updated or created
    """
    if not created:
        show = instance.show
        user_shows = UserShow.objects.filter(show=show)

        channel_layer = get_channel_layer()

        for user_show in user_shows:
            user = user_show.user

            create_notification(
                user=user,
                message=f"A new episode of {show.name} has been updated: {instance.name}",
                content_type=ContentType.objects.get_for_model(Episode),
                object_id=instance.id,
                notification_type="episode_update",
            )

            logger.info(f"Sending real-time notification to user {user.username}")

            # Send WebSocket notification to each user
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user.id}',
                {
                    'type': 'send_notification',
                    'message': f"A new episode of {show.name} has been updated: {instance.name}"
                }
            )

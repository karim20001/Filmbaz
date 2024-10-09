import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from .models import Episode, UserShow, Show, Follow
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


@receiver(post_save, sender=Follow)
def follow_notification(sender, instance, created, **kwargs):
    follower = instance.user
    followed = instance.follow
    channel_layer = get_channel_layer()

    if created:
        """
        signal to send notification of follow or follow-request is created
        """
        if instance.is_accepted:
            create_notification(
                user=followed,
                message=f"user {follower.username} followed You",
                content_type=ContentType.objects.get_for_model(Follow),
                object_id=instance.id,
                notification_type="follow",
            )

            async_to_sync(channel_layer.group_send)(
                f'notifications_{followed.username}',
                {
                    'type': 'send_notification',
                    'message': f"user {follower.username} followed You"
                }
            )

        else:
            create_notification(
                user=followed,
                message=f"user {follower.username} requested to following You",
                content_type=ContentType.objects.get_for_model(Follow),
                object_id=instance.id,
                notification_type="follow-request",
            )

            async_to_sync(channel_layer.group_send)(
                f'notifications_{followed.username}',
                {
                    'type': 'send_notification',
                    'message': f"user {follower.username} requested to following You"
                }
            )

    else:
        """
        Signal to send notification user accepted the follow request
        """
        create_notification(
                user=follower,
                message=f"user {followed.username} accepted ypur follow request",
                content_type=ContentType.objects.get_for_model(Follow),
                object_id=instance.id,
                notification_type="follow",
            )

        async_to_sync(channel_layer.group_send)(
            f'notifications_{follower.username}',
            {
                'type': 'send_notification',
                'message': f"user {followed.username} accepted ypur follow request"
            }
        )
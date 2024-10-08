import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # The group name for each user will be 'notifications_<user_id>'
        self.user = self.scope['user']
        if self.user.is_authenticated:
            self.group_name = f'notification_{self.user.id}'

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

            await self.accept()
    
    async def disconnect(self, close_code):
        # Leave the group when the WebSocket is disconnected
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    # Receive a notification message and send it to WebSocket
    async def send_notification(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))


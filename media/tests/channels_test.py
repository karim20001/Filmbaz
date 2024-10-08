from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.contrib.auth import get_user_model
from FilmBaz.consumers import NotificationConsumer
from FilmBaz.asgi import application

class NotificationTest(TestCase):
    async def test_receive_notification(self):
        # Simulate WebSocket connection
        communicator = WebsocketCommunicator(application, f"/ws/notifications/")
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Simulate sending notification
        await communicator.send_json_to({
            'type': 'send_notification',
            'message': 'A new episode has been updated.'
        })

        # Assert that we received the notification message
        response = await communicator.receive_json_from()
        self.assertEqual(response["message"], "A new episode has been updated.")

        # Close the WebSocket connection
        await communicator.disconnect()

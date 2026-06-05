import json

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(WebsocketConsumer):

    def connect(self):

        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            self.close()
            return

        self.group_name = f"notifications_{self.user.id}"

        async_to_sync(
            self.channel_layer.group_add
        )(
            self.group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):

        async_to_sync(
            self.channel_layer.group_discard
        )(
            self.group_name,
            self.channel_name
        )

    def notification_event(self, event):

        self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "notification_type": event["notification_type"],
                    "message": event["message"],
                    "actor": event["actor"],
                }
            )
        )
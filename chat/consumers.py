import json

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser

from django.utils import timezone
from .models import ConversationMember, Message, MessageReceipt

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            self.close()
            return

        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"

        is_member = ConversationMember.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user
        ).exists()

        if not is_member:
            self.close()
            return

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.user.is_online = True
        self.user.save()

        self.broadcast_presence("online")
        self.accept()


    def broadcast_presence(self, status):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "presence_event",
                "user": self.user.username,
                "status": status,
            }
        )


    def disconnect(self, close_code):
        self.user.is_online = False
        self.user.last_seen = timezone.now()
        self.user.save()

        self.broadcast_presence("offline")

        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )


    def receive(self, text_data):
        data = json.loads(text_data)

        event_type = data.get("type")

        if event_type == "message":
            self.handle_message(data)

        elif event_type == "typing":
            self.handle_typing(data)

        elif event_type == "delivered":
            self.handle_delivered(data)

        elif event_type == "seen":
            self.handle_seen(data)

    def handle_message(self, data):
        content = data["message"]

        message = Message.objects.create(
            conversation_id=self.conversation_id,
            sender=self.user,
            content=content
        )
        recipients = ConversationMember.objects.exclude(
            user=self.user
        ).filter(
            conversation_id=self.conversation_id
        )

        for recipient in recipients:
            MessageReceipt.objects.create(
                message=message,
                user=recipient.user
            )


        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "chat_message",
                "message_id": message.id,
                "sender": self.user.username,
                "content": message.content,
                "created_at": str(message.created_at),
            }
    )
        
    def handle_typing(self, data):
        is_typing = data["is_typing"]

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "typing_event",
                "user": self.user.username,
                "is_typing": is_typing,
            }
    )

    def handle_delivered(self, data):
        message_id = data["message_id"]

        receipt = MessageReceipt.objects.filter(
            message_id=message_id,
            user=self.user
        ).first()

        if not receipt:
            return

        if not receipt.delivered:
            receipt.delivered = True
            receipt.delivered_at = timezone.now()
            receipt.save()

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "delivery_receipt_event",
                "message_id": message_id,
                "user": self.user.username,
                "status": "delivered",
            }
        )

    def handle_seen(self, data):
        message_id = data["message_id"]

        receipt = MessageReceipt.objects.filter(
            message_id=message_id,
            user=self.user
        ).first()

        if not receipt:
            return

        if not receipt.delivered:
            receipt.delivered = True
            receipt.delivered_at = timezone.now()

        if not receipt.seen:
            receipt.seen = True
            receipt.seen_at = timezone.now()

        receipt.save()

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "read_receipt_event",
                "message_id": message_id,
                "user": self.user.username,
                "status": "seen",
            }
        )

    def chat_message(self, event):
        self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message_type": event.get(
                        "message_type",
                        "text"
                    ),
                    "id": event["message_id"],
                    "sender": event["sender"],
                    "content": event["content"],
                    "attachment_url": event.get(
                        "attachment_url"
                    ),
                    "created_at": event["created_at"],
                }
            )
        )

    def typing_event(self, event):
        self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "user": event["user"],
                    "is_typing": event["is_typing"],
                }
            )
    )


    def presence_event(self, event):
        self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "user": event["user"],
                    "status": event["status"],
                }
            )
        )

    def delivery_receipt_event(self, event):
        self.send(
            text_data=json.dumps(
                {
                    "type": "delivery_receipt",
                    "message_id": event["message_id"],
                    "user": event["user"],
                    "status": event["status"],
                }
            )
        )
    
    def read_receipt_event(self, event):
        self.send(
            text_data=json.dumps(
                {
                    "type": "read_receipt",
                    "message_id": event["message_id"],
                    "user": event["user"],
                    "status": event["status"],
                }
            )
        )

    def reaction_event(self, event):
        self.send(
            text_data=json.dumps(
                {
                    "type": "reaction",
                    "message_id": event["message_id"],
                    "user": event["user"],
                    "emoji": event["emoji"],
                    "action": event["action"],
                }
            )
        )
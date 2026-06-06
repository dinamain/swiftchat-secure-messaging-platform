from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from accounts.models import User
from chat.models import (
    Conversation,
    ConversationMember,
    Message,
)
class ConversationTests(APITestCase):

    def setUp(self):

        self.user1 = User.objects.create_user(
        username="dina",
        email="dina@test.com",
        password="password123"
        )

        self.user2 = User.objects.create_user(
            username="john",
            email="john@test.com",
            password="password123"
        )
                

        self.client.force_authenticate(
            user=self.user1
        )


    
    def test_send_message(self):

        conversation = Conversation.objects.create(
            created_by=self.user1
        )

        ConversationMember.objects.create(
            conversation=conversation,
            user=self.user1
        )

        response = self.client.post(
            "/api/chat/messages/",
            {
                "conversation": conversation.id,
                "content": "Hello"
            }
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )


    def test_cannot_access_without_login(self):

        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            "/api/chat/conversations/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_create_group(self):

        response = self.client.post(
            "/api/chat/conversations/",
            {
                "name": "Developers",
                "is_group": True,
                "member_ids": [self.user2.id]
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    def test_reaction_creation(self):

        conversation = Conversation.objects.create(
            created_by=self.user1
        )

        ConversationMember.objects.create(
            conversation=conversation,
            user=self.user1
        )

        message = Message.objects.create(
            conversation=conversation,
            sender=self.user1,
            content="Hello"
        )

        response = self.client.post(
            f"/api/chat/messages/{message.id}/react/",
            {
                "emoji": "🔥"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )
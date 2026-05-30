from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    MessageUpdateSerializer,
)
from django.shortcuts import get_object_or_404
from .models import Conversation, ConversationMember, Message

from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from .models import MessageReceipt
from .serializers import UnreadCountSerializer

class ConversationCreateView(APIView):
    def post(self, request):
        serializer = ConversationSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            conversation = serializer.save()

            response_serializer = ConversationSerializer(conversation)

            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
class ConversationListView(APIView):
    def get(self, request):
        conversations = Conversation.objects.filter(
            memberships__user=request.user
        ).distinct()

        serializer = ConversationSerializer(
            conversations,
            many=True
        )

        return Response(serializer.data)
    
class MessageCreateView(APIView):
    def post(self, request):
        serializer = MessageSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            message = serializer.save()

            response_serializer = MessageSerializer(message)

            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
class MessageListView(APIView):
    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id
        )

        is_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=request.user
        ).exists()

        if not is_member:
            return Response(
                {"error": "You are not allowed to view these messages."},
                status=status.HTTP_403_FORBIDDEN
            )

        messages = conversation.messages.all().order_by("created_at")

        serializer = MessageSerializer(
            messages,
            many=True
        )

        return Response(serializer.data)
    
class MessageUpdateView(APIView):
    def patch(self, request, message_id):
        message = get_object_or_404(
            Message,
            id=message_id
        )

        if message.sender != request.user:
            return Response(
                {"error": "You can only edit your own messages."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MessageUpdateSerializer(
            message,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            updated_message = serializer.save()

            response_serializer = MessageSerializer(updated_message)

            return Response(response_serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
class MessageDeleteView(APIView):
    def delete(self, request, message_id):
        message = get_object_or_404(
            Message,
            id=message_id
        )

        if message.sender != request.user:
            return Response(
                {"error": "You can only delete your own messages."},
                status=status.HTTP_403_FORBIDDEN
            )

        message.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    



class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_counts = (
            MessageReceipt.objects.filter(
                user=request.user,
                seen=False
            )
            .values("message__conversation_id")
            .annotate(unread_count=Count("id"))
        )

        formatted_data = [
            {
                "conversation_id": item["message__conversation_id"],
                "unread_count": item["unread_count"],
            }
            for item in unread_counts
        ]

        serializer = UnreadCountSerializer(formatted_data, many=True)

        return Response(serializer.data)
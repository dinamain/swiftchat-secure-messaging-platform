from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    MessageUpdateSerializer,
    AddMemberSerializer,
    TransferOwnershipSerializer,
    RenameGroupSerializer,
    GroupDetailsSerializer,
    MessageReactionSerializer,
)
from django.shortcuts import get_object_or_404
from .models import Conversation, ConversationMember, Message, MessageReaction

from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from .models import MessageReceipt
from .serializers import UnreadCountSerializer

from django.contrib.auth import get_user_model
from .pagination import MessagePagination

from rest_framework.parsers import (
    MultiPartParser,
    FormParser
)
from notifications.models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()

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
    parser_classes = [
        MultiPartParser,
        FormParser
    ]

    def post(self, request):
        serializer = MessageSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            message = serializer.save()

            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                f"chat_{message.conversation.id}",
                {
                    "type": "chat_message",
                    "message_id": message.id,
                    "sender": request.user.email,
                    "content": message.content,
                    "attachment_url": (
                        request.build_absolute_uri(
                            message.attachment.url
                        )
                        if message.attachment
                        else None
                    ),
                    "reply_to": (
                    {
                        "id": message.reply_to.id,
                        "sender": message.reply_to.sender.email,
                        "content": message.reply_to.content,
                    }
                    if message.reply_to
                    else None
                ),
                "message_type": (
                    "file"
                    if message.attachment
                    else "text"
                ),
                "created_at": str(message.created_at),
            }
        )

        response_serializer = MessageSerializer(
            message,
            context={"request": request}
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
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

        messages = conversation.messages.all().order_by("-created_at")

        paginator = MessagePagination()

        page = paginator.paginate_queryset(
            messages,
            request
        )

        serializer = MessageSerializer(
            page,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )
    
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
    

class AddMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id
        )

        if not conversation.is_group:
            return Response(
                {
                    "error": "This operation is only allowed for group conversations."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if conversation.created_by != request.user:
            return Response(
                {
                    "error": "Only group creator can add members."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]

        user = get_object_or_404(
            User,
            id=user_id
        )

        membership_exists = ConversationMember.objects.filter(
            conversation=conversation,
            user=user
        ).exists()

        if membership_exists:
            return Response(
                {
                    "error": "User is already a member."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        ConversationMember.objects.create(
            conversation=conversation,
            user=user
        )
        Notification.objects.create(
            recipient=user,
            actor=request.user,
            notification_type="group",
            message=(
                f"{request.user.email} added you "
                f"to {conversation.name}"
            )
        )
        return Response(
            {
                "message": f"{user.email} added successfully."
            }
        )
    
class RemoveMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, conversation_id, user_id):

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id
        )

        if not conversation.is_group:
            return Response(
                {
                    "error": "This operation is only allowed for group conversations."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if conversation.created_by != request.user:
            return Response(
                {
                    "error": "Only group creator can remove members."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        membership = ConversationMember.objects.filter(
            conversation=conversation,
            user_id=user_id
        ).first()

        if not membership:
            return Response(
                {
                    "error": "User is not a member."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if membership.user == conversation.created_by:
            return Response(
                {
                    "error": "Creator cannot be removed."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        membership.delete()

        return Response(
            {
                "message": "Member removed successfully."
            }
        )
    
class LeaveGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id
        )

        if not conversation.is_group:
            return Response(
                {
                    "error": "Direct conversations cannot be left."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if conversation.created_by == request.user:
            return Response(
                {
                    "error": "Transfer ownership before leaving."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        membership = ConversationMember.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()

        if not membership:
            return Response(
                {
                    "error": "You are not a member of this group."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        membership.delete()

        return Response(
            {
                "message": "You left the group successfully."
            }
        )

    
class DeleteGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, conversation_id):

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id
        )

        if not conversation.is_group:
            return Response(
                {
                    "error": "Only group conversations can be deleted."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if conversation.created_by != request.user:
            return Response(
                {
                    "error": "Only the creator can delete this group."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        deleted_count, details = conversation.delete()

        return Response(
            {
                "deleted_count": deleted_count,
                "details": details,
            }
        )
    
class TransferOwnershipView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id
        )

        if not conversation.is_group:
            return Response(
                {
                    "error": "Only group conversations support ownership transfer."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if conversation.created_by != request.user:
            return Response(
                {
                    "error": "Only the creator can transfer ownership."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TransferOwnershipSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        new_owner_id = serializer.validated_data["new_owner_id"]

        membership_exists = ConversationMember.objects.filter(
            conversation=conversation,
            user_id=new_owner_id
        ).exists()

        if not membership_exists:
            return Response(
                {
                    "error": "New owner must be a member of the group."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        conversation.created_by_id = new_owner_id
        conversation.save()

        return Response(
            {
                "message": "Ownership transferred successfully."
            }
        )
    

class RenameGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, conversation_id):

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id
        )

        if not conversation.is_group:
            return Response(
                {
                    "error": "Only group conversations can be renamed."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if conversation.created_by != request.user:
            return Response(
                {
                    "error": "Only the creator can rename the group."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RenameGroupSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        conversation.name = serializer.validated_data["name"]
        conversation.save()

        return Response(
            {
                "message": "Group renamed successfully.",
                "group_name": conversation.name
            }
        )
    
class GroupDetailsView(APIView):
    permission_classes = [IsAuthenticated]

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
                {
                    "error": "You are not a member of this conversation."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        members = ConversationMember.objects.filter(
            conversation=conversation
        )

        data = {
            "id": conversation.id,
            "name": conversation.name,
            "is_group": conversation.is_group,
            "created_by": conversation.created_by.email,
            "member_count": members.count(),
            "members": [
                {
                    "id": member.user.id,
                    "email": member.user.email,
                }
                for member in members
            ]
        }

        serializer = GroupDetailsSerializer(data)

        return Response(serializer.data)
    

class MessageSearchView(APIView):
    permission_classes = [IsAuthenticated]

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
                {
                    "error": "You are not a member of this conversation."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        query = request.GET.get("q")

        if not query:
            return Response(
                {
                    "error": "Search query is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        messages = (
            Message.objects.filter(
                conversation=conversation
            )
            .filter(
                Q(content__icontains=query)
                |
                Q(sender__email__icontains=query)
            )
            .order_by("-created_at")
        )

        paginator = MessagePagination()

        page = paginator.paginate_queryset(
            messages,
            request
        )

        serializer = MessageSerializer(
            page,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )

class MessageReactionView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):

        message = get_object_or_404(
            Message,
            id=message_id
        )

        emoji = request.data.get("emoji")

        if not emoji:
            return Response(
                {
                    "error": "Emoji is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        channel_layer = get_channel_layer()

        existing_reaction = MessageReaction.objects.filter(
            message=message,
            user=request.user,
            emoji=emoji
        ).first()

        # REMOVE REACTION
        if existing_reaction:

            existing_reaction.delete()

            async_to_sync(channel_layer.group_send)(
                f"chat_{message.conversation.id}",
                {
                    "type": "reaction_event",
                    "message_id": message.id,
                    "user": request.user.email,
                    "emoji": emoji,
                    "action": "removed",
                }
            )

            return Response(
                {
                    "action": "removed",
                    "emoji": emoji,
                    "message_id": message.id,
                }
            )

       # ADD REACTION
        reaction = MessageReaction.objects.create(
            message=message,
            user=request.user,
            emoji=emoji
        )

        # Create notification
        if message.sender != request.user:

            notification = Notification.objects.create(
                recipient=message.sender,
                actor=request.user,
                notification_type="reaction",
                message=f"{request.user.email} reacted {emoji} to your message"
            )

            # Realtime notification
            async_to_sync(channel_layer.group_send)(
                f"notifications_{message.sender.id}",
                {
                    "type": "notification_event",
                    "notification_type": notification.notification_type,
                    "message": notification.message,
                    "actor": request.user.email,
                }
            )

        # Realtime reaction event
        async_to_sync(channel_layer.group_send)(
            f"chat_{message.conversation.id}",
            {
                "type": "reaction_event",
                "message_id": message.id,
                "user": request.user.email,
                "emoji": emoji,
                "action": "added",
            }
        )

        serializer = MessageReactionSerializer(
            reaction
        )

        return Response(
            {
                "action": "added",
                "reaction": serializer.data,
            },
            status=status.HTTP_201_CREATED
        )
    
class PinMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):

        message = get_object_or_404(
            Message,
            id=message_id
        )

        membership_exists = ConversationMember.objects.filter(
            conversation=message.conversation,
            user=request.user
        ).exists()

        if not membership_exists:
            return Response(
                {
                    "error": "You are not a member of this conversation."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        message.is_pinned = not message.is_pinned
        message.save()

        return Response(
            {
                "message_id": message.id,
                "is_pinned": message.is_pinned,
            }
        )
    
class PinnedMessagesView(APIView):
    permission_classes = [IsAuthenticated]

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
                {
                    "error": "You are not a member of this conversation."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        messages = Message.objects.filter(
            conversation=conversation,
            is_pinned=True
        ).order_by("-created_at")

        serializer = MessageSerializer(
            messages,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)
    
class ForwardMessageView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):

        original_message = get_object_or_404(
            Message,
            id=message_id
        )

        target_conversation_id = request.data.get(
            "conversation_id"
        )

        conversation = get_object_or_404(
            Conversation,
            id=target_conversation_id
        )


        membership_exists = ConversationMember.objects.filter(
            conversation=conversation,
            user=request.user
        ).exists()

        if not membership_exists:
            return Response(
                {
                    "error": "You are not a member of this conversation."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        forwarded_message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=original_message.content,
            attachment=original_message.attachment,
            forwarded_from=original_message,
        )
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation.id}",
            {
                "type": "chat_message",
                "message_id": forwarded_message.id,
                "sender": request.user.email,
                "content": forwarded_message.content,
                "attachment_url": (
                    request.build_absolute_uri(
                        forwarded_message.attachment.url
                    )
                    if forwarded_message.attachment
                    else None
                ),
                "message_type": (
                    "file"
                    if forwarded_message.attachment
                    else "text"
                ),
                "forwarded_from": (
                    {
                        "id": original_message.id,
                        "sender": original_message.sender.email,
                        "content": original_message.content,
                    }
                ),
                "created_at": str(
                    forwarded_message.created_at
                ),
            }
        )

        serializer = MessageSerializer(
            forwarded_message,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
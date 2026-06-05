from rest_framework import serializers
from .models import (
    Conversation,
    ConversationMember,
    Message,
    MessageReaction,
)
from notifications.models import Notification

class ConversationSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "name",
            "is_group",
            "member_ids",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        member_ids = attrs.get("member_ids", [])
        is_group = attrs.get("is_group", False)
        name = attrs.get("name")

        user = self.context["request"].user

        # DIRECT CHAT
        if not is_group:

            if len(member_ids) != 1:
                raise serializers.ValidationError(
                    "Direct conversations must have exactly one participant."
                )

            # Prevent chatting with yourself
            if member_ids[0] == user.id:
                raise serializers.ValidationError(
                    "You cannot create a conversation with yourself."
                )

            # Direct chats don't need names
            attrs["name"] = None

        # GROUP CHAT
        else:

            if not name:
                raise serializers.ValidationError(
                    "Group conversations require a name."
                )

            # Count members excluding creator
            other_members = [
                member_id
                for member_id in member_ids
                if member_id != user.id
            ]

            if len(other_members) < 1:
                raise serializers.ValidationError(
                    "Group conversations must have at least one participant besides the creator."
                )

        return attrs

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", [])
        user = self.context["request"].user

        conversation = Conversation.objects.create(
            created_by=user,
            **validated_data
        )

        # Add creator automatically
        ConversationMember.objects.create(
            conversation=conversation,
            user=user
        )

        # Add other members
        for member_id in member_ids:

            # Skip creator if included accidentally
            if member_id == user.id:
                continue

            membership_exists = ConversationMember.objects.filter(
                conversation=conversation,
                user_id=member_id
            ).exists()

            if not membership_exists:
                ConversationMember.objects.create(
                    conversation=conversation,
                    user_id=member_id
                )

        return conversation
    
class ReplyMessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField()

    class Meta:
        model = Message
        fields = [
            "id",
            "sender",
            "content",
        ]

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)
    attachment_url = serializers.SerializerMethodField()
    reply_to = ReplyMessageSerializer(
    read_only=True
)
    reply_to_id = serializers.IntegerField(
    write_only=True,
    required=False,
    allow_null=True
)
    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "content",
            "attachment",
            "attachment_url",
            "reply_to",
            "reply_to_id",
            "is_pinned",
            "is_edited",
            "created_at",
        ]

    def get_attachment_url(self, obj):
        request = self.context.get("request")

        if obj.attachment:
            if request:
                return request.build_absolute_uri(
                    obj.attachment.url
                )

            return obj.attachment.url

        return None

    def validate_attachment(self, attachment):

        allowed_extensions = [
            ".jpg",
            ".jpeg",
            ".png",
            ".pdf",
            ".docx",
        ]

        allowed_content_types = [
            "image/jpeg",
            "image/png",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]

        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

        filename = attachment.name.lower()

        # Extension validation
        if not any(
            filename.endswith(ext)
            for ext in allowed_extensions
        ):
            raise serializers.ValidationError(
                "Only JPG, PNG, PDF and DOCX files are allowed."
            )

        # MIME validation
        if attachment.content_type not in allowed_content_types:
            raise serializers.ValidationError(
                "Invalid file type."
            )

        # Size validation
        if attachment.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                "Maximum file size is 10 MB."
            )

        return attachment
        

    def validate(self, attrs):
        content = attrs.get("content")
        attachment = attrs.get("attachment")

        if not content and not attachment:
            raise serializers.ValidationError(
                "Message must contain text or attachment."
            )

        return attrs

    def validate_conversation(self, conversation):
        user = self.context["request"].user

        is_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=user
        ).exists()

        if not is_member:
            raise serializers.ValidationError(
                "You are not a member of this conversation."
            )

        return conversation

    def create(self, validated_data):

        user = self.context["request"].user

        reply_to_id = validated_data.pop(
            "reply_to_id",
            None
        )

        reply_to = None

        if reply_to_id:
            reply_to = Message.objects.filter(
                id=reply_to_id
            ).first()

        message = Message.objects.create(
            sender=user,
            reply_to=reply_to,
            **validated_data
        )

        # Reply notification
        if (
            reply_to
            and reply_to.sender != user
        ):
            Notification.objects.create(
                recipient=reply_to.sender,
                actor=user,
                notification_type="reply",
                message=f"{user.email} replied to your message"
            )

        return message
        
class MessageUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["content"]

    def update(self, instance, validated_data):
        instance.content = validated_data["content"]
        instance.is_edited = True
        instance.save()
        return instance
    
class UnreadCountSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    unread_count = serializers.IntegerField()

class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class TransferOwnershipSerializer(serializers.Serializer):
    new_owner_id = serializers.IntegerField()

class RenameGroupSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255
    )

class GroupMemberSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()

class GroupDetailsSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    is_group = serializers.BooleanField()
    created_by = serializers.CharField()
    member_count = serializers.IntegerField()
    members = GroupMemberSerializer(many=True)

class MessageReactionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = MessageReaction
        fields = [
            "id",
            "message",
            "user",
            "emoji",
            "created_at",
        ]
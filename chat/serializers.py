from rest_framework import serializers
from .models import Conversation, ConversationMember, Message


class ConversationSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    created_by = serializers.StringRelatedField()

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

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids",[])
        user = self.context["request"].user

        conversation = Conversation.objects.create(
            created_by=user,
            **validated_data
        )

        ConversationMember.objects.create(
            conversation=conversation,
            user=user
        )

        for member_id in member_ids:
            ConversationMember.objects.create(
                conversation=conversation,
                user_id=member_id
            )

        return conversation
    
class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "content",
            "is_edited",
            "created_at",
        ]

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

        message = Message.objects.create(
            sender=user,
            **validated_data
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
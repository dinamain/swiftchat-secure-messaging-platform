from django.contrib import admin
from .models import Conversation, ConversationMember, Message, MessageReceipt
admin.site.register(Conversation)
admin.site.register(ConversationMember)
admin.site.register(Message)
admin.site.register(MessageReceipt)
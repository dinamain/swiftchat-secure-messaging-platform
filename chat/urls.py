from django.urls import path
from .views import (
    ConversationCreateView, 
    ConversationListView,
    MessageCreateView,
    MessageListView,
    MessageUpdateView,
    MessageDeleteView
)

urlpatterns = [
    path("conversations/", ConversationCreateView.as_view(), name="create_conversation"),
    path("conversations/list/", ConversationListView.as_view(), name="list_conversations"),
    path("messages/", MessageCreateView.as_view(), name="send_message"),
    path(
    "conversations/<int:conversation_id>/messages/",
    MessageListView.as_view(),
    name="conversation_messages",
    ),
    path(
        "messages/<int:message_id>/",
        MessageUpdateView.as_view(),
        name="edit_message",
    ),
    path(
    "messages/<int:message_id>/delete/",
    MessageDeleteView.as_view(),
    name="delete_message",
    ),
]
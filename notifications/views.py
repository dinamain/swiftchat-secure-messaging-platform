from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        notifications = (
            Notification.objects.filter(
                recipient=request.user
            )
            .order_by("-created_at")
        )

        serializer = NotificationSerializer(
            notifications,
            many=True
        )

        return Response(serializer.data)
    from django.shortcuts import get_object_or_404


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):

        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=request.user
        )

        notification.is_read = True
        notification.save()

        return Response(
            {
                "message": "Notification marked as read."
            }
        )
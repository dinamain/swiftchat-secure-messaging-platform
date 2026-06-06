import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "swiftchat.settings"
)

from django.core.asgi import get_asgi_application

# Initialize Django FIRST
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from chat.routing import websocket_urlpatterns as chat_routes
from notifications.routing import websocket_urlpatterns as notification_routes
from swiftchat.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,

        "websocket": JWTAuthMiddleware(
            URLRouter(
                chat_routes + notification_routes
            )
        ),
    }
)
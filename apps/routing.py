from django.urls import re_path
from .consumers import StreamingConsumer

websocket_urlpatterns = [
    re_path(r"ws/auth/user/$", StreamingConsumer.as_asgi()),
    re_path(r'ws/stream/start/live/(?P<user_id>\w+)/$', StreamingConsumer.as_asgi()),
    re_path(r"ws/stream/live/join/event/(?P<event_id>[^/]+)/(?P<username>[^/]+)/(?P<participantId>[^/]+)/$", StreamingConsumer.as_asgi())
]


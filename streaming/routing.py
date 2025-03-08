from django.urls import re_path
from .consumers import AudioStreamConsumer

websocket_urlpatterns = [
    re_path(r'ws/stream/start/live/(?P<user_id>\w+)/$', AudioStreamConsumer.as_asgi()),
    re_path(r"ws/user/live/join/(?P<event_id>[^/]+)/(?P<username>[^/]+)/(?P<participantId>[^/]+)/$", AudioStreamConsumer.as_asgi())
]


from django.urls import re_path
from .consumers import VideoLiveStreamConsumer

websocket_urlpatterns = [
    re_path(r'ws/video/stream/(?P<event_id>\w+)/$', VideoLiveStreamConsumer.as_asgi()),
]

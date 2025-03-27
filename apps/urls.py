from django.urls import path, re_path
from .views import UploadRecordingAPIView, RecordedAudioStreamView, ScheduleEvent

urlpatterns = [
    path('api/recordings/', UploadRecordingAPIView.as_view(), name='recordings-list-create'),
    re_path(r'^api/recordings/(?P<pk>[0-9a-fA-F-]{36})/$', UploadRecordingAPIView.as_view(), name='recordings-detail'),
    path("api/upload-audio-stream/", RecordedAudioStreamView.as_view(), name="upload_audio_stream"),
    path('events/', ScheduleEvent.as_view(), name='create-list-events'),  # GET all events, POST new event
    path('events/<int:event_id>/', ScheduleEvent.as_view(), name='event-detail'),  # GET, PUT, DELETE specific event
]

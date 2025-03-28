from django.urls import path, re_path
from .views import UploadRecordingAPIView, RecordedAudioStreamView, ScheduleEvent

urlpatterns = [
    path('api/v1/recordings/', UploadRecordingAPIView.as_view(), name='recordings-list-create'), # Supports filtering like /api/recordings/?visibility=Public
    re_path(r'^api/v1/recordings/(?P<pk>[0-9a-fA-F-]{36})/$', UploadRecordingAPIView.as_view(), name='recordings-detail'),
    path("api/v1/upload-audio-stream/", RecordedAudioStreamView.as_view(), name="upload_audio_stream"),   # Get all & Post
    path("api/v1/upload-audio-stream/<int:audio_id>/", RecordedAudioStreamView.as_view()),  # Get by ID, Update, and Delete
    path('api/v1/events/', ScheduleEvent.as_view(), name='create-list-events'),  # GET all events, POST new event
    path('api/v1/events/<int:event_id>/', ScheduleEvent.as_view(), name='event-detail'),  # GET, PUT, DELETE specific event
]

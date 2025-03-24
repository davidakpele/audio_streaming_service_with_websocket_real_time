from django.urls import path, re_path
from .views import UploadRecordingAPIView, RecordedAudioStreamView

urlpatterns = [
    path('api/recordings/', UploadRecordingAPIView.as_view(),
         name='recordings-list-create'),
    re_path(r'^api/recordings/(?P<pk>[0-9a-fA-F-]{36})/$',
            UploadRecordingAPIView.as_view(), name='recordings-detail'),
    path("api/upload-audio-stream/", RecordedAudioStreamView.as_view(),
         name="upload_audio_stream"),
]

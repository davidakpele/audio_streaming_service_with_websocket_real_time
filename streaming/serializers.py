from rest_framework import serializers
from .models import UploadRecording


class UploadRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadRecording
        fields = '__all__'

    def validate_music(self, value):
        allowed_types = ['audio/mpeg', 'audio/mp3', 'video/mp4']
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Only MP3 or MP4 files are allowed.")
        return value

    def validate_theme(self, value):
        allowed_types = ['image/jpeg', 'image/png']
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Only JPEG or PNG images are allowed.")
        return value

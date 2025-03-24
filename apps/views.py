from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import UploadAudioRecord, RecordedAudioStream
from .serializers import RecordedAudioStreamSerializer, UploadRecordingSerializer
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from urllib.parse import urlparse


class UploadRecordingAPIView(APIView):
    @staticmethod
    def format_recording(recording, request):
        def get_absolute_url(file_field):
            """Ensure the URL is absolute and avoid double encoding"""
            if not file_field:
                return None  # Return None if the field is empty

            file_url = str(file_field)  # Convert FieldFile to string
            # If it's a relative path, prepend MEDIA_URL
            if not urlparse(file_url).scheme:
                return request.build_absolute_uri(settings.MEDIA_URL + file_url)
            return file_url  # Already an absolute URL, return as is

        return {
            "id": str(recording.id),
            "record_title": recording.record_title,
            "description": recording.description,
            "visibility": recording.visibility,
            "file": get_absolute_url(recording.file),
            "theme": get_absolute_url(recording.theme),
            "created_at": recording.created_at,
        }

    def get(self, request, pk=None):
        if pk:
            recording = get_object_or_404(UploadAudioRecord, id=pk)
            return Response(self.format_recording(recording, request), status=status.HTTP_200_OK)

        recordings = UploadAudioRecord.objects.all()
        formatted_recordings = [self.format_recording(
            recording, request) for recording in recordings]
        return Response(formatted_recordings, status=status.HTTP_200_OK)

    def post(self, request: HttpRequest):
        if not request.data:
            return Response({"error": "Request data is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate music file
        music_file = request.FILES.get("music")
        if not music_file:
            return Response({"error": "Music file is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not self.is_valid_music(music_file):
            return Response({"error": "Invalid music file format. Allowed: MP3, MP4"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate theme image
        theme_file = request.FILES.get("theme")
        if theme_file and not self.is_valid_image(theme_file):
            return Response({"error": "Invalid image format. Allowed: JPEG, PNG"}, status=status.HTTP_400_BAD_REQUEST)

        # Get full base URL dynamically
        protocol = "https" if request.is_secure() else "http"
        domain = request.get_host()
        base_url = f"{protocol}://{domain}"

        # Save music file
        music_filename = default_storage.save(
            f"uploads/music/{music_file.name}", ContentFile(music_file.read()))
        music_url = f"{base_url}/media/{music_filename}"

        # Save theme file (if exists)
        theme_url = None
        if theme_file:
            theme_filename = default_storage.save(
                f"uploads/theme/{theme_file.name}", ContentFile(theme_file.read()))
            theme_url = f"{base_url}/media/{theme_filename}"

        # Extract data from request
        record_title = request.data.get("record_title", "").strip()
        description = request.data.get("description", "").strip()
        visibility = request.data.get("visibility", "Public")
        userId = request.data.get("userId", "").strip()

        # Save to database with full URLs
        recording = UploadAudioRecord.objects.create(
            record_title=record_title,
            userId=userId,
            description=description,
            visibility=visibility,
            file=music_url,
            theme=theme_url
        )

        return Response(
            {
                "message": "Recording uploaded successfully",
                "data": {
                    "id": str(recording.id),
                    "userId": recording.serId,
                    "title": userId.record_title,
                    "description": recording.description,
                    "visibility": recording.visibility,
                    "music_url": music_url,
                    "theme_url": theme_url,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    def put(self, request, pk):
        try:
            recording = UploadAudioRecord.objects.get(pk=pk)
        except UploadAudioRecord.DoesNotExist:
            return Response({"error": "Recording not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UploadRecordingSerializer(
            recording, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            recording = UploadAudioRecord.objects.get(pk=pk)
            recording.delete()
            return Response({"message": "Recording deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except UploadAudioRecord.DoesNotExist:
            return Response({"error": "Recording not found"}, status=status.HTTP_404_NOT_FOUND)

    def is_valid_music(self, file):
        allowed_types = ['audio/mpeg', 'audio/mp3', 'video/mp4']
        return hasattr(file, 'content_type') and file.content_type in allowed_types

    def is_valid_image(self, file):
        allowed_types = ["image/jpeg", "image/jpg", "image/png"]
        return hasattr(file, 'content_type') and file.content_type in allowed_types


class RecordedAudioStreamView(APIView):
    def post(self, request):
        user_id = request.data.get("userId")
        if not user_id:
            return Response({"error": "userId is required"}, status=status.HTTP_400_BAD_REQUEST)

        if "recorded_audio_stream" not in request.FILES:
            return Response({"error": "Audio file is required"}, status=status.HTTP_400_BAD_REQUEST)

        audio_file = request.FILES["recorded_audio_stream"]

        # Validate file type
        allowed_formats = ["audio/mpeg", "audio/webm", "audio/wav"]
        if audio_file.content_type not in allowed_formats:
            return Response({"error": "Invalid audio format. Allowed: MP3, WEBM, WAV"}, status=status.HTTP_400_BAD_REQUEST)

        # Get full base URL dynamically
        protocol = "https" if request.is_secure() else "http"
        domain = request.get_host()
        base_url = f"{protocol}://{domain}{settings.MEDIA_URL}"

        # Save file
        audio_filename = default_storage.save(
            f"stream/audio/{audio_file.name}", ContentFile(audio_file.read()))
        audio_url = f"{base_url}{audio_filename}"

        # Save record in the database
        recorded_audio = RecordedAudioStream.objects.create(
            userId=user_id,
            stream_audio_file=audio_url  # Save full URL
        )

        return Response(
            {
                "message": "Recorded audio uploaded successfully",
                "data": RecordedAudioStreamSerializer(recorded_audio).data,
            },
            status=status.HTTP_201_CREATED,
        )

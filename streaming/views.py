from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import UploadRecording
from .serializers import UploadRecordingSerializer
import mimetypes


class UploadRecordingAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            try:
                recording = UploadRecording.objects.get(pk=pk)
                serializer = UploadRecordingSerializer(recording)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except UploadRecording.DoesNotExist:
                return Response({"error": "Recording not found"}, status=status.HTTP_404_NOT_FOUND)

        recordings = UploadRecording.objects.all()
        serializer = UploadRecordingSerializer(recordings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
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
            return Response({"error": "Invalid image format"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UploadRecordingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            recording = UploadRecording.objects.get(pk=pk)
        except UploadRecording.DoesNotExist:
            return Response({"error": "Recording not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UploadRecordingSerializer(
            recording, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            recording = UploadRecording.objects.get(pk=pk)
            recording.delete()
            return Response({"message": "Recording deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except UploadRecording.DoesNotExist:
            return Response({"error": "Recording not found"}, status=status.HTTP_404_NOT_FOUND)

    def is_valid_music(self, file):
        allowed_types = ["audio/mp3", "video/mp4"]
        content_type = mimetypes.guess_type(file.name)[0]
        return content_type in allowed_types

    def is_valid_image(self, file):
        allowed_types = ["image/jpeg", "image/png"]
        content_type = mimetypes.guess_type(file.name)[0]
        return content_type in allowed_types

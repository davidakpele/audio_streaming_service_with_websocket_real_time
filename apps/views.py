import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import UploadAudioRecord, RecordedAudioStream, EventSchedule
from .serializers import RecordedAudioStreamSerializer, UploadRecordingSerializer
from django.http import HttpRequest, JsonResponse
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
        
        allowed_formats = ["audio/mpeg", "audio/webm", "audio/wav"]
        if music_file.content_type not in allowed_formats:
            return Response({"error": "Invalid audio format. Allowed: MP3, WEBM, WAV"}, status=status.HTTP_400_BAD_REQUEST)

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

    # Fetch records by visibility type 
    def get(self, request, pk=None):
        visibility = request.query_params.get("visibility", None)

        if pk:
            recording = get_object_or_404(UploadAudioRecord, id=pk)
            return Response(self.format_recording(recording, request), status=status.HTTP_200_OK)

        recordings = UploadAudioRecord.objects.all()

        # Filter by visibility if provided
        if visibility:
            if visibility not in ["Public", "Private"]:
                return Response({"error": "Invalid visibility filter. Allowed values: Public, Private"},
                                status=status.HTTP_400_BAD_REQUEST)
            recordings = recordings.filter(visibility=visibility)

        formatted_recordings = [self.format_recording(recording, request) for recording in recordings]
        return Response(formatted_recordings, status=status.HTTP_200_OK)

    def is_valid_music(self, file):
        allowed_types = ['audio/mpeg', 'audio/mp3', 'video/mp4']
        return hasattr(file, 'content_type') and file.content_type in allowed_types

    def is_valid_image(self, file):
        allowed_types = ["image/jpeg", "image/jpg", "image/png"]
        return hasattr(file, 'content_type') and file.content_type in allowed_types

class RecordedAudioStreamView(APIView):
    def get(self, request, audio_id=None):
        if audio_id:
            # Get single audio by ID
            try:
                recorded_audio = RecordedAudioStream.objects.get(id=audio_id)
                return Response(RecordedAudioStreamSerializer(recorded_audio).data, status=status.HTTP_200_OK)
            except RecordedAudioStream.DoesNotExist:
                return Response({"error": "Audio not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get all recorded audio
            all_audio = RecordedAudioStream.objects.all()
            return Response(RecordedAudioStreamSerializer(all_audio, many=True).data, status=status.HTTP_200_OK)

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

    def put(self, request, audio_id):
        try:
            recorded_audio = RecordedAudioStream.objects.get(id=audio_id)
        except RecordedAudioStream.DoesNotExist:
            return Response({"error": "Audio not found"}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get("userId")
        new_audio_file = request.FILES.get("recorded_audio_stream")

        if user_id:
            recorded_audio.userId = user_id  # Update user ID if provided

        if new_audio_file:
            # Validate file type
            allowed_formats = ["audio/mpeg", "audio/webm", "audio/wav"]
            if new_audio_file.content_type not in allowed_formats:
                return Response({"error": "Invalid audio format. Allowed: MP3, WEBM, WAV"}, status=status.HTTP_400_BAD_REQUEST)

            # Delete old audio file
            if recorded_audio.stream_audio_file:
                old_file_path = recorded_audio.stream_audio_file.replace(settings.MEDIA_URL, "")
                default_storage.delete(old_file_path)

            # Save new file
            protocol = "https" if request.is_secure() else "http"
            domain = request.get_host()
            base_url = f"{protocol}://{domain}{settings.MEDIA_URL}"

            audio_filename = default_storage.save(
                f"stream/audio/{new_audio_file.name}", ContentFile(new_audio_file.read()))
            recorded_audio.stream_audio_file = f"{base_url}{audio_filename}"

        recorded_audio.save()

        return Response(
            {
                "message": "Recorded audio updated successfully",
                "data": RecordedAudioStreamSerializer(recorded_audio).data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, audio_id):
        try:
            recorded_audio = RecordedAudioStream.objects.get(id=audio_id)
            recorded_audio.delete()
            return Response({"message": "Audio deleted successfully"}, status=status.HTTP_200_OK)
        except RecordedAudioStream.DoesNotExist:
            return Response({"error": "Audio not found"}, status=status.HTTP_404_NOT_FOUND)

class ScheduleEvent(APIView):
    def post(self, request):
        try:
            data = json.loads(request.body)

            required_fields = ["event_title", "startTime", "startYear",
                               "endTime", "endYear", "category", "theme"]

            for field in required_fields:
                if field not in data:
                    return JsonResponse({"error": f"Missing required field: {field}"}, status=400)

            if "themeImage" not in request.FILES:
                return JsonResponse({"error": "Missing required file: themeImage"}, status=400)

            # Validate theme image
            theme_file = request.FILES.get("themeImage")
            if theme_file and not self.is_valid_image(theme_file):
                return Response({"error": "Invalid image format. Allowed: JPEG, PNG"}, status=status.HTTP_400_BAD_REQUEST)

            # Get full base URL dynamically
            protocol = "https" if request.is_secure() else "http"
            domain = request.get_host()
            base_url = f"{protocol}://{domain}"

            # Save theme file (if exists)
            theme_url = None
            if theme_file:
                theme_filename = default_storage.save(
                    f"uploads/theme/{theme_file.name}", ContentFile(theme_file.read()))
                theme_url = f"{base_url}/media/{theme_filename}"
           
            # Extract data from request
            event_title = request.data.get("event_title", "").strip()
            startTime = request.data.get("startTime", "")
            startYear = request.data.get("startYear", "")
            endTime = request.data.get("endTime", "")
            endYear = request.data.get("endYear", "")
            category = request.data.get("category", "")
            userId = request.data.get("userId", "").strip()

            # Save to database with full URLs
            recording = EventSchedule.objects.create(
                event_title=event_title,
                userId=userId,
                startTime=startTime,
                startYear=startYear,
                endTime=endTime,
                endYear=endYear,
                category=category,
                theme=theme_url
            )

            return JsonResponse({
                "message": "Event scheduled successfully",
                "event": {
                    "title": data["event_title"],
                    "startTime": data["startTime"],
                    "startYear": data["startYear"],
                    "endTime": data["endTime"],
                    "endYear": data["endYear"],
                    "category": data["category"],
                    "theme": data["theme"],
                    "themeImage": theme_url
                }
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def get(self, request, event_id=None):
        try:
            if event_id:
                event = EventSchedule.objects.filter(id=event_id).first()
                if not event:
                    return JsonResponse({"error": "Event not found"}, status=404)
                return JsonResponse({
                    "event": {
                        "title": event.event_title,
                        "startTime": event.startTime,
                        "startYear": event.startYear,
                        "endTime": event.endTime,
                        "endYear": event.endYear,
                        "category": event.category,
                        "theme": event.theme
                    }
                })
            else:
                events = EventSchedule.objects.all().values()
                return JsonResponse({"events": list(events)}, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request, event_id):
        try:
            event = EventSchedule.objects.filter(id=event_id).first()
            if not event:
                return JsonResponse({"error": "Event not found"}, status=404)
            event.delete()
            return JsonResponse({"message": "Event deleted successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    def put(self, request, event_id):
        try:
            data = json.loads(request.body)
            event = EventSchedule.objects.filter(id=event_id).first()
            if not event:
                return JsonResponse({"error": "Event not found"}, status=404)

            for key, value in data.items():
                if hasattr(event, key):
                    setattr(event, key, value)
            event.save()

            return JsonResponse({"message": "Event updated successfully"}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

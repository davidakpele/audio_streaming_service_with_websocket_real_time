import base64
from datetime import datetime
import json
from django.utils.timezone import now
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from streaming.models import Participant, Room, StreamType

# Active streams storage (Replace with database later)
active_streams = {}

class AudioStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle both stream start and join based on URL."""
        self.scope_params = self.scope["url_route"]["kwargs"]
        self.user_id = self.scope_params.get("user_id", None)  # Broadcaster ID
        self.event_id = self.scope_params.get("event_id", None)  # Event ID
        self.participant_id = self.scope_params.get("participantId", None)  # Participant ID
        self.username = self.scope_params.get("username", "Guest")  # Default username

        if self.user_id is not None:
            # Host starts a new stream
            self.event_id = str(uuid.uuid4())

            # Save to Room table
            await self.create_room(self.event_id, self.user_id)

            active_streams[self.event_id] = {
                "host": self.user_id,
                "status": "active",
                "participants": {},
                "chat_history": [],
            }
            self.room_group_name = f"user_audio_live_{self.event_id}"

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Send event_id and join_url to the host
            join_url = f"ws://127.0.0.1:8000/ws/user/live/join/{self.event_id}/"
            await self.send(text_data=json.dumps({
                "event_id": self.event_id,
                "join_url": join_url
            }))

        elif self.event_id is not None:
             # Participant joins existing stream
            if not await self.room_exists(self.event_id):
                await self.close()
                return
            
            # Save participant to DB
            await self.add_participant(self.event_id, self.participant_id, self.username)

            # Use participantId instead of userId for tracking
            active_streams[self.event_id]["participants"][self.channel_name] = {
                "username": self.username,
                "participant_id": self.participant_id
            }
            self.room_group_name = f"user_audio_live_{self.event_id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Send chat history to new participant
            await self.send_chat_history()

            # Broadcast participant count and join message
            await self.broadcast_participant_count()
            await self.broadcast_message(
                f"{self.username} joined live.",
                self.username,
                self.participant_id,
                event_type="participant_joined"
            )

    async def receive(self, text_data=None, bytes_data=None):
        """Handle WebSocket messages for both text-based control and binary audio streaming."""
        if text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get("type")

                if message_type == "stream_ended":
                    """Host ends the stream"""
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "stream_ended",
                            "message": "The live stream has ended.",
                        }
                    )
                    await self.close()
                    
                    """Update Room table when the broadcaster ends streaming."""
                    room = await database_sync_to_async(Room.objects.get)(room_id=self.event_id)
                    room.status = "end"
                    room.end_timestamp = now()
                    await database_sync_to_async(room.save)()

                elif message_type == "audio":
                    audio_data = data.get("audio_data")

                    # Decode Base64 if the frontend mistakenly sends encoded audio
                    if isinstance(audio_data, str):
                        try:
                            audio_data = base64.b64decode(audio_data)
                        except Exception as e:
                            print(f"Error decoding Base64 audio data: {e}")
                            return

                    # Broadcast decoded audio data
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "broadcast_audio",
                            "audio_data": audio_data
                        }
                    )

                elif message_type == "text":
                    text_message = data.get("message", "").strip()
                    if text_message:
                        await self.broadcast_message(text_message, self.username, self.participant_id)

            except json.JSONDecodeError as e:
                print(f"Invalid JSON received: {e}")
                return

        elif bytes_data:
            # Directly relay binary audio data for real-time streaming
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast_audio",
                    "audio_data": bytes_data
                }
            )

    async def broadcast_audio(self, event):
        """Send received audio data to all connected clients, including the host."""
        await self.send(bytes_data=event["audio_data"])

    async def broadcast_participant_count(self):
        """Send participant count to all connected users."""
        if self.event_id in active_streams:
            participant_count = len(
                active_streams[self.event_id]["participants"])

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "update_participant_count",
                    "event_id": self.event_id,
                    "count": participant_count,
                }
            )

    async def update_participant_count(self, event):
        """Broadcast participant count update to all users."""
        await self.send(text_data=json.dumps({
            "type": "participant_count",
            "count": event["count"]
        }))

    async def broadcast_message(self, message, username, user_id, event_type="chat"):
        """Send a chat message to all participants and store it in history."""
        timestamp = datetime.utcnow().isoformat()
        chat_message = {
            "type": event_type,
            "message": message,
            "username": username,
            "user_id": user_id,
            "timestamp": timestamp
        }

        # Store in chat history
        if self.event_id in active_streams:
            active_streams[self.event_id]["chat_history"].append(chat_message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat",
                **chat_message
            }
        )

    async def chat(self, event):
        """Send a structured chat message to all users."""
        await self.send(text_data=json.dumps(event))

    async def send_chat_history(self):
        """Send previous chat messages to the newly joined user."""
        if self.event_id in active_streams:
            chat_history = active_streams[self.event_id]["chat_history"]
            await self.send(text_data=json.dumps({
                "type": "chat_history",
                "messages": chat_history
            }))

    async def participant_joined(self, event):
        """Handle participant joining event."""
        await self.send(text_data=json.dumps({
            "type": "participant_joined",
            "message": f"{event['username']} joined live.",
            "username": event["username"],
            "user_id": event["user_id"]
        }))

    async def disconnect(self, close_code):
        """Handle disconnection (host or participant)."""
        if not hasattr(self, "room_group_name") or not self.room_group_name:
            return  # Prevent AttributeError

        if self.event_id and self.event_id in active_streams:
            if str(self.user_id) == active_streams[self.event_id]["host"]:
                # Host disconnects → End stream
                del active_streams[self.event_id]
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "stream_ended", "message": "Stream ended by host"}
                )
            else:
                # Participant disconnects → Remove from tracking
                participant_info = active_streams[self.event_id]["participants"].pop(
                    self.channel_name, {"username": "Someone", "participant_id": None})

                # Broadcast participant left message with participant ID
                await self.broadcast_message(
                    f"{participant_info['username']} left now.",
                    participant_info["username"],
                    participant_info["participant_id"],
                    event_type="participant_left"
                )

                # Broadcast updated participant count
                await self.broadcast_participant_count()

        # Leave the group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def participant_left(self, event):
        """Notify all users that a participant has left."""
        await self.send(text_data=json.dumps({
            "type": "participant_left",
            "message": f"{event['username']} left the stream.",
            "username": event["username"],
            "user_id": event["user_id"]
        }))

    async def create_room(self, event_id, user_id):
        """Save the Room when broadcaster starts streaming."""
        await database_sync_to_async(Room.objects.create)(
            room_id=event_id,
            user_id=user_id,
            status="active",
            start_timestamp=now(),
            type=StreamType.AUDIO
        )

    async def room_exists(self, event_id):
        """Check if the room exists."""
        return await database_sync_to_async(Room.objects.filter(room_id=event_id).exists)()

    async def add_participant(self, event_id, user_id, username):
        """Save a participant to the Participants table and update Room total_participants count."""
        room = await database_sync_to_async(Room.objects.get)(room_id=event_id)
        
        await database_sync_to_async(Participant.objects.create)(
            room=room,
            user_id=user_id,
            username=username
        )

        # Update total_participants count
        room.total_participants = await database_sync_to_async(Participant.objects.filter(room=room).count)()
        await database_sync_to_async(room.save)()

    async def stream_ended(self, event):
        """Notify participants that the stream has ended."""
        await self.send(text_data=json.dumps({"type": "stream_ended", "message": event["message"]}))
        await self.close()

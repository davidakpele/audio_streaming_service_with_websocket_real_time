import json
import uuid
import logging
import aiohttp
import redis
import jwt
import numpy as np
from datetime import datetime
from django.conf import settings
from django.utils.timezone import now
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from .models import Participant, Room, StreamType
from django.core.exceptions import ObjectDoesNotExist
from channels.generic.websocket import AsyncWebsocketConsumer

# Redis connection
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
# Constants for event types
SWITCH_TO_VIDEO = "switching_to_video"
SWITCH_TO_AUDIO = "switching_to_audio"
SWITCH_TO_SCREEN_SHARING = "switching_to_screen_sharing"

active_streams = {}  
active_audio_streams = {}
logger = logging.getLogger(__name__)
class StreamingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle both stream start and join based on URL."""
        global active_streams
        self.scope_params = self.scope.get("url_route", {}).get("kwargs", {})
        self.user_id = self.scope_params.get("user_id", None)  
        self.event_id = self.scope_params.get("event_id", None)  
        self.participant_id = self.scope_params.get("participantId", None) 
        self.username = self.scope_params.get("username", "Guest")
        
        # Check if this is an "active-streams" request
        if self.scope["path"] == "/ws/active-streams/":
            await self.accept()
            # Fetch active streams using the method
            active_streams = await self.get_active_streams()

            await self.send(json.dumps({
                "type": "active_streams",
                "streams": active_streams  # Send the list of active room names
            }))
            return
        # Extract token from query params
        jwt_token = self.scope["query_string"].decode().split("token=")[-1] if b"token=" in self.scope["query_string"] else None

        if self.user_id:
            if not jwt_token:
                await self.accept() 
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "JWT token is missing. Authentication required.",
                    "details": "Only authenticated users can access the platform."
                }))
                await self.close()
                return

            # Verify and decode JWT
            try:
                payload = jwt.decode(
                    jwt_token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
                extracted_user_id = payload.get("user_id")

                if not extracted_user_id:
                    await self.accept()
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": "Invalid token",
                        "details": "System cannot extract user ID from this token."
                    }))
                    await self.close()
                    return
                
            except jwt.ExpiredSignatureError:
                await self.accept()
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Expired Token",
                    "details": "Token has expired."
                }))
                await self.close()
                return
            
            except jwt.InvalidTokenError:
                await self.accept()
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid token",
                    "details": "Invalid token."
                }))
                await self.close()
                return

            # Fetch user details from authentication API
            redis_user = redis_client.get(f"user:{self.user_id}")

            if redis_user:
                user_details = json.loads(redis_user)
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:8001/api/v1/user/id/{extracted_user_id}") as response:
                        if response.status != 200:
                            await self.accept()
                            await self.send(json.dumps({
                                "status":302,
                                "type": "error",
                                "message": "User not found",
                                "details": "Sorry. You currenctly not registered in our system."
                            }))
                            await self.close()
                            return

                        user_data = await response.json()
                        user_details = user_data.get("data", {})
                        fetched_user_id = str(user_details.get("id"))
                        self.username = user_details.get("username", "Host")

                        broadcaster_data = {
                            "user_id": fetched_user_id,
                            "username": self.username,
                        }

                        if fetched_user_id != str(self.user_id):
                            await self.accept()
                            await self.send(json.dumps({
                                "status":401,
                                "type": "error",
                                "message": "Unauthorized User.",
                                "details": "Your request Id does not match with our verified user id."
                                }))
                            await self.close()
                            return

                        redis_client.set(
                            f"broadcaster:{extracted_user_id}", json.dumps(broadcaster_data))

                        # Accept the connection before sending anything
                        await self.accept()

                        # Host starts a new stream
                        self.event_id = str(uuid.uuid4())
                        self.user_id = fetched_user_id
                        # Save to Room table
                        await self.create_room(self.event_id, self.user_id)

                        active_streams[self.event_id] = {
                            "host": self.user_id,
                            "status": "active",
                            "participants": {},
                            "chat_history": [],
                        }
                        self.room_group_name = f"user_audio_live_{self.event_id}"

                        # Add host to WebSocket group
                        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                        await self.channel_layer.group_add(f"user_{self.user_id}", self.channel_name)

                        # Generate and send the streaming link
                        stream_link = await self.generate_streaming_link()
                        await self.send(text_data=json.dumps({
                            "type": "stream_link",
                            "event_id": self.event_id,
                            "join_url": stream_link
                        }))

        # Participant joins existing stream
        elif self.event_id is not None:
            try:
                room = await database_sync_to_async(Room.objects.get)(room_id=self.event_id)
                if room.status != "active":
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": "event_ended",
                        "details": "This event is no longer active."
                    }))
                    await self.close()
                    return
                
            except ObjectDoesNotExist:
                await self.accept()
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "event_not_found",
                    "details": "This event does not exist."
                }))
                await self.close()
                return
            
            if not await self.room_exists():
                await self.close()
                return
            
            # Get existing participants
            existing_participants = active_streams.get(self.event_id, {}).get("participants", {})

            # Check if either participant_id or username already exists
            if self.participant_id in existing_participants or any(p["username"] == self.username for p in existing_participants.values()):
                await self.accept()
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "duplicate_user",
                    "details": f"User ID {self.participant_id} or Username {self.username} is already in the session."
                }))
                await self.close()
                return
            
            # Save participant to DB
            await self.add_participant(self.event_id, self.participant_id, self.username)

            # Track participant
            active_streams[self.event_id]["participants"][self.participant_id] = {
                "username": self.username,
                "participant_id": self.participant_id
            }
            
            self.room_group_name = f"user_audio_live_{self.event_id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.channel_layer.group_add(f"user_{self.participant_id}", self.channel_name)  # Add to personal group
            await self.accept()

            # Send chat history to new participant
            await self.send_chat_history()

            # Broadcast updated participant list
            await self.broadcast_participant_list()

            # Broadcast participant count and join message
            await self.broadcast_participant_count()
            await self.broadcast_message(
                f"{self.username} joined live.",
                self.username,
                self.participant_id,
                event_type="participant_joined"
            )

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
                
                # Broadcast updated participant list
                await self.broadcast_participant_list()

        # Leave the group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)
                event_type = data.get("type")

                if event_type == "send_invite":
                    target_user_id = str(data.get("user_id"))

                    if not target_user_id:
                        return

                    # Send notification to the specific user's WebSocket
                    await self.channel_layer.group_send(
                        f"user_{target_user_id}",
                        {
                            "type": "invite_notification",
                            "message": "You have been invited to join.",
                            "from_user": self.user_id
                        }
                    )

                elif event_type == "invite_cohost":
                    if str(self.user_id) != active_streams[self.event_id]["host"]:
                        await self.accept()
                        await self.send(text_data=json.dumps({
                            "type": "error",
                            "message": "Unauthorized User",
                            "details": f"Unauthorized cohost invite attempt by {self.user_id}"
                        }))
                        await self.close()
                        return 
                    
                    # Ensure correct key and type
                    participant_id = str(data.get("user_id"))

                    if participant_id in active_streams[self.event_id]["participants"]:
                        await self.channel_layer.group_send(
                            # Send to specific user's WebSocket group
                            f"user_{participant_id}",
                            {
                                "type": "cohost_invite",
                                "participant_id": participant_id,
                                "message": f"You have been invited to co-host."
                            }
                        )

                elif event_type == "accept_cohost":
                    cohosts = active_streams[self.event_id].setdefault("cohosts", {})

                    # Prevent duplicate co-hosts
                    if any(value["participant_id"] == self.participant_id for value in cohosts.values()):
                        await self.accept()
                        await self.send(text_data=json.dumps({
                            "type": "error",
                            "message": "Duplicate Cohost",
                            "details": f"User {self.participant_id} is already a co-host!"
                        }))
                        await self.close()
                        return 

                    # Ensure the participant exists before making them a co-host
                    if self.participant_id in active_streams[self.event_id]["participants"]:
                        cohosts[self.channel_name] = {
                            "username": self.username,
                            "participant_id": self.participant_id
                        }

                        # Notify the group that a new co-host has joined
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "cohost_joined",
                                "participant_id": self.participant_id,
                                "username": self.username,
                                "message": f"{self.username} is now a co-host."
                            }
                        )

                elif event_type == "cohost_leave":
                    cohosts = active_streams[self.event_id].get("cohosts", {})

                    # Convert participant_id to string for consistency
                    participant_id_str = str(self.participant_id)

                    # Find the cohost key
                    cohost_key = next((key for key, value in cohosts.items() if str(
                        value.get("participant_id")) == participant_id_str), None)

                    if cohost_key:
                        del cohosts[cohost_key]  # Remove co-host

                         # Notify all users
                        await self.channel_layer.group_send(
                            self.room_group_name, 
                            {
                                "type": "cohost_left",
                                "user_id": participant_id_str,
                                "username": self.username,
                                "message": f"{self.username} is no longer a co-host."
                            }
                        )
                       
                    else:
                        print(f"DEBUG: Cohost {participant_id_str} not found in cohosts.")

                elif event_type == "remove_cohost":
                    cohosts = active_streams[self.event_id].get("cohosts", {})

                    # Convert participant_id to string for consistency
                    participant_id_str = str(data.get("participant_id"))
                    participant_username_str = str(data.get("username"))

                    # Find the cohost key
                    cohost_key = next((key for key, value in cohosts.items() if str(value.get("participant_id")) == participant_id_str), None)

                    if cohost_key:
                        del cohosts[cohost_key]  # Remove co-host

                        # Notify all users
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "cohost_removed",
                                "participant_id": participant_id_str,
                                "username": participant_username_str,
                                "message": f"User {participant_username_str} is no longer a co-host."
                            }
                        )
                    else:
                        print(f"Participant {participant_id_str} not found in co-hosts.")

                elif event_type == "stream_ended":
                    await self.end_stream()

                elif event_type == "leave_room": 
                    participant_id = data.get("participant_id")
                    username = str(data.get("username"))

                    # Ensure the event exists in active_streams
                    if self.event_id in active_streams and participant_id in active_streams[self.event_id]["participants"]:
                
                        # Notify all users that the participant left
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "participant_left",
                                "participant_id": participant_id,
                                "username": username,
                                "message": f"{username} has left the live stream."
                            }
                        )

                        # Remove participant from active streams
                        del active_streams[self.event_id]["participants"][participant_id]

                        # Broadcast updated participant list
                        await self.broadcast_participant_list()

                        # Broadcast updated participant count
                        await self.broadcast_participant_count()

                        # Remove participant from WebSocket group
                        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                        await self.channel_layer.group_discard(f"user_{participant_id}", self.channel_name)

                        # Close the WebSocket connection for the leaving participant
                        await self.close()

                elif event_type in [SWITCH_TO_VIDEO, SWITCH_TO_AUDIO, SWITCH_TO_SCREEN_SHARING]:
                    await self.switch_streaming_mode(event_type)

                elif event_type in ["text", "broadcast_message"]:
                    #  If you want to controller audience messages to only allow host and co host to communicate in message then you can comment this out, let the if condition controll the action below
                    # if (self.channel_name == active_streams[self.event_id]["host"] or
                    #         self.channel_name in active_streams[self.event_id].get("cohosts", {})):

                    text_message = data.get("message", "").strip()
                    await self.send_message_to_room(text_message, self.username, self.participant_id)
                    # else:
                    #     await self.send(text_data=json.dumps({
                    #         "type": "error",
                    #         "message": "Only the broadcaster and co-hosts can speak."
                    #     }))

                elif event_type == "webrtc_offer":
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "webrtc_offer",
                            "offer": data["offer"],
                            "username": self.username
                        }
                    )

                elif event_type == "webrtc_answer":
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "webrtc_answer",
                            "answer": data["answer"],
                            "username": self.username
                        }
                    )

            except json.JSONDecodeError as e:
                print(f"Invalid JSON received: {e}")
                return

        elif bytes_data:
            await self.handle_binary_data(bytes_data)

    async def webrtc_offer(self, event):
        """Forward WebRTC offer to all participants."""
        await self.send(text_data=json.dumps(event))

    async def webrtc_answer(self, event):
        """Forward WebRTC answer to all participants."""
        await self.send(text_data=json.dumps(event))

    async def handle_binary_data(self, bytes_data):
        """Handle and broadcast raw PCM audio, video, and screen sharing data."""
        if self.event_id in active_streams:
            mode = active_streams[self.event_id].get("stream_mode", SWITCH_TO_AUDIO)

            try:
                if mode == SWITCH_TO_AUDIO:
    
                    # Assuming 16-bit PCM, little-endian, mono, 16kHz
                    pcm_data = np.frombuffer(bytes_data, dtype=np.int16)

                    # Normalize PCM data (-1.0 to 1.0 float range)
                    normalized_data = pcm_data.astype(np.float32) / 32768.0

                    # Store the latest audio chunk for this participant
                    active_audio_streams[self.participant_id] = normalized_data

                    # Mix all active audio streams
                    if len(active_audio_streams) > 1:
                        mixed_audio = sum(active_audio_streams.values()) / len(active_audio_streams)
                        mixed_audio = np.clip(mixed_audio, -1.0, 1.0)  # Prevent clipping
                    else:
                        mixed_audio = normalized_data  # Single speaker

                    # Convert back to 16-bit PCM
                    processed_bytes = (mixed_audio * 32768).astype(np.int16).tobytes()
                    event_type = "audio_chunk"

                elif mode == SWITCH_TO_VIDEO:
                   
                    processed_bytes = bytes_data  # No need for audio-specific processing
                    event_type = "video_chunk"

                elif mode == SWITCH_TO_SCREEN_SHARING:
                    
                    processed_bytes = bytes_data  # Handle screen-sharing chunks
                    event_type = "screen_chunk"

                else:
                    return  # Ignore unknown modes
                # Broadcast the processed data
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "binary_data_received",
                        "bytes_data": processed_bytes,
                        "event_type": event_type,
                    }
                )

            except Exception as e:
                print(f"Error processing {event_type}: {e}")

    async def binary_data_received(self, event):
        """Send binary data (audio/video) to clients with correct event type."""
        # await self.send(text_data=json.dumps({"event_type": event["event_type"]}))# Send metadata first
        await self.send(bytes_data=event["bytes_data"])  # Then send the binary data

    async def switch_streaming_mode(self, mode):
        if self.event_id in active_streams:
            active_streams[self.event_id]["stream_mode"] = mode
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "stream_mode_changed",
                    "mode": mode,
                    "message": f"Broadcaster switched to {mode.replace('_', ' ').title()} mode."
                }
            )
            if mode == SWITCH_TO_SCREEN_SHARING:
                await self.start_screen_sharing({"type": "start_screen_sharing"})

            elif mode == SWITCH_TO_AUDIO:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "audio_streaming_started",
                        "message": "Broadcaster switched back to audio mode."
                    }
                )

    async def audio_streaming_started(self, event):
        """Send a notification when the broadcaster switches back to audio."""
        await self.send(json.dumps({
            "type": "audio_streaming_started",
            "message": event["message"]
        }))

    async def stream_mode_changed(self, event):
        """Send mode switch notification to all clients."""
        await self.send(json.dumps({
            "type": "stream_mode_changed",
            "mode": event["mode"],
            "message": event["message"]
        }))

    async def start_audio_streaming(self, event):
        await self.send(bytes_data=event["audio_data"])

    async def start_video_streaming(self, event):
        await self.send(bytes_data=event.get("video_data", b""))

    async def start_screen_sharing(self, event):
        """Notify all participants to start screen sharing."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "screen_sharing_started",
                "message": "Broadcaster started screen sharing."
            }
        )

    async def screen_sharing_started(self, event):
        """Send screen sharing notification to all clients."""
        await self.send(json.dumps({
            "type": "screen_sharing_started",
            "message": event["message"]
        }))

    async def send_chat_history(self):
        """Send previous chat messages to the newly joined user."""
        if self.event_id in active_streams:
            chat_history = active_streams[self.event_id].get("chat_history", [])
            await self.send(text_data=json.dumps({
                "type": "chat_history",
                "messages": chat_history
            }))

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
    
    async def participant_joined(self, event):
        """Handle participant joining event."""
        await self.send(text_data=json.dumps({
            "type": "participant_joined",
            "message": f"{event['username']} joined live.",
            "username": event["username"],
            "user_id": event["user_id"]
        }))

    async def participant_left(self, event):
        """Notify all users that a participant has left."""
        await self.send(text_data=json.dumps({
            "type": "participant_left",
            "message": f"{event['username']} left the stream.",
            "username": event["username"],
        }))

    async def participant_count(self, event):
        await self.send(json.dumps(event))

    async def send_message_to_room(self, message, username, user_id):
        """
        Broadcasts a message to all connected users in the chat room and stores it in chat history.
        """
        event_data = {
            "type": "chat_message",
            "message": message,
            "username": username,
            "user_id": user_id
        }
        
        # Store message in chat history
        if self.event_id in active_streams:
            active_streams[self.event_id]["chat_history"].append(event_data)

        # Broadcast message to group
        await self.channel_layer.group_send(self.room_group_name, event_data)

    async def chat_message(self, event):
        """
        Handles incoming messages and sends them to the WebSocket.
        """
        message = event["message"]
        username = event["username"]
        user_id = event["user_id"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "message_broadcast",
            "message": message,
            "username": username,
            "user_id": user_id
        }))

    async def broadcast_message(self, message, username, user_id, event_type="broadcast_message"):
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
            active_streams[self.event_id].setdefault("chat_history", []).append(chat_message)

        # Broadcast to WebSocket clients directly (instead of sending it to another function)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "send_to_client",
                **chat_message
            }
        )

    async def send_to_client(self, event):
        """Send chat message directly to WebSocket clients."""
        await self.send_json(event)

    async def broadcast_participant_list(self):
        """Send the updated participant list to all users."""
        if self.event_id in active_streams:
            participants = [
                {"username": data["username"], "user_id": data["participant_id"]}
                for data in active_streams[self.event_id]["participants"].values()
            ]

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "update_participant_list",
                    "event_id": self.event_id,
                    "participants": participants,
                }
            )

    async def update_participant_list(self, event):
        """Send the updated participant list to the frontend."""
        await self.send(text_data=json.dumps({
            "type": "participant_list",
            "participants": event["participants"]
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

    async def generate_streaming_link(self):
        """Generate a valid streaming link for participants to join."""
        if not self.event_id:
            return None
        
        scheme = "wss" if self.scope.get("scheme", "ws") == "https" else "ws"
        server = self.scope.get("server", ("localhost", 8000))  # Default host & port
        host, port = server if isinstance(server, tuple) else ("localhost", 8000)

        return f"{scheme}://{host}:{port}/ws/stream/live/join/event/{self.event_id}/"

    async def invite_notification(self, event):
        """ WebSocket handler for user invitation """
        await self.send(text_data=json.dumps({
            "type": "invite_notification",
            "message": event["message"],
            "from_user": event["from_user"]
        }))

    async def cohost_invite(self, event):
        """Send co-host invitation notification."""
        if event["participant_id"] == self.participant_id:
            await self.send(text_data=json.dumps({
                "type": "cohost_invite",
                "message": event["message"]
            }))

    async def cohost_joined(self, event):
        """Notify all users when a participant becomes a co-host."""
        await self.send(text_data=json.dumps({
            "type": "cohost_joined",
            "username": event["username"],
            "participant_id": event["participant_id"],
            "message": event["message"]
        }))

    async def cohost_removed(self, event):
        """Notify all users when a co-host is removed."""
        await self.send(text_data=json.dumps({
            "type": "cohost_removed",
            "participant_id": event["participant_id"],
            "username": event["username"],
            "message": event["message"]
        }))

    async def cohost_left(self, event):
        """Send notification when a cohost leaves."""
        await self.send(text_data=json.dumps({
            "type": "cohost_left",
            "user_id": event["user_id"],
            "username": event["username"],
            "message": event["message"]
        }))

    async def participant_left_notification(self, event):
        """Send notification when a participant leaves."""
        await self.send(text_data=json.dumps({
            "type": "participant_left",
            "user_id": event["user_id"],
            "username": event["username"],
            "message": event["message"]
        }))

    async def end_stream(self):
        if await self.room_exists():
            room = await self.get_room()
            room.status = "ended"
            room.end_timestamp = now()
            await self.save_room(room)

            """Host ends the stream"""
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "stream_ended",
                    "message": "The stream has ended. The broadcaster has closed the session.",
                }
            )
            await self.close()

    async def stream_ended(self, event):
        """Notify participants that the stream has ended."""
        await self.send(text_data=json.dumps({"type": "stream_ended", "message": event["message"]}))
        await self.close()

    async def get_active_streams(self):
        # Wrap ORM calls inside `sync_to_async(thread_sensitive=False)`
        exists = await sync_to_async(Room.objects.filter(status="active").exists, thread_sensitive=False)()
        if not exists:
            return []

        # Fetch active streams as dictionaries
        active_streams = await sync_to_async(
            lambda: list(Room.objects.filter(status="active").values(
                "room_id", "created_at", "total_participants", 
                "status", "start_timestamp", "type"
            )), 
            thread_sensitive=False
        )()

        # Convert datetime fields to strings
        for stream in active_streams:
            if isinstance(stream["created_at"], datetime):
                stream["created_at"] = stream["created_at"].isoformat()
            if isinstance(stream["start_timestamp"], datetime):
                stream["start_timestamp"] = stream["start_timestamp"].isoformat()

        return active_streams

    @database_sync_to_async
    def room_exists(self):
        return Room.objects.filter(room_id=self.event_id).exists()
    
    @database_sync_to_async
    def get_room(self):
        return Room.objects.get(room_id=self.event_id)

    @database_sync_to_async
    def save_room(self, room):
        room.save()
    
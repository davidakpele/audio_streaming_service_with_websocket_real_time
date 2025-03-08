import os
import cv2
import base64
import json
import asyncio
import numpy as np
import mediapipe as mp
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

# Initialize Mediapipe Selfie Segmentation
mp_selfie_segmentation = mp.solutions.selfie_segmentation
selfie_segmenter = mp_selfie_segmentation.SelfieSegmentation(model_selection=1)


class VideoLiveStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.room_group_name = f'video_stream_{self.event_id}'

        # Open the webcam
        self.capture = cv2.VideoCapture(0)

        # Default background settings
        self.background_type = "none"  # Default: No background manipulation
        self.background_color = (0, 0, 0)  # Default color (black)
        self.background_image = None  # No image initially

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        asyncio.create_task(self.send_video_frames())

    async def receive(self, text_data):
        """Handle WebSocket messages from frontend (background selection)."""
        data = json.loads(text_data)

        if "background_type" in data:
            self.background_type = data["background_type"]

            if self.background_type == "color" and "background_color" in data:
                # Convert HEX to BGR (for OpenCV)
                hex_color = data["background_color"].lstrip("#")
                rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                self.background_color = rgb_color[::-1]  # Convert RGB to BGR

            elif self.background_type == "image" and "background_image" in data:
                # Decode base64 image from frontend
                image_data = base64.b64decode(data["background_image"])
                np_arr = np.frombuffer(image_data, np.uint8)
                new_bg = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if new_bg is not None:
                    # Resize new background to match webcam frame size
                    ret, frame = self.capture.read()
                    if ret:
                        height, width, _ = frame.shape
                        self.background_image = cv2.resize(
                            new_bg, (width, height))

    async def send_video_frames(self):
        """Capture and send video frames with updated background."""
        while self.capture.isOpened():
            ret, frame = self.capture.read()
            if not ret:
                break

            if self.background_type == "none":
                output_frame = frame  # No background change

            else:
                # Convert frame to RGB for Mediapipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Apply Mediapipe segmentation
                results = selfie_segmenter.process(rgb_frame)

                # Generate segmentation mask
                mask = results.segmentation_mask
                condition = mask > 0.6
                binary_mask = (condition * 255).astype(np.uint8)

                # Smooth edges
                binary_mask = cv2.GaussianBlur(binary_mask, (7, 7), 0)
                kernel = np.ones((5, 5), np.uint8)
                binary_mask = cv2.morphologyEx(
                    binary_mask, cv2.MORPH_CLOSE, kernel)
                final_mask = binary_mask / 255.0

                # Apply background based on selection
                if self.background_type == "color":
                    color_bg = np.full(
                        frame.shape, self.background_color, dtype=np.uint8)
                    output_frame = (
                        frame * final_mask[:, :, None] + color_bg * (1 - final_mask[:, :, None])).astype(np.uint8)

                elif self.background_type == "image" and self.background_image is not None:
                    output_frame = (frame * final_mask[:, :, None] + self.background_image * (
                        1 - final_mask[:, :, None])).astype(np.uint8)

                else:
                    output_frame = frame  # Fallback: No changes

            # Encode and send frame
            _, buffer = cv2.imencode(".jpg", output_frame)
            frame_base64 = base64.b64encode(buffer).decode("utf-8")
            await self.send(text_data=json.dumps({"frame": frame_base64}))

            await asyncio.sleep(0.03)  # 30 FPS

    async def disconnect(self, close_code):
        """Handles WebSocket disconnection."""
        if self.capture.isOpened():
            self.capture.release()
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

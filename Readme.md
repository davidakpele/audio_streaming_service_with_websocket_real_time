


## AUDIO LIVE ENDPOINTS
| Endpoint | Description | 
|----------|--------|
| `/ws://127.0.0.1:8000/ws/active-streams/` | GET ALL ACTIVE LIVE STREAM | 
| `ws://127.0.0.1:8000/ws/stream/start/live/${userId}/?token=` | STARTING BROADCAST OR GOING LIVE | 
| `ws://127.0.0.1:8000/ws/stream/live/join/event/${event_id}/${user_id}/` | User join live stream|


# HOST ACTIONS
| Action Type | Description | Params |
|----------|--------|--------|
| `Start Live Secure and valid Jwt token` | `To enable backend to validate user details from auth service` | null |
| `Switching` | `Broadcaster can switch from audio to screen sharing back to audio in single event` | `{ type: "switching_to_audio", stream: "audio" }` or `{ type: "switching_to_screen_sharing", stream: "screen" }` |
| `End Event` | `Host can end the live stream and event activities associated with that event ends.` | `{ type: "stream_ended", event_id: liveId }` |
| `Invite Co-Host` | `Broadcaster can invite another user to be co-host to speak, Only then User {cohost} **MICROPHONE** will be enable and once he leave or remove, hIS **MICROPHONE** will disabled and only left ill speaker to listen to stream. 'FrontEnd Job' `| `{ type: "invite_cohost", user_id: userId }` |
| `Remove Co Host` | `Host remove CoHost`| `{ type: "remove_cohost", username: coHostUsername, participant_id: userId }` |
| `See total number of User/Participants in live stream` | `Host remove CoHost`| Handle is [ **participant_count** ] |


# User ACTIONS
| Action Type | Description | Params |
|----------|--------|--------|
| `Join Live Stream with Username and User ID` | `Backend will vet the user details and feds on user existing list to avoid duplicated entry` | **Example** ` ws://localhost:8000/ws/stream/live/join/event/${event_id}/${username}/${userId}/` |
| `Accept invite to become Co-Host` | `When host invite user to become cohost, a modal will pop up in that specific user screen to accept the request or reject` | `{ type: "accept_cohost" }` or `type: "cohost_reject"`|
| `Leave Co-Host` | User can always decide to leave cohost| `{ type: "cohost_leave", participant_id: participant_user_id}` |



# SOME SIMILAR ACTIONS
| Action Type | Description | Params |
|----------|--------|--------|
| `Message` | `Both can chat in the message/ chat section and get instant display through websocket` | `{ type: "broadcast_message", message }` |
| `Participants Display` | `Both can see all participants list *Users who join the event*` | `The list constantly update through webscoket`[ Handle is **participant_list**] |
| `Notification Display` | Both get notification when user join, or when user accept to be co-host or leave as coHost or even exit the event | [ Handles are  **broadcast_message, message_broadcast, cohost_joined cohost_left, cohost_removed, participant_left**]  |





## SCHEDULE EVENT ENDPOINTS
| Endpoint | Description | Method | payloads | 
|----------|--------|----------|--------|
| `api/v1/events/` | Create Schedule event | `POST`| `{event_title:'', 'startTime':'', 'startYear':'', 'endTime':'', 'endYear':'', 'category':'', 'theme':'theme':'this is image'}` |
| `api/v1/events/:id/` | Update Schedule event | `PUT`| `{event_title:'', 'startTime':'', 'startYear':'', 'endTime':'', 'endYear':'', 'category':'', 'theme':'theme':'this is image'}` |
| `api/v1/events/:id/` | Get Specific Scheduled event record | `GET`| NULL |
| `api/v1/events/` | Get All Scheduled event records | `GET`| NULL |
| `api/v1/events/:id/` | Delete Specific Scheduled event record | `DELETE`| NULL |



## RECORD UPLOAD ENDPOINTS
| Endpoint | Description | Method | payloads | 
|----------|--------|----------|--------|
| `api/v1/recordings/` | Create record upload | `POST`| `{record_title:'', 'description':'', 'visibility':'', 'userId':'', 'theme':'this is image', 'music':'This is music mp4/mp3'}` **Allowed: MP3, WEBM, WAV**|
| `api/v1/recordings/:id/` | Update record details | `PUT`| `{record_title:'', 'description':'', 'visibility':'', 'userId':'', 'theme':'this is image', 'music':'This is music mp4/mp3'}` **Allowed: MP3, WEBM, WAV**|
| `api/v1/recordings/:id/` | Get Specific record | `GET`| NULL |
| `api/v1/events/` | Get All records | `GET`| NULL |
| `api/v1/events/:id/` | Delete Specific record | `DELETE`| NULL |
| `/api/recordings/?visibility=Public` | Filtering record by Public or Private | `GET`| NULL |


## UPLOAD RECORDED AUDIO STREAM ENDPOINTS
| Endpoint | Description | Method | payloads | 
|----------|--------|----------|--------|
| `api/v1/upload-audio-stream/` | Create upload ON recorded audio during live stream | `POST`| `{userId:'',  'recorded_audio_stream':'This is music mp4/mp3'}` **Allowed: MP3, WEBM, WAV**|
| `api/v1/upload-audio-stream/:id/` | Update record details | `PUT`| `{'userId':'', 'recorded_audio_stream':'This is music mp4/mp3'}` **Allowed: MP3, WEBM, WAV**|
| `api/v1/upload-audio-stream/:id/` | Get Specific record | `GET`| NULL |
| `api/v1/upload-audio-stream/` | Get All records | `GET`| NULL |
| `api/v1/upload-audio-stream/:id/` | Delete Specific record | `DELETE`| NULL |




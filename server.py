"""
    @Author: LunaEspindola
    @Date: 2024-04-03
    @Description: Backend for meowseek widget with API key authentication.
"""

# Import libraries
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
import spotipy
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from pydantic import BaseModel
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow requests from your frontend domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Allow methods
    allow_headers=["*"],  # Allow headers
)

@app.get("/current-song")
async def get_current_song():
    # Your logic to return song data
    return {"song_name": "Song Title", "artist": "Artist", "image_url": "image_url", "progress_ms": 12000, "duration_ms": 240000}

@app.post("/seek")
async def update_song_progress(progress_ms: int):
    # Your logic to update the song progress
    return {"message": "Progress updated"}


# Load environment variables
load_dotenv()

# Spotify API credentials
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

# API Key setup
API_KEY = os.getenv('API_KEY', 'default-api-key')  # Use a secure value for production
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Configure Spotify authentication
scope = "user-modify-playback-state user-read-playback-state"
sp_oauth = SpotifyOAuth(client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        redirect_uri=REDIRECT_URI,
                        scope=scope)

# Initialize FastAPI app
app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dependency for API key validation
def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized. Invalid or missing API key.")
    return api_key

# Dependency to get authenticated Spotify client
def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info or sp_oauth.is_token_expired(token_info):
        raise HTTPException(status_code=401, detail="Unauthorized. Please authenticate.")
    return Spotify(auth=token_info['access_token'])

# API models
class PlaybackRequest(BaseModel):
    device_id: str = None  # Optional: Specify a device ID

# Routes
@app.get("/", dependencies=[Depends(get_api_key)])
async def root():
    return {"message": "Welcome to the Meowseek Widget API"}

@app.get("/auth")
async def auth():
    """Get the Spotify authorization URL."""
    auth_url = sp_oauth.get_authorize_url()
    return {"auth_url": auth_url}

@app.get("/callback")
async def callback(code: str):
    """Spotify callback route to handle token exchange."""
    try:
        token_info = sp_oauth.get_access_token(code)
        if not token_info:
            raise HTTPException(status_code=400, detail="Failed to get access token.")
    except Exception as e:
        logger.error(f"Error during token exchange: {e}")
        raise HTTPException(status_code=400, detail=f"Error during token exchange: {e}")
    return {"message": "Authentication successful. You can now use the API."}

@app.post("/play", dependencies=[Depends(get_api_key)])
async def play_song(request: PlaybackRequest, sp: Spotify = Depends(get_spotify_client)):
    """Play the current song."""
    try:
        # Get available devices
        devices = sp.devices()['devices']
        logger.info(f"Available devices: {devices}")

        if not any(device["id"] == request.device_id for device in devices):
            raise HTTPException(status_code=404, detail="Device not found.")

        # Check if the device is active
        active_device = next((device for device in devices if device["id"] == request.device_id), None)
        if not active_device or not active_device.get('is_active', False):
            raise HTTPException(status_code=400, detail="Device is not active.")
        
        logger.info(f"Starting playback on device {request.device_id}")
        # Start playback
        sp.start_playback(device_id=request.device_id)
        return {"message": "Playback started."}

    except spotipy.exceptions.SpotifyException as e:
        logger.error(f"Spotify error: {e}")
        raise HTTPException(status_code=400, detail=f"Spotify error: {e}")
    except Exception as e:
        logger.error(f"Error during playback: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.post("/pause", dependencies=[Depends(get_api_key)])
async def pause_song(request: PlaybackRequest, sp: Spotify = Depends(get_spotify_client)):
    """Pause the current song."""
    try:
        # Validate device ID
        devices = sp.devices()['devices']
        if not any(device["id"] == request.device_id for device in devices):
            raise HTTPException(status_code=404, detail="Device not found.")
        
        sp.pause_playback(device_id=request.device_id)
        return {"message": "Playback paused."}
    except spotipy.exceptions.SpotifyException as e:
        logger.error(f"Spotify error: {e}")
        raise HTTPException(status_code=400, detail=f"Spotify error: {e}")
    except Exception as e:
        logger.error(f"Error during pause: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.post("/next", dependencies=[Depends(get_api_key)])
async def next_song(request: PlaybackRequest, sp: Spotify = Depends(get_spotify_client)):
    """Skip to the next song."""
    try:
        # Validate device ID
        devices = sp.devices()['devices']
        if not any(device["id"] == request.device_id for device in devices):
            raise HTTPException(status_code=404, detail="Device not found.")
        
        sp.next_track(device_id=request.device_id)
        return {"message": "Skipped to the next song."}
    except spotipy.exceptions.SpotifyException as e:
        logger.error(f"Spotify error: {e}")
        raise HTTPException(status_code=400, detail=f"Spotify error: {e}")
    except Exception as e:
        logger.error(f"Error during next song: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.post("/previous", dependencies=[Depends(get_api_key)])
async def previous_song(request: PlaybackRequest, sp: Spotify = Depends(get_spotify_client)):
    """Go back to the previous song."""
    try:
        # Validate device ID
        devices = sp.devices()['devices']
        if not any(device["id"] == request.device_id for device in devices):
            raise HTTPException(status_code=404, detail="Device not found.")
        
        sp.previous_track(device_id=request.device_id)
        return {"message": "Went back to the previous song."}
    except spotipy.exceptions.SpotifyException as e:
        logger.error(f"Spotify error: {e}")
        raise HTTPException(status_code=400, detail=f"Spotify error: {e}")
    except Exception as e:
        logger.error(f"Error during previous song: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.get("/device", dependencies=[Depends(get_api_key)])
async def get_devices(sp: Spotify = Depends(get_spotify_client)):
    """Get a list of available devices."""
    try:
        devices = sp.devices()
        logger.info(f"Available devices: {devices}")

        if not devices['devices']:
            return {"message": "No devices found."}

        device_list = [{"id": device["id"], "name": device["name"], "type": device["type"]} for device in devices['devices']]
        return {"devices": device_list}
    except spotipy.exceptions.SpotifyException as e:
        logger.error(f"Spotify error: {e}")
        raise HTTPException(status_code=400, detail=f"Spotify error: {e}")
    except Exception as e:
        logger.error(f"Error fetching devices: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {e}")


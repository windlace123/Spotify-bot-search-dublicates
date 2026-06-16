import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import asyncio
from dotenv import load_dotenv
import os
import re
from fastapi import FastAPI

load_dotenv()

class Playlist_spotify:
    def __init__(self, url: str | None = None):
        self.url = url
        self.lst_autors = []
        self.lst_name = []
        # Извлекаем ID плейлиста с помощью регулярного выражения
        match = re.search(r"playlist/([a-zA-Z0-9]+)", url) if url else None
        self.playlist_id = match.group(1) if match else None
        
        self.offset = 0  # Начинаем с 0
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=os.getenv("CLIENT_ID"),
                    client_secret=os.getenv("CLIENT_SECRET")))
        
    async def init(self) -> None:
        if not self.playlist_id:
            return
        data = await asyncio.to_thread(lambda: self.sp.playlist(self.playlist_id))
        self.total_tracks = data['tracks']['total']

    async def write_all(self) -> None:
        if not self.playlist_id:
            return

        def process_batch(playlist_data):
            for item in playlist_data["items"]:
                if not item.get('track'): continue
                track = item['track']
                self.lst_name.append(track["name"])
                artists = [artist['name'] for artist in track['artists']]
                self.lst_autors.append(", ".join(artists))

        while self.offset < self.total_tracks:
            playlist = await asyncio.to_thread(
                lambda: self.sp.playlist_tracks(self.playlist_id, offset=self.offset, limit=100)
            )
            if not playlist or not playlist['items']:
                break
                
            process_batch(playlist)
            self.offset += 100

app = FastAPI()

@app.post("/")
async def path(payload: dict):
    url = payload.get("path_on_playlist")
    if not url:
        return {"error": "No URL provided"}
        
    obj = Playlist_spotify(url)
    await obj.init()
    if obj.playlist_id:
        await obj.write_all()
        return {"lst_name": obj.lst_name, "lst_autors": obj.lst_autors}
    return {"error": "Invalid Spotify URL"}
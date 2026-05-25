"""View module for handling requests about songs, including Spotify search. The song data comes from Spotify and then we save data about songs that users add to their setlists in our database."""

import os
import time
import base64
import requests
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from thelineup_api.models import Song


# ── Spotify helpers ───────────────────────────────────────────────────────────

# Module-level token cache — avoids fetching a new token on every request.
# Tokens are valid for 3600 seconds; we refresh 60 seconds early to be safe.
_token_cache = {"token": None, "expires_at": 0}


def get_spotify_token():
    """Get a cached Spotify access token using the Client Credentials flow.
    Only fetches a new token when the cached one has expired."""
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {credentials}"},
        data={"grant_type": "client_credentials"},
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(f"Failed to get Spotify token: {response.json().get('error_description', 'unknown error')}")

    data = response.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"] - 60

    return _token_cache["token"]


def spotify_get(url, params=None):
    """Make a GET request to the Spotify API.
    Handles 429 rate limiting by respecting the Retry-After header.
    Raises an exception with a meaningful message for other errors."""
    token = get_spotify_token()

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10
    )

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "a few")
        raise Exception(f"Spotify rate limit reached. Please try again in {retry_after} seconds.")

    if response.status_code == 401:
        # Token may have expired unexpectedly — clear cache and raise
        _token_cache["token"] = None
        raise Exception("Spotify authentication failed. Please try again.")

    if response.status_code != 200:
        error = response.json().get("error", {}).get("message", "Unknown Spotify error")
        raise Exception(f"Spotify error {response.status_code}: {error}")

    return response.json()


# ── Serializers ───────────────────────────────────────────────────────────────

class SongSerializer(serializers.ModelSerializer):
    """JSON serializer for songs"""

    class Meta:
        model = Song
        fields = ['id', 'title', 'artist', 'spotify_id', 'preview_url', 'album_art_url']


# ── ViewSet ───────────────────────────────────────────────────────────────────

class SongView(ViewSet):
    """Handles song search via Spotify and saving songs to the database"""

    def list(self, request):
        """GET /songs — list all songs saved in the database"""
        songs = Song.objects.all()
        serializer = SongSerializer(songs, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='search')
    def search(self, request):
        """GET /songs/search?q=autumn leaves — search Spotify.
        Returns results directly from Spotify without saving to the database."""
        query = request.query_params.get("q")
        if not query:
            return Response(
                {"message": "q query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = spotify_get(
                "https://api.spotify.com/v1/search",
                params={"q": query, "type": "track", "limit": 10}
            )

            tracks = data["tracks"]["items"]

            results = []
            for track in tracks:
                results.append({
                    "spotify_id": track["id"],
                    "title": track["name"],
                    "artist": track["artists"][0]["name"],
                    "preview_url": track.get("preview_url"),
                    "album_art_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None
                })

            return Response(results)

        except Exception as ex:
            return Response(
                {"message": f"Spotify search failed: {str(ex)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        """POST /songs — save a song from Spotify to the database.
        Called when a user selects a song to add to a setlist.
        If the song already exists, returns it instead of creating a duplicate."""
        try:
            existing = Song.objects.filter(spotify_id=request.data["spotify_id"]).first()
            if existing:
                serializer = SongSerializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)

            song = Song()
            song.title = request.data["title"]
            song.artist = request.data["artist"]
            song.spotify_id = request.data["spotify_id"]
            song.preview_url = request.data.get("preview_url")
            song.album_art_url = request.data.get("album_art_url")
            song.save()

            serializer = SongSerializer(song)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except KeyError as ex:
            return Response(
                {"message": f"{ex.args[0]} field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

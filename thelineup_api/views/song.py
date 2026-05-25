"""View module for handling requests about songs, including Spotify search. The song data comes from Spotify and then we save data about songs that users add to their setlists in our database."""

import os  # for environment variables; the spotify client id and secret should be stored in .env
import time  # for token caching
import base64  # for encoding client credentials in the Spotify token request
import requests  # for making HTTP requests to the Spotify API (external)
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from thelineup_api.models import Song

# ── Spotify helpers ───────────────────────────────────────────────────────────

# Module-level token cache — avoids fetching a new token on every request.Tokens are valid for 3600 seconds; we refresh 60 seconds early to be safe.
_token_cache = {"token": None, "expires_at": 0}


def get_spotify_token():
    """Get a cached Spotify access token using the Client Credentials flow.
    Only fetches a new token when the cached one has expired."""

    # if we have a token and it's not expired, return it.
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    # Reading the api keys and encrypting them for the Spotify token request.
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    # sends a post to Spotify saying  "here are my credentials, give me a token." grant_type
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {credentials}"},
        data={"grant_type": "client_credentials"},
        timeout=10,
    )

    # if spotify responds with an error, it would be stored in the response json just like a valid token would be. So checking the status code first is the way for us to know if the response is a token or an error.
    if response.status_code != 200:
        raise Exception(
            f"Failed to get Spotify token: {response.json().get('error_description', 'unknown error')}"
        )

    # now we know we have a valid token response, so we can parse it and store it in the cache with its expiration time.
    data = response.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"] - 60

    return _token_cache["token"]


# Spotify helper function to make GET requests to Spotify, with built in handling for rate limits and token expiration.It also raises exceptions with clear messages for different error scenarios, which makes it easier to handle errors in the endpoints that call it.
# Used by the song search endpoint below. Definition of a helper function: a function that performs a common task (like making an API request) that can be reused across multiple endpoints or even multiple viewsets, and makes it easier to maintain. If we need to change how we handle Spotify requests (like adding logging, or changing error handling), we can do it in one place instead of in every endpoint that talks to Spotify.
def spotify_get(url, params=None):
    """Make a GET request to the Spotify API.
    Handles 429 rate limiting by respecting the Retry-After header.
    Raises an exception with a meaningful message for other errors."""
    # we need the token to make GET requests.
    token = get_spotify_token()

    # make the actual GET request to Spotify with the token in the Authorization header, and any params that were passed in. We also set a timeout to avoid hanging if Spotify doesn't respond.
    response = requests.get(
        url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=10
    )
    # A 429 error can happen when we hit Spotify's rate limits. The Retry-After header tells us how long to wait before making another request. By raising an exception here, we can tell the viewset method about it later and be able to return a clear error message to the client.
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "a few")
        raise Exception(
            f"Spotify rate limit reached. Please try again in {retry_after} seconds."
        )

    # A 401 error can happen if the token has expired unexpectedly (maybe it was revoked, or there was a clock sync issue). By raising an exception here, we can tell the viewset method about it later and be able to return a clear error message to the client.
    if response.status_code == 401:
        # Token may have expired unexpectedly — clear cache and raise
        _token_cache["token"] = None
        raise Exception("Spotify authentication failed. Please try again.")

    # A 200 error means the request was successful and we got a valid response. So if we get anything else, we'll treat it as an error and try to extract a meaningful message from the response to include in the exception.
    if response.status_code != 200:
        error = response.json().get("error", {}).get("message", "Unknown Spotify error")
        raise Exception(f"Spotify error {response.status_code}: {error}")

    return response.json()




# ── Serializers ───────────────────────────────────────────────────────────────
# This expands the data of a song, so that when we save a song to our database, we have all the relevant details about it (like title, artist, album art) instead of just the Spotify ID. This way, when we display songs in the setlist, we can show all that info without needing to make additional requests to Spotify.

class SongSerializer(serializers.ModelSerializer):
    """JSON serializer for songs"""

    class Meta:
        model = Song
        fields = ["id", "title", "artist", "spotify_id", "album_art_url"]





# ── ViewSet ───────────────────────────────────────────────────────────────────

class SavedSongView(ViewSet):
    """Handles saving songs to the database (Song model) when user adds a song to a setlist. That way the song object can be linked to setlist through SetlistSong, and we have all the song details stored in our database for easy access when displaying setlists."""

    def create(self, request):
        """POST /songs — save a song from Spotify to the database.
        Called when a user selects a song to add to a setlist"""

        song = Song.objects.create(
            title=request.data["title"],
            artist=request.data["artist"],
            spotify_id=request.data["spotify_id"],
            album_art_url=request.data.get("album_art_url"),
        )

        serializer = SongSerializer(song)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SpotifySearchView(ViewSet):
    """Searches Spotify for tracks. Results are not saved to the database."""

    def list(self, request):
        """GET /spotify-search/?q=searchterm — search Spotify for tracks."""
        #get the search query from the request's query parameters
        query = request.query_params.get("q")
        #use the helper function to make a GET request from the spotify api. we're giving the params it needs.
        data = spotify_get(
            "https://api.spotify.com/v1/search",
            params={"q": query, "type": "track", "limit": 10},
        )
        #the section of the spotify response that has valuable data for us. We're cutting out the fat with this
        songs = data["tracks"]["items"]
        #create an empty array to hold the results
        results = []
        #loop the songs array from Spotify and pull out just the details we care about, and put those in a simpler object that we add to our results array.
        for song in songs:
            results.append({
                "spotify_id": song["id"],
                "title": song["name"],
                "artist": song["artists"][0]["name"],
                "album_art_url": song["album"]["images"][0]["url"],
            })
        #return the results array to the client.
        return Response(results)
    



    #Spotify returns: 
#     {
#     "tracks": {
#         "href": "https://api.spotify.com/v1/search?query=autumn+leaves...",
#         "limit": 10,
#         "total": 847,
#         "items": [
#             {
#                 "id": "3dDmVz5TaAJuJYjCW6Y0i4",
#                 "name": "Autumn Leaves",
#                 "artists": [
#                     { "id": "abc123", "name": "Miles Davis" }
#                 ],
#                 "album": {
#                     "name": "Kind of Blue",
#                     "images": [
#                         { "url": "https://i.scdn.co/image/...", "width": 640 },
#                         { "url": "https://i.scdn.co/image/...", "width": 300 },
#                         { "url": "https://i.scdn.co/image/...", "width": 64 }
#                     ]
#                 },
#                 "duration_ms": 327000,
#                 "explicit": false,
#                 "popularity": 72,
#                 ... loads more fields
#             },
#             { ... second song },
#             { ... third song },
#         ]
#     }
# }

# data["tracks"]["items"] is just the array of song objects — so each song in the for loop looks like this:


# {
#     "id": "3dDmVz5TaAJuJYjCW6Y0i4",
#     "name": "Autumn Leaves",
#     "artists": [
#         { "id": "abc123", "name": "Miles Davis" }
#     ],
#     "album": {
#         "name": "Kind of Blue",
#         "images": [
#             { "url": "https://i.scdn.co/image/...", "width": 640 },
#             { "url": "https://i.scdn.co/image/...", "width": 300 },
#             { "url": "https://i.scdn.co/image/...", "width": 64 }
#         ]
#     },
#     "duration_ms": 327000,
#     "explicit": false,
#     "popularity": 72
# }


#then the for loop pulls out the things I care about and puts them in a simpler object that we return to the client, which looks like this:
# {
#     "spotify_id": "3dDmVz5TaAJuJYjCW6Y0i4",
#     "title": "Autumn Leaves",
#     "artist": "Miles Davis",
#     "album_art_url": "https://i.scdn.co/image/..."
# }
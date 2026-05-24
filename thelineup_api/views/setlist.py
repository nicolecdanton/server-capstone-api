"""View module for handling requests about setlists"""

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from thelineup_api.models import Setlist, SetlistSong, Song, UserProfile


# ── Serializers ───────────────────────────────────────────────────────────────

class SetlistSongSerializer(serializers.ModelSerializer):
    """Nested serializer showing song details on a setlist"""
    song_id = serializers.IntegerField(source='song.id', read_only=True)
    title = serializers.CharField(source='song.title', read_only=True)
    artist = serializers.CharField(source='song.artist', read_only=True)
    spotify_id = serializers.CharField(source='song.spotify_id', read_only=True)
    album_art_url = serializers.CharField(source='song.album_art_url', read_only=True)

    class Meta:
        model = SetlistSong
        fields = ['id', 'song_id', 'title', 'artist', 'spotify_id', 'album_art_url']


class SetlistSerializer(serializers.ModelSerializer):
    """JSON serializer for setlists"""
    songs = SetlistSongSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.user.username', read_only=True)

    class Meta:
        model = Setlist
        fields = ['id', 'name', 'created_by_username', 'songs']


# ── ViewSet ───────────────────────────────────────────────────────────────────

class SetlistView(ViewSet):
    """Handles full CRUD for setlists plus adding and removing songs"""

    def list(self, request):
        """GET /setlists — returns the logged-in user's setlists"""
        profile = UserProfile.objects.get(user=request.auth.user)
        setlists = Setlist.objects.filter(created_by=profile)
        serializer = SetlistSerializer(setlists, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """GET /setlists/{id} — returns a single setlist with its songs"""
        try:
            setlist = Setlist.objects.get(pk=pk)
            serializer = SetlistSerializer(setlist)
            return Response(serializer.data)
        except Setlist.DoesNotExist:
            return Response({"message": "Setlist not found"}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request):
        """POST /setlists — create a new setlist"""
        profile = UserProfile.objects.get(user=request.auth.user)

        try:
            setlist = Setlist()
            setlist.name = request.data["name"]
            setlist.created_by = profile
            setlist.save()

            serializer = SetlistSerializer(setlist)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except KeyError as ex:
            return Response(
                {"message": f"{ex.args[0]} field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def partial_update(self, request, pk=None):
        """PATCH /setlists/{id} — rename a setlist. Only the creator can edit."""
        try:
            setlist = Setlist.objects.get(pk=pk)
        except Setlist.DoesNotExist:
            return Response({"message": "Setlist not found"}, status=status.HTTP_404_NOT_FOUND)

        if setlist.created_by.user != request.auth.user:
            return Response(
                {"message": "You can only edit your own setlists"},
                status=status.HTTP_403_FORBIDDEN
            )

        setlist.name = request.data.get("name", setlist.name)
        setlist.save()

        serializer = SetlistSerializer(setlist)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """DELETE /setlists/{id} — delete a setlist. Only the creator can delete."""
        try:
            setlist = Setlist.objects.get(pk=pk)
        except Setlist.DoesNotExist:
            return Response({"message": "Setlist not found"}, status=status.HTTP_404_NOT_FOUND)

        if setlist.created_by.user != request.auth.user:
            return Response(
                {"message": "You can only delete your own setlists"},
                status=status.HTTP_403_FORBIDDEN
            )

        setlist.delete()
        return Response({}, status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post', 'delete'], detail=True, url_path='songs')
    def manage_songs(self, request, pk=None):
        """POST /setlists/{id}/songs — add a song to a setlist.
        DELETE /setlists/{id}/songs — remove a song from a setlist.
        Both require song_id in the request body."""
        try:
            setlist = Setlist.objects.get(pk=pk)
        except Setlist.DoesNotExist:
            return Response({"message": "Setlist not found"}, status=status.HTTP_404_NOT_FOUND)

        if setlist.created_by.user != request.auth.user:
            return Response(
                {"message": "You can only modify your own setlists"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            song = Song.objects.get(pk=request.data["song_id"])
        except Song.DoesNotExist:
            return Response({"message": "Song not found"}, status=status.HTTP_404_NOT_FOUND)
        except KeyError:
            return Response({"message": "song_id field is required"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":
            # Prevent duplicate entries
            if SetlistSong.objects.filter(setlist=setlist, song=song).exists():
                return Response(
                    {"message": "Song is already on this setlist"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            SetlistSong.objects.create(setlist=setlist, song=song)
            serializer = SetlistSerializer(setlist)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            setlist_song = SetlistSong.objects.filter(setlist=setlist, song=song).first()
            if not setlist_song:
                return Response(
                    {"message": "Song is not on this setlist"},
                    status=status.HTTP_404_NOT_FOUND
                )
            setlist_song.delete()
            serializer = SetlistSerializer(setlist)
            return Response(serializer.data)

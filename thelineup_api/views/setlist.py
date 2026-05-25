"""View module for handling requests about setlists; including adding songs to them and removing songs from them"""

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from thelineup_api.models import Setlist, SetlistSong, Song, UserProfile


# ── Serializers ───────────────────────────────────────────────────────────────
#this serializer is getting the song details for each song on the setlist
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

#this serializer is getting the username of the creator of the setlist, and puts it together with the song details for the setlist.
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
        """GET setlists will return the all of the user's setlists"""
        profile = UserProfile.objects.get(user=request.auth.user)
        setlists = Setlist.objects.filter(created_by=profile)
        serializer = SetlistSerializer(setlists, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """GET setlists/{id} — returns a single setlist with its songs details. Only the creator can view."""
        setlist = Setlist.objects.get(pk=pk)
        serializer = SetlistSerializer(setlist)
        return Response(serializer.data)

    def create(self, request):
        """POST /setlists, create a new setlist"""
        profile = UserProfile.objects.get(user=request.auth.user)
        setlist = Setlist(
            name = request.data["name"],
            created_by = profile,                                
        )
        
        setlist.save()

        serializer = SetlistSerializer(setlist)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

    #this is just for letting the setlist creator rename the setlist
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
    
    #delete an actual setlist
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


class SetlistSongView(ViewSet):
    """Handles adding and removing songs from a setlist via the SetlistSong join table."""

    def create(self, request):
        """POST /setlist-songs/ — add a song to a setlist. Requires setlist_id and song_id."""
        setlist = Setlist.objects.get(pk=request.data["setlist_id"])

        if setlist.created_by.user != request.auth.user:
            return Response(
                {"message": "You can only modify your own setlists"},
                status=status.HTTP_403_FORBIDDEN
            )

        song = Song.objects.get(pk=request.data["song_id"])
        SetlistSong.objects.create(setlist=setlist, song=song)

        serializer = SetlistSerializer(setlist)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        """DELETE /setlist-songs/{id}/ — remove a song from a setlist. pk is the SetlistSong join row id."""
        setlist_song = SetlistSong.objects.get(pk=pk)

        if setlist_song.setlist.created_by.user != request.auth.user:
            return Response(
                {"message": "You can only modify your own setlists"},
                status=status.HTTP_403_FORBIDDEN
            )

        setlist = setlist_song.setlist
        setlist_song.delete()

        serializer = SetlistSerializer(setlist)
        return Response(serializer.data)

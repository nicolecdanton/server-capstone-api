"The model for Songs, which includes fields for title, artist, spotify_id, preview_url, album_art_url"

from django.db import models

class Song(models.Model):

    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    spotify_id = models.CharField(max_length=100, unique=True)
    album_art_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} by {self.artist}"
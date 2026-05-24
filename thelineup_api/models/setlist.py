"Setlist is an object created by a user. Songs are added to it via SetlistSong. A Setlist can be applied to multiple Gigs."

from django.db import models


class Setlist(models.Model):

    created_by = models.ForeignKey("thelineup_api.UserProfile", on_delete=models.CASCADE, related_name="setlists")
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name} by {self.created_by.user.username}"


class SetlistSong(models.Model):

    setlist = models.ForeignKey(
        Setlist, on_delete=models.CASCADE, related_name="songs")
    song = models.ForeignKey(
        "thelineup_api.Song", on_delete=models.PROTECT, related_name="setlist_entries")

    def __str__(self):
        return f"{self.song.title} in {self.setlist.name}"

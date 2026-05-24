"Model for Gig — a musical performance with a venue, date, pay, and an optional setlist. The booker creates the Gig."

from django.db import models


class Gig(models.Model):
    "Represents a single gig created by a UserProfile."

    booker = models.ForeignKey(
        "thelineup_api.UserProfile", on_delete=models.CASCADE, related_name="booked_gigs"
    )
    title = models.CharField(max_length=100)
    venue = models.CharField(max_length=200)
    date = models.DateTimeField()
    pay_per_musician = models.FloatField()
    setlist = models.ForeignKey(
        "thelineup_api.Setlist", on_delete=models.SET_NULL, null=True, blank=True, related_name="gigs"
    )

    def __str__(self):
        return f"{self.title} at {self.venue} on {self.date.strftime('%Y-%m-%d')} — booked by {self.booker.user.username}"

"A GigSlot represents one instrument seat in a Gig. filled_by is nullable because a slot can exist without being filled yet by a musician."

from django.db import models


class GigSlot(models.Model):

    gig = models.ForeignKey(
        "thelineup_api.Gig", on_delete=models.CASCADE, related_name="slots")
    instrument = models.ForeignKey(
        "thelineup_api.Instrument", on_delete=models.PROTECT, related_name="gig_slots")
    filled_by = models.ForeignKey(
        "thelineup_api.UserProfile", on_delete=models.PROTECT, null=True, blank=True, related_name="gig_slots")

    def __str__(self):
        filled = self.filled_by.user.username if self.filled_by else "unfilled"
        return f"{self.instrument} slot at {self.gig.title} — {filled}"
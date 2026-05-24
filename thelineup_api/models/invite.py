"Model for Invite, which is a record of a musician being invited to fill a GigSlot. Accepting an invite updates filled_by on the slot."

from django.db import models


class Invite(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("withdrawn", "Withdrawn"),
    ]

    slot = models.ForeignKey(
        "thelineup_api.GigSlot", on_delete=models.CASCADE, related_name="invites")
    musician = models.ForeignKey(
        "thelineup_api.UserProfile", on_delete=models.CASCADE, related_name="invites")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending")
    sent_at = models.DateTimeField(
        auto_now_add=True)
    responded_at = models.DateTimeField(
        null=True, blank=True)

    def __str__(self):
        return f"Invite to {self.musician.user.username} for {self.slot} — {self.status}"

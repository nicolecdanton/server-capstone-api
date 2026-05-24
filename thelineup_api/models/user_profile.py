"Model for UserProfile — extends the built-in User with bio, social links, and instruments."

from django.db import models
from django.contrib.auth.models import User
from thelineup_api.models.instrument import Instrument


class UserProfile(models.Model):
    "Extends Django's built-in User model with profile information."

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, default="")
    soundcloud = models.URLField(blank=True, default="")
    instagram_handle = models.CharField(max_length=100, blank=True, default="")
    instrument = models.ManyToManyField(Instrument, blank=True, related_name="musicians")

    def __str__(self):
        return self.user.username

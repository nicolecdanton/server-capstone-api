# Instrument is a lookup table — just a list of instrument names.
# The many-to-many relationship with UserProfile is defined on UserProfile via a ManyToManyField,
# which tells Django to auto-create the join table (UserInstrument) behind the scenes.

from django.db import models


class Instrument(models.Model):

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


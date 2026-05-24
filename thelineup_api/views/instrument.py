"""View module for handling requests about instruments"""

from django.db import IntegrityError
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from thelineup_api.models import Instrument


#Serializers ───────────────────────────────────────────────────────────────
class InstrumentSerializer(serializers.ModelSerializer):
    """JSON serializer for instruments"""

    class Meta:
        model = Instrument
        fields = ['id', 'name']



# ViewSet ───────────────────────────────────────────────────────────────────
class InstrumentView(ViewSet):
    """Handles list and create for instruments"""

    def list(self, request):
        """Handle GET requests to return all instruments"""
        instruments = Instrument.objects.all().order_by('name')
        serializer = InstrumentSerializer(instruments, many=True)
        return Response(serializer.data)


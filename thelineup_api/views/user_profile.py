"Views for retrieving and editing a UserProfile."

from django.http import HttpResponseServerError
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from thelineup_api.models import UserProfile, Instrument


# ── Serializers ───────────────────────────────────────────────────────────────

class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ['id', 'name']


class UserProfileSerializer(serializers.ModelSerializer):
    # Read: returns full instrument objects
    instrument = InstrumentSerializer(many=True, read_only=True)

    # Write: accepts a list of instrument IDs
    instrument_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Instrument.objects.all(),
        source='instrument'
    )

    # Expose username and name from the related User
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'first_name', 'last_name',
            'bio', 'soundcloud', 'instagram_handle',
            'instrument', 'instrument_ids'
        ]


# ── ViewSet ───────────────────────────────────────────────────────────────────

class UserProfileView(ViewSet):
    lookup_field = 'user_id'

    def list(self, request):
        """GET /profiles — return all user profiles (used by Musicians directory and SendInvite)."""
        profiles = UserProfile.objects.select_related('user').prefetch_related('instrument').all()
        serializer = UserProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    def retrieve(self, request, user_id=None):
        """GET /profiles/{user_id}/ — retrieve a single profile by user id."""
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist as ex:
            return HttpResponseServerError(ex)

    def partial_update(self, request, user_id=None):
        """PATCH /profiles/{user_id}/ — edit your own profile only."""
        try:
            profile = UserProfile.objects.get(user_id=user_id)

            if profile.user != request.auth.user:
                return Response(
                    {'error': 'You can only edit your own profile.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except UserProfile.DoesNotExist as ex:
            return HttpResponseServerError(ex)

"""View module for handling requests about invites"""

from datetime import datetime
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from thelineup_api.models import Invite, GigSlot, UserProfile


# ── Serializers ───────────────────────────────────────────────────────────────
#this serializer is getting the gig title and id for the gigslot that the invite is for. 
class InviteGigSlotSerializer(serializers.ModelSerializer):
    """Nested serializer to show slot context on an invite"""
    instrument_name = serializers.CharField(source='instrument.name', read_only=True)
    gig_title = serializers.CharField(source='gig.title', read_only=True)
    gig_id = serializers.IntegerField(source='gig.id', read_only=True)

    class Meta:
        model = GigSlot
        fields = ['id', 'gig_id', 'gig_title', 'instrument_name']


#this serializer is getting the username of the musician that the invite is for, so that we can show it on the booker's view of the invite.
class InviteMusicianSerializer(serializers.ModelSerializer):
    """Nested serializer to show musician info on an invite"""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username']

#putting it together: slot info and musician info can come back with the invite info of status, sent_at, responsed_at.
class InviteSerializer(serializers.ModelSerializer):
    """JSON serializer for invites"""
    slot = InviteGigSlotSerializer(read_only=True)
    musician = InviteMusicianSerializer(read_only=True)

    class Meta:
        model = Invite
        fields = ['id', 'slot', 'musician', 'status', 'sent_at', 'responded_at']


# ── ViewSet ───────────────────────────────────────────────────────────────────

class InviteView(ViewSet):
    """Handles all invite operations for bookers and musicians"""

    def list(self, request):
        """Handle GET requests for invites.

        Default — returns invites where I am the musician (my inbox).
        ?gig_id=1 — returns invites sent for a specific gig (booker view).
        ?status=pending — filter by status (works with or without gig_id).
        """
        profile = UserProfile.objects.get(user=request.auth.user)
        gig_id = request.query_params.get("gig_id")
        status_filter = request.query_params.get("status")

        if gig_id:
            # Booker viewing invites for their gig
            invites = Invite.objects.filter(slot__gig_id=gig_id)
        else:
            # Musician viewing their own received invites
            invites = Invite.objects.filter(musician=profile)

        if status_filter:
            invites = invites.filter(status=status_filter)

        serializer = InviteSerializer(invites, many=True)
        return Response(serializer.data)


    def create(self, request):
        """Handle POST requests to send an invite. Only the gig's booker can send invites."""
        invite = Invite.objects.create(
            slot = GigSlot.objects.get(pk=request.data["slot_id"])
            musician = UserProfile.objects.get(pk=request.data["musician_id"])
            status = "pending"
            )
        invite.save()

        serializer = InviteSerializer(invite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """Handle PATCH requests to update an invite status.

        Musician can: accept, decline
        Booker can: withdraw

        Accepting also updates filled_by on the GigSlot.
        """
        try:
            invite = Invite.objects.get(pk=pk)
        except Invite.DoesNotExist:
            return Response({"message": "Invite not found"}, status=status.HTTP_404_NOT_FOUND)

        profile = UserProfile.objects.get(user=request.auth.user)
        new_status = request.data.get("status")

        is_musician = invite.musician == profile
        is_booker = invite.slot.gig.booker.user == request.auth.user

        if not is_musician and not is_booker:
            return Response(
                {"message": "You are not authorized to update this invite"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Musician can only accept or decline
        if is_musician and new_status not in ["accepted", "declined"]:
            return Response(
                {"message": "Musicians can only accept or decline an invite"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Booker can only withdraw
        if is_booker and not is_musician and new_status != "withdrawn":
            return Response(
                {"message": "Bookers can only withdraw an invite"},
                status=status.HTTP_400_BAD_REQUEST
            )

        invite.status = new_status
        invite.responded_at = datetime.now()

        # Accepting fills the slot
        if new_status == "accepted":
            slot = invite.slot
            slot.filled_by = invite.musician
            slot.save()

        invite.save()

        serializer = InviteSerializer(invite)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """Handle DELETE requests. Only the booker who created the invite can delete it."""
        try:
            invite = Invite.objects.get(pk=pk)
        except Invite.DoesNotExist:
            return Response({"message": "Invite not found"}, status=status.HTTP_404_NOT_FOUND)

        if invite.slot.gig.booker.user != request.auth.user:
            return Response(
                {"message": "You can only delete invites you created"},
                status=status.HTTP_403_FORBIDDEN
            )

        invite.delete()
        return Response({}, status=status.HTTP_204_NO_CONTENT)

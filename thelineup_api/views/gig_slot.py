"""View module for handling requests about gig slots"""

from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from thelineup_api.models import GigSlot, Gig, Instrument, UserProfile


# Serializers first
#───────────────────────────────────────────────────────────────────

#When getting the data about a gigslot, what do i want to know about the instruments? Just name on instrument would help:
class SlotInstrumentSerializer(serializers.ModelSerializer):
    """Nested serializer for instrument on a slot"""

    class Meta:
        model = Instrument
        fields = ['id', 'name']

#When getting the data about a gigslot, I want to be able to show who it is filled by. I need the username.
class SlotFilledBySerializer(serializers.ModelSerializer):
    """Nested serializer for the musician filling a slot"""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username']

#put it all together. Also adds the ability to see the count of invites for the slot
class GigSlotSerializer(serializers.ModelSerializer):
    """JSON serializer for gig slots"""
    instrument = SlotInstrumentSerializer(read_only=True)
    filled_by = SlotFilledBySerializer(read_only=True)
    invite_count = serializers.SerializerMethodField()

    def get_invite_count(self, singleGigSlotObj):
        return singleGigSlotObj.invites.count()

    class Meta:
        model = GigSlot
        fields = ['id', 'gig', 'instrument', 'filled_by', 'invite_count']

# with nested serializers for insturment and filled by, + the computation of invite_count, the final shape of a single GigSlot looks like: 
# {
#     "id": 1,
#     "gig": 3,
#     "instrument": {
#         "id": 2,
#         "name": "Guitar"
#     },
#     "filled_by": {
#         "id": 5,
#         "username": "maya"
#     },
#     "invite_count": 2
# }



# ViewSet 
#───────────────────────────────────────────────────────────────────
class GigSlotView(viewsets.ViewSet):
    """Handles list, retrieve, create, partial_update, and destroy for gig slots"""

    #this is a special list, i only care about gig slots for a single gig, so i will pass in the gig id as a query param and filter by that. If no query param is passed, return all slots.
    def list(self, request):
        """Handle GET requests to get all gig slots, or all slots for a single gig if a gig_id query param is passed"""
        #get every slot for all the gigs- safeguard
        gigSlots = GigSlot.objects.all()

        #if theres a gig id in the query params, we filter the slots to just those for that gig.
        gig_id = request.query_params.get("gig_id")
        if gig_id:
            gigSlots = gigSlots.filter(gig_id=gig_id)
        
        #serialize and return the data
        serializer = GigSlotSerializer(gigSlots, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """GET /gigslots/{id}/ — get a single slot"""
        try:
            slot = GigSlot.objects.get(pk=pk)
        except GigSlot.DoesNotExist:
            return Response({"message": "Slot not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = GigSlotSerializer(slot)
        return Response(serializer.data)

    def create(self, request):
        """Handle POST requests to create a new gig slot. Only the gig's booker can add slots. New gig slots are created in connection with a gig, so the gig id must be passed in the request body."""
        #Checking we know what gig we're trying to create a slot in relation to and that it exists- since that is crucial to create a slot, so we can understand and traceback issues easier. Instead of a blanket 500 internal server error.
        try:
            gig = Gig.objects.get(pk=request.data["gig_id"])
        except Gig.DoesNotExist:
            return Response({"message": "Gig not found"}, status=status.HTTP_404_NOT_FOUND)
        
        #safeguard to make sure the user creating the slot is the booker of the gig. Only the booker can add slots to a gig.
        if gig.booker.user != request.auth.user:
            return Response(
                {"message": "You can only add slots to gigs you created"},
                status=status.HTTP_403_FORBIDDEN
            )

        slot = GigSlot.objects.create(
            gig_id = request.data["gig_id"],
            instrument_id = request.data["instrument_id"]
            #filled_by is not included in create because the model already defines it as null=True, and when a slot is created it is not filled by anyone. It'll get set without issue upon create.
        )

        #serialize and return the new slot data
        serializer = GigSlotSerializer(slot)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        #TODO: figure out what error handling is needed here. What if the instrument id is invalid? What if the gig id is invalid?

    def partial_update(self, request, pk=None):
        """Handle PATCH requests to update a slot. Only the gig's booker can edit an existing slot. Only the instrument of a slot can be edited by the booker."""
        #we gotta make sure the gigslot exists before we can update it, so we can return a 404 if it doesn't exist instead of a blanket 500 internal server error.
        try:
            slot = GigSlot.objects.get(pk=pk)
        except GigSlot.DoesNotExist:
            return Response({"message": "Slot not found"}, status=status.HTTP_404_NOT_FOUND)

        #same safeguard here- only the booker of the gig can edit the slots for that gig.
        if slot.gig.booker.user != request.auth.user:
            return Response(
                {"message": "You can only edit slots for gigs you created"},
                status=status.HTTP_403_FORBIDDEN
            )

        #the only thing that can really be edited by a booker about an existing slot is the instrument, so we're looking for changes to instrument.
        slot.instrument = Instrument.objects.get(pk=request.data.get("instrument_id", slot.instrument_id))
        
        #This time we are not creating a new row, its updating an existing row, so we have to save the changes to the database.
        slot.save()

        #serialize and return the updated slot data
        serializer = GigSlotSerializer(slot)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """Handle DELETE requests to remove a slot. Only the gig's booker can delete a slot."""
        #we gotta make sure the gigslot exists before we can delete it, and this way we can return a 404 if it doesn't exist instead of a blanket 500 internal server error.
        try:
            slot = GigSlot.objects.get(pk=pk)
        except GigSlot.DoesNotExist:
            return Response({"message": "Slot not found"}, status=status.HTTP_404_NOT_FOUND)

        #same safeguard here- only the booker of the gig can delete the slots for that gig.
        if slot.gig.booker.user != request.auth.user:
            return Response(
                {"message": "You can only delete slots for gigs you created"},
                status=status.HTTP_403_FORBIDDEN
            )

        slot.delete()
        return Response({}, status=status.HTTP_204_NO_CONTENT)

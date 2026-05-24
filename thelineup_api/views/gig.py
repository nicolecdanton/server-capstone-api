"""View module for handling requests about gigs"""

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from thelineup_api.models import Gig, UserProfile, Setlist


#Serializers ───────────────────────────────────────────────────────────────
#When getting data about a gig, I want to be able to show the slots for that gig. I have these serializers already so I'm going to reuse them here.
from thelineup_api.views.gig_slot import GigSlotSerializer

#When getting the data about a gig, I want to be able to show who the booker is. I need the username
class BookerSerializer(serializers.ModelSerializer):
    """Nested serializer to show basic booker info on a gig"""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username']

#When getting the data about a gig, I want to be able to show the setlist name if there is a setlist attached to the gig, so I can display it on the frontend. I don't need the songs for this view, just the name and id of the setlist.
class GigSetlistSerializer(serializers.ModelSerializer):
    """Nested serializer to get setlist id + name when a gig has one"""

    class Meta:
        model = Setlist
        fields = ['id', 'name']


#Putting it together: when getting data about a gig, I want to be able to show the booker username, the setlist name if there is a setlist attached, and the slots for the gig with the instrument name, who it's filled by, and how many invites each slot has.
class GigSerializer(serializers.ModelSerializer):
    """JSON serializer for gigs"""
    booker = BookerSerializer(read_only=True)
    setlist = GigSetlistSerializer(read_only=True)
    slots = GigSlotSerializer(many=True, read_only=True)

    class Meta:
        model = Gig
        fields = ['id', 'booker', 'title', 'venue', 'date', 'pay_per_musician', 'setlist', 'slots']


# ViewSet ───────────────────────────────────────────────────────────────────

class GigView(ViewSet):
    """Handles list, create, partial_update, and destroy for gigs"""

    #listing all the gigs that the users cares about: the ones theyve booked and the ones they have been invited to.
    def list(self, request):
        """Handle GET requests to return all gigs"""
        profile = UserProfile.objects.get(user=request.auth.user)
        gigs = Gig.objects.filter(booker=profile)
        
        serializer = GigSerializer(gigs, many=True)
        return Response(serializer.data)

    #need to get details of a single gig to show the gig details page. This will include the booker username, the setlist name if there is a setlist attached, and the slots for the gig with the instrument name, who it's filled by, and how many invites each slot has.
    def retrieve(self, request, pk=None):
        """Handle GET requests for a single gig"""
        #we're doing the try so that if a user tries to access a gig that doesn't exist, we can return a 404 not found instead of a blanket 500 internal server error.
        try:
            gig = Gig.objects.get(pk=pk)
        except Gig.DoesNotExist:
            return Response({"message": "Gig not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = GigSerializer(gig)
        return Response(serializer.data)

    
    def create(self, request):
        """Handle POST requests to create a new gig.
        Booker is set automatically from the logged-in user.
        setlist_id is optional."""
        if "setlist_id" in request.data:
            setlist = Setlist.objects.get(pk=request.data["setlist_id"])
        else:
            setlist = None

        gig = Gig.objects.create(
            booker=UserProfile.objects.get(user=request.auth.user),
            title=request.data["title"],
            venue=request.data["venue"],
            date=request.data["date"],
            pay_per_musician=request.data["pay_per_musician"],
            setlist=setlist
        )

        serializer = GigSerializer(gig)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        #TODO: figure out what error handling is needed here. What could go wrong when creating a gig?

    #I want to make sure a booker is able to edit their gig if they need to change something. Only the booker can edit. They should be able to edit the title, venue, date, pay per musician, and setlist.
    def partial_update(self, request, pk=None):
        """Handle PATCH requests to update a gig. Only the booker can edit."""
        #we gotta make sure the gig exists
        try:
            gig = Gig.objects.get(pk=pk)
        except Gig.DoesNotExist:
            return Response({"message": "Gig not found"}, status=status.HTTP_404_NOT_FOUND)

        #we gotta make sure you're allowed to edit this gig- only the booker can edit the gig.
        if gig.booker.user != request.auth.user:
            return Response(
                {"message": "You can only edit gigs you created"},
                status=status.HTTP_403_FORBIDDEN
            )

        gig.title = request.data.get("title", gig.title)
        gig.venue = request.data.get("venue", gig.venue)
        gig.date = request.data.get("date", gig.date)
        gig.pay_per_musician = request.data.get("pay_per_musician", gig.pay_per_musician)

        #Setlist is allowed to be null, so this got weird:
        if "setlist_id" in request.data: #because- did the user send a setlist_id at all? It can be null
            setlist_id = request.data["setlist_id"] #figure out the value of setlist_id
            if setlist_id is None: #Detach- update to none then!
                gig.setlist = None
            else:
                gig.setlist = Setlist.objects.get(pk=setlist_id) #attach- update that id to the new setlist

        gig.save()

        serializer = GigSerializer(gig)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """Handle DELETE requests to remove a gig. Only the booker can delete."""
        #gigs gotta exist be be deleted
        try:
            gig = Gig.objects.get(pk=pk)
        except Gig.DoesNotExist:
            return Response({"message": "Gig not found"}, status=status.HTTP_404_NOT_FOUND)

        #you have to be the booker to be allowed to delete it.
        if gig.booker.user != request.auth.user:
            return Response(
                {"message": "You can only delete gigs you created"},
                status=status.HTTP_403_FORBIDDEN
            )

        gig.delete()
        return Response({}, status=status.HTTP_204_NO_CONTENT)

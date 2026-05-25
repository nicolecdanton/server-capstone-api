from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from rest_framework import routers
from thelineup_api.views import *

# pylint: disable=invalid-name
router = routers.DefaultRouter(trailing_slash=False)
router.register(r"profiles", UserProfileView, "profile")
router.register(r"instruments", InstrumentView, "instrument")
router.register(r"gigs", GigView, "gig")
router.register(r"gigslots", GigSlotView, "gigslot")
router.register(r"invites", InviteView, "invite")
router.register(r"songs", SavedSongView, "song")
router.register(r"spotify-search", SpotifySearchView, "spotify-search")
router.register(r"setlists", SetlistView, "setlist")
router.register(r"setlist-songs", SetlistSongView, "setlist-song")


urlpatterns = [
    path("", include(router.urls)),
    path("register", register_user),
    path("login", login_user),
    path("api-auth", include("rest_framework.urls", namespace="rest_framework")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""Register and login views"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from thelineup_api.models import UserProfile


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Handles the authentication of a user"""

    username = request.data.get('username', None)
    password = request.data.get('password', None)

    authenticated_user = authenticate(username=username, password=password)

    if authenticated_user is not None:
        token = Token.objects.get(user=authenticated_user)
        return Response({'valid': True, 'token': token.key, 'id': authenticated_user.id})

    return Response({'valid': False}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Handles the creation of a new user for authentication"""

    username = request.data.get('username', None)
    email = request.data.get('email', None)
    password = request.data.get('password', None)
    first_name = request.data.get('first_name', None)
    last_name = request.data.get('last_name', None)

    if username and email and password and first_name and last_name:
        try:
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
        except IntegrityError:
            return Response(
                {'message': 'An account with that username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        UserProfile.objects.create(
            user=new_user,
            bio=request.data.get('bio', ''),
            soundcloud=request.data.get('soundcloud', ''),
            instagram_handle=request.data.get('instagram_handle', ''),
        )

        token = Token.objects.create(user=new_user)
        return Response({'token': token.key, 'id': new_user.id}, status=status.HTTP_201_CREATED)

    return Response(
        {'message': 'You must provide username, email, password, first_name, and last_name'},
        status=status.HTTP_400_BAD_REQUEST
    )

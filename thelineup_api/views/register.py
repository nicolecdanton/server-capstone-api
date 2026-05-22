"""Register and login views for The Lineup API."""

import json

from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


@csrf_exempt
def login_user(request):
    """Handles the authentication of a user."""

    if request.method == "POST":
        req_body = json.loads(request.body.decode())

        required_fields = ["username", "password"]
        for field in required_fields:
            if field not in req_body:
                return HttpResponse(
                    f"Missing required field: {field}",
                    status=status.HTTP_400_BAD_REQUEST,
                )

        authenticated_user = authenticate(
            username=req_body["username"],
            password=req_body["password"],
        )

        if authenticated_user is not None:
            token = Token.objects.get(user=authenticated_user)
            data = json.dumps(
                {"valid": True, "token": token.key, "id": authenticated_user.id}
            )
            return HttpResponse(data, content_type="application/json")
        else:
            data = json.dumps({"valid": False})
            return HttpResponse(data, content_type="application/json")
    else:
        return HttpResponseNotAllowed(permitted_methods=["POST"])


@csrf_exempt
def register_user(request):
    """Handles the creation of a new user."""

    if request.method == "POST":
        req_body = json.loads(request.body.decode())

        required_fields = ["username", "email", "password", "first_name", "last_name"]
        for field in required_fields:
            if field not in req_body:
                return HttpResponse(
                    f"Missing required field: {field}",
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            password_validation.validate_password(req_body["password"])
        except ValidationError as e:
            return HttpResponse(
                json.dumps({"valid": False, "errors": e.messages}),
                content_type="application/json",
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                new_user = User.objects.create_user(
                    username=req_body["username"],
                    email=req_body["email"],
                    password=req_body["password"],
                    first_name=req_body["first_name"],
                    last_name=req_body["last_name"],
                )

                token = Token.objects.create(user=new_user)

            data = json.dumps({"token": token.key, "id": new_user.id})
            return HttpResponse(
                data, content_type="application/json", status=status.HTTP_201_CREATED
            )

        except IntegrityError:
            return HttpResponse(
                "Username already exists. Please choose a different username.",
                status=status.HTTP_409_CONFLICT,
            )
    else:
        return HttpResponseNotAllowed(permitted_methods=["POST"])

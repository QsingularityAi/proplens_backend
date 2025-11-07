from ninja import Router
from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from pydantic import BaseModel
from typing import Optional

router = Router()


class TokenAuth(HttpBearer):
    def authenticate(self, request, token):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return user
        except:
            return None


class LoginSchema(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access: str
    refresh: str


@router.post("/login", response=TokenResponse)
def login(request, credentials: LoginSchema):
    """Login and get JWT tokens"""
    user = authenticate(username=credentials.username, password=credentials.password)
    if user:
        refresh = RefreshToken.for_user(user)
        return TokenResponse(
            access=str(refresh.access_token),
            refresh=str(refresh),
        )
    return {"error": "Invalid credentials"}, 401


@router.post("/refresh", response=TokenResponse)
def refresh_token(request, refresh: str):
    """Refresh access token"""
    try:
        refresh_token = RefreshToken(refresh)
        return TokenResponse(
            access=str(refresh_token.access_token),
            refresh=str(refresh_token),
        )
    except:
        return {"error": "Invalid refresh token"}, 401




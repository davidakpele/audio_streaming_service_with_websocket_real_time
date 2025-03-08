import jwt
import datetime
from rest_framework import exceptions
from django.conf import settings


def create_access_token(user_id):
    """
    Create a JWT access token for the given user ID.
    The token expires in 1 day.
    """
    payload = {
        'roles': ['USER'],
        'user_id': user_id,
        # Token expires in 1 day
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        'iat': datetime.datetime.utcnow(),  # Issued at
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')
    return token


def decode_access_token(token):
    """
    Decode and validate a JWT access token.
    Returns the user ID if the token is valid.
    Raises an AuthenticationFailed exception if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        raise exceptions.AuthenticationFailed({
            "status": 401,
            "title": "Authentication Error",
            "detail": "Access token has expired.",
            "code": "token_expired"
        })
    except jwt.InvalidTokenError:
        raise exceptions.AuthenticationFailed({
            "status": 401,
            "title": "Authentication Error",
            "detail": "Invalid access token.",
            "code": "invalid_token"
        })


def create_refresh_token(user_id):
    """
    Create a JWT refresh token for the given user ID.
    The token expires in 7 days.
    """
    payload = {
        'roles': ['USER'],
        'user_id': user_id,
        # Token expires in 7 days
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow(),  # Issued at
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')
    return token


def decode_refresh_token(token):
    """
    Decode and validate a JWT refresh token.
    Returns the user ID if the token is valid.
    Raises an AuthenticationFailed exception if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        raise exceptions.AuthenticationFailed({
            "status": 401,
            "title": "Authentication Error",
            "detail": "Refresh token has expired.",
            "code": "token_expired"
        })
    except jwt.InvalidTokenError:
        raise exceptions.AuthenticationFailed({
            "status": 401,
            "title": "Authentication Error",
            "detail": "Invalid refresh token.",
            "code": "invalid_token"
        })

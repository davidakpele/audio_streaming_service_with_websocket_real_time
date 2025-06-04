import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from .JwtAuthenticationService import decode_access_token 

User = get_user_model()  # Get the User model dynamically


class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None  
        
        # Ensure "Bearer" token format
        try:
            prefix, token = auth_header.split()
            if prefix.lower() != 'bearer':
                raise AuthenticationFailed(
                    {'detail': 'Invalid token format', 'status': 401})
        except ValueError:
            raise AuthenticationFailed(
                {'detail': 'Invalid Authorization header', 'status': 401})

        # Decode the token and get user ID
        user_id = decode_access_token(token)

        # Get user from DB
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                {'detail': 'User not found', 'status': 401})

        return (user, None)  # Authentication successful

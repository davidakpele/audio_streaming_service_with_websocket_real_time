import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from app.services.authentication import CustomJWTAuthentication
from .models import AccountVerification, CustomUser
from .serializers import ProfileUpdateSerializer, UserDetailSerializer
import random
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from .services.JwtAuthenticationService import create_access_token, create_refresh_token
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

def generate_otp():
    """Generate a 6-digit OTP."""
    return random.randint(100000, 999999)

def send_otp_email(email, otp):
    """Send an OTP email using an HTML template."""
    subject = 'Your OTP for Account Verification'

    # Load and render the HTML template
    html_content = render_to_string(
        'emails/email.html', {'otp': otp})

    # Create the email message with both plain text and HTML versions
    email_message = EmailMultiAlternatives(
        subject=subject,
        # Fallback plain text
        body=f"Your OTP is: {otp}. Do not share this with anyone.",
        from_email=settings.EMAIL_HOST_USER,
        to=[email]
    )

    email_message.attach_alternative(
        html_content, "text/html")  # Attach HTML version
    email_message.send()  # Send the email

    return otp

def send_welcome_email(email):
    """Send a welcome email to the user."""
    subject = 'Welcome to the Plug LR family! 🎉'
    try:
       # Load and render the HTML template
        html_content = render_to_string(
            'emails/welcome-email.html')

        # Create the email message with both plain text and HTML versions
        email_message = EmailMultiAlternatives(
            subject=subject,
            # Fallback plain text
            from_email=settings.EMAIL_HOST_USER,
            to=[email]
        )

        email_message.attach_alternative(
            html_content, "text/html")  # Attach HTML version
        email_message.send()  # Send the email
        return True
    except Exception:
        return False

def send_reset_password_email(email, otp):
    """Send an OTP email using an HTML template."""
    subject = 'Your OTP for creating new password'

    # Load and render the HTML template
    html_content = render_to_string(
        'emails/reset_password.html', {'OTP_CODE': otp})

    # Create the email message with both plain text and HTML versions
    email_message = EmailMultiAlternatives(
        subject=subject,
        # Fallback plain text
        body=f"Your OTP is: {otp}. Do not share this with anyone.",
        from_email=settings.EMAIL_HOST_USER,
        to=[email]
    )

    email_message.attach_alternative(
        html_content, "text/html")  # Attach HTML version
    email_message.send()  # Send the email

    return otp

class SendWelcomeEmailAPI(APIView):
    """
    API endpoint to send a welcome email to a user.
    """
    def post(self, request):
        try:
    
            email = request.data.get('email')

            if not email:
                return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Send email
            if send_welcome_email(email):
                return Response({"message": "Welcome email sent successfully!"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Failed to send email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegisterAPI(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            password = request.data.get('password')

            # Validate email
            if not email or email.strip() == '':
                return JsonResponse({'error': 'Email cannot be empty or null.', 'status': 400}, status=400)

            # Validate password
            if not password or password.strip() == '':
                return JsonResponse({'error': 'Password cannot be empty or null.', 'status': 400}, status=400)

            # Check if email already exists
            user = CustomUser.objects.filter(email=email).first()
            if user is not None:
                return JsonResponse({'error': 'User already taken this email address.*', 'status': 409}, status=409)

            # Create user
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                firstname=None,
                lastname=None
            )
            user.enabled = False
            user.save()

            # # Generate OTP only once and store in a variable
            otp = generate_otp()

            # # Save OTP in the database
            otp_record = AccountVerification.objects.create(
                user=user,
                otp=otp,
                expires_at=timezone.now() + timedelta(minutes=30)
            )

            # # Send the same OTP via email
            send_otp_email(user.email, otp)

            return JsonResponse({'message': 'OTP sent to your email.', 'status': 201}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data', 'status': 400}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e), 'status': 500}, status=500)

class LoginAPI(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            email = request.data.get('email')
            password = request.data.get('password')

            # Validate email and password
            if not email or email.strip() == '':
                return JsonResponse({'error': 'Email cannot be empty or null.', 'status': 400}, status=400)
            if not password or password.strip() == '':
                return JsonResponse({'error': 'Password cannot be empty or null.', 'status': 400}, status=400)

            # Authenticate user
            user = authenticate(email=email, password=password)
            if user is None:
                return JsonResponse({'error': 'Invalid email or password.', 'status': 401}, status=401)

            # Check if the user account is enabled
            if not user.enabled:
                return JsonResponse({'error': 'Your account is unverified. Please verify your account.', 'status': 403}, status=403)
            
            # Set session
            request.session['email'] = user.email

            # Generate tokens
            access_token = create_access_token(user.id)
            refresh_token = create_refresh_token(user.id)

            # Prepare response
            response = Response()
            response.data = {
                'token': access_token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'firstname': user.firstname,  
                    'lastname': user.lastname,  
                    'mobile': user.mobile,  
                    'state': user.state,  
                    'enabled': user.enabled,
                    'createdAt': user.createdAt,
                },
                'status': 200
            }
            response.set_cookie(
                key='jwt', value=refresh_token, httponly=True, samesite='Lax')
            return response

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data', 'status': 400}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e), 'status': 500}, status=500)

class VerifyOTPAPI(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Email and OTP are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
            otp_record = AccountVerification.objects.filter(user=user).last()

            if not otp_record:
                return Response({"error": "No OTP found for this user"}, status=status.HTTP_400_BAD_REQUEST)

            if otp_record.is_expired():
                otp_record.delete()  # Delete expired OTP
                return Response({"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)

            if otp_record.otp == otp:
                # Update user enabled status
                user.enabled = True
                user.save()

                # Delete OTP record after successful verification
                otp_record.delete()

                return Response({"message": "OTP verified successfully, account enabled."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class CompleteProfileAPI(APIView):
    authentication_classes = [CustomJWTAuthentication]

    def put(self, request):
        user = request.user

        # Validate and update profile data
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully."}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FindUserByIdAPI(APIView):
    authentication_classes = [CustomJWTAuthentication]

    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_data = {
                "id": user.id,
                "email": user.email,
                "firstname": user.firstname if user.firstname is not None else "",  
                "lastname": user.lastname if user.lastname is not None else "",    
                "mobile": user.mobile if user.mobile is not None else "",        
                "username": user.username if user.username is not None else "",  
                "state": user.state if user.state is not None else "",          
                "enabled": user.enabled,
                "createdAt": user.createdAt
            }
            return Response({"data": user_data}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class GenerateRefreshTokenAPI(APIView):
    """
    API endpoint to generate a refresh token for a user.
    """

    def post(self, request):
        # Get the user ID from the request data
        user_id = request.data.get('user_id')

        # Validate the user ID
        if not user_id:
            return Response(
                {"error": "User ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate the refresh token
        try:
            refresh_token = create_refresh_token(user_id)
            return Response(
                {
                    "message": "Refresh token generated successfully.",
                    "refresh_token": refresh_token
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ResendOTPAPI(APIView):
    """Resend OTP if the previous one expired."""

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Generate a new OTP
        new_otp = generate_otp()
        expiration_time = timezone.now() + timezone.timedelta(minutes=30)

        # Update or create OTP record
        otp_instance, created = AccountVerification.objects.get_or_create(
            user=user)
        # Replace expired OTP
        otp_instance.code = new_otp  
        # Set new expiration time
        otp_instance.expires_at = expiration_time 
        # Save changes
        otp_instance.save()  

        # Send OTP via email
        send_otp_email(user.email, new_otp)

        return Response({"message": "A new OTP has been sent to your email."}, status=status.HTTP_200_OK)

class RestPasswordAPI(APIView):
    """User Reset Password Endpoint"""

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Generate a new OTP
        new_otp = generate_otp()
        expiration_time = timezone.now() + timezone.timedelta(hours=1)

        # Update or create OTP record
        otp_instance, created = AccountVerification.objects.get_or_create(
            user=user)
        # Replace expired OTP
        otp_instance.code = new_otp
        # Set new expiration time
        otp_instance.expires_at = expiration_time
        # Save changes
        otp_instance.save()

        # Send OTP via email
        send_reset_password_email(user.email, new_otp)

        return Response({"message": "Message has been sent to the email you provided."}, status=status.HTTP_200_OK)

class PasswordUpdateAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            password = request.data.get('password')
            confirm_password = request.data.get('confirm_password')

            # Validate email
            if not email or email.strip() == '':
                return JsonResponse({'error': 'Email cannot be empty or null.', 'status': 400}, status=400)

            # Validate passwords
            if not password or password.strip() == '':
                return JsonResponse({'error': 'Password cannot be empty or null.', 'status': 400}, status=400)
            if password != confirm_password:
                return JsonResponse({'error': 'Passwords do not match.', 'status': 400}, status=400)

            # Check if user exists
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                return JsonResponse({'error': 'User not found.', 'status': 404}, status=404)

            # Update password
            user.password = make_password(password)
            user.save()

            return JsonResponse({'message': 'Password updated successfully.', 'status': 200}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e), 'status': 500}, status=500)

class AuthUserChangePasswordAPI(APIView):
    # Only authenticated users can access this view
    authentication_classes = [CustomJWTAuthentication]

    def put(self, request):
        try:
            old_password = request.data.get('old_password')
            new_password = request.data.get('new_password')
            confirm_password = request.data.get('confirm_password')

            # Validate old password
            if not old_password or old_password.strip() == '':
                return Response({'error': 'Old password cannot be empty or null.', 'status': 400}, status=status.HTTP_400_BAD_REQUEST)

            # Validate new password
            if not new_password or new_password.strip() == '':
                return Response({'error': 'New password cannot be empty or null.', 'status': 400}, status=status.HTTP_400_BAD_REQUEST)

            # Validate confirm password
            if new_password != confirm_password:
                return Response({'error': 'New passwords do not match.', 'status': 400}, status=status.HTTP_400_BAD_REQUEST)

            # Get the current authenticated user
            user = request.user

            # Check if the old password matches the user's current password
            if not check_password(old_password, user.password):
                return Response({'error': 'Old password is incorrect.', 'status': 400}, status=status.HTTP_400_BAD_REQUEST)

            # Update the password
            user.password = make_password(new_password)
            user.save()

            return Response({'message': 'Password updated successfully.', 'status': 200}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e), 'status': 500}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

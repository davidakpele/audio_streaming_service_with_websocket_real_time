from django.urls import path, include
from .views import RegisterAPI, VerifyOTPAPI, AuthUserChangePasswordAPI, PasswordUpdateAPI, CompleteProfileAPI, LoginAPI, FindUserByIdAPI, ResendOTPAPI, SendWelcomeEmailAPI, GenerateRefreshTokenAPI

urlpatterns = [
    path('api/v1/auth/register/', RegisterAPI.as_view(), name='register'),
    path('api/v1/auth/login/', LoginAPI.as_view(), name='login'),
    path('api/v1/auth/verify-otp/', VerifyOTPAPI.as_view(), name='verify_otp'),
    path('api/v1/auth/resend-otp/', ResendOTPAPI.as_view(), name='resend_otp'),
    path('api/v1/auth/token/refresh/', GenerateRefreshTokenAPI.as_view(), name='token_refresh'),
    path('api/v1/send-welcome-email/', SendWelcomeEmailAPI.as_view(), name='send_welcome_email'),
    path('api/v1/auth/create-new-password/', PasswordUpdateAPI.as_view(), name='create_new_password'),
    
    path('api/v1/user/update-password/', AuthUserChangePasswordAPI.as_view(), name='update_password'),
    path('api/v1/user/complete-profile/', CompleteProfileAPI.as_view(), name='complete_profile'),
    path('api/v1/user/id/<int:user_id>/', FindUserByIdAPI.as_view(), name='find_user_by_id'),
]

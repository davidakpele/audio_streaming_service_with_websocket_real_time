# Django Authentication API

## Overview
**This Django-based API provides user authentication and profile management functionalities, including user registration, login, OTP verification, and email notifications.**

## Features

- User Registration

- Login with JWT authentication

- OTP verification and Resend OTP

- Profile completion

- Fetch user details by ID

- Welcome email notification

- Token refresh

## Installation
#### Ensure you have the following installed:

1. Python 3.x

2. Django

3. Django REST Framework

4. PyJWT

## Setup

1. Clone the repository:
```
git clone <repository_url>
cd <project_folder>
```
2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```
3. Install dependencies:
```
pip install -r requirements.txt
```
4. Run database migrations:
```
python manage.py migrate
```
5. Start the development server:
```
python manage.py runserver
```

## API Endpoints

#### Authentication & User Management
| Endpoint | Method | Description | Expected Data |
|----------|--------|-------------|--------------|
| `/api/v1/auth/register/` | POST | Register a new user | `{'password':'password', 'email':'username@aol.com'}` |
| `/api/v1/auth/login/` | POST | Login and obtain access & refresh tokens | `{'password':'password', 'email':'username@aol.com'}` |
| `/api/v1/auth/verify-otp/` | POST | Verify OTP for account activation | `{'otp':'42232', 'email':'username@aol.com'}` |
| `/api/v1/auth/resend-otp/` | POST | Resend OTP if expired | `{'email':'username@aol.com'}` |
| `/api/v1/auth/token/refresh/` | POST | Refresh expired access token | `{'user_id':'UserID'}` |
| `/api/v1/auth/create-new-password/` | POST | To Reset User Password | `{'password':'password', 'confirm_password':'password'}` |
| `/api/v1/send-welcome-email/` | POST | Send a welcome email upon successful registration | `null` |
| `/api/v1/complete-profile/` | POST | Complete user profile after registration | `{'firstname':'UserFName', 'lastname':'UserLname', 'mobile':'UserMobile', 'state':'UserState'}` |
| `/api/v1/user/id/<int:user_id>/` | GET | Fetch user details by ID | `UserIdParam` |

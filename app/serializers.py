from rest_framework import serializers
from .models import CustomUser, AccountVerification
from rest_framework.serializers import ModelSerializer

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'firstname', 'lastname',
                  'mobile', 'state', 'enabled', 'createdAt']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class AccountVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountVerification
        fields = ['user', 'AccountVerification', 'created_at', 'expires_at']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['firstname', 'lastname', 'mobile', 'state']
        extra_kwargs = {
            'firstname': {'required': False},
            'lastname': {'required': False},
            'mobile': {'required': False},
            'state': {'required': False},
        }

    def validate_mobile(self, value):
        """
        Validate the mobile number.
        """
        if value and not value.isdigit():
            raise serializers.ValidationError(
                "Mobile number must contain only digits.")
        return value

    def validate_username(self, value):
        """
        Validate the username.
        """
        if value and CustomUser.objects.filter(username=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value


class UserDetailSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'firstname', 'lastname', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
            instance.save()
            return instance

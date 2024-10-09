from rest_framework import serializers
from django.shortcuts import get_object_or_404
from .models import CustomUser


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'profile_photo', 'cover_photo']
class UserSignUpSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'username', 'password1', 'password2']
        extra_kwargs = {
            'password1': {'write_only': True},
            'password2': {'write_only': True},
        }

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        username = validated_data['username']
        email = validated_data['email']
        password = validated_data['password1']
        first_name = validated_data['first_name']
        last_name = validated_data['last_name']
        
        user = CustomUser.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)


    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'password', 'password1', 'password2',
                  'gender', 'private', 'profile_photo', 'cover_photo']
        extra_kwargs = {
            'password': {'write_only': True},
            'password1': {'write_only': True},
            'password2': {'write_only': True},
        }

    def validate(self, data):
        user = self.context['request'].user
        user_instance = get_object_or_404(CustomUser, id=user.id)
        
        if not user_instance.check_password(data.get('password')):
            raise serializers.ValidationError("old password not correct")
        
        if data.get('password1') != data.get('password2'):
            raise serializers.ValidationError("Passwords do not match.")
        return data


class UserGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'profile_photo', 'cover_photo', 'email', 'gender', 'profile_photo', 'cover_photo']


class UserLoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField()

    class Meta:
        model = CustomUser
        fields = ['username', 'password']
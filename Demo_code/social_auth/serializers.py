from decouple import config
from rest_framework import serializers
from . import google, microsofthelper       
from .register import register_social_user, signup_social_user
import os, json
from rest_framework.exceptions import AuthenticationFailed
from accounts.serializers import TokenObtainPairSerializer



class GoogleSocialAuthSerializer(serializers.Serializer):
    tokenId = serializers.CharField()
    company = serializers.CharField(required = False)

    def validate(self, attrs):
        token = attrs.get("tokenId")
        company = attrs.get("company")
        
        user_data = google.Google.validate_auth_token(token)
        print("GOOGLE DATA",user_data)
        
        try:
            user_data['sub']
        except:
            raise serializers.ValidationError(
                'The token is invalid or expired. Please login again.'
            )

        if user_data['aud'] != config('GOOGLE_CLIENT_ID'):
            raise AuthenticationFailed('oops, who are you?')

        user_id = user_data['sub']
        email = user_data['email']
        name = user_data['name']
        provider = 'google'
        tenant = self.context['tenant']
        if tenant == 'public':
            data = signup_social_user(provider=provider, user_id="", email=email, name=name, company=company)
        else:
            data = register_social_user(provider=provider, user_id="", email=email, name=name, company=company)
        self.context['user'] = data
        return attrs

class MicrosoftSocialAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    company = serializers.CharField(required = False)

    def validate(self, attrs):
        token = attrs.get("access_token")
        company = attrs.get("company")

        user_info = microsofthelper.get_auth_token(token)

        email = user_info["mail"].lower()
        name = user_info["displayName"]
        provider = 'microsoft'

        tenant = self.context['tenant']
        if tenant == 'public':
            data = signup_social_user(provider=provider, user_id="", email=email, name=name, company=company)
        else:
            data = register_social_user(provider=provider, user_id="", email=email, name=name, company=company)
        self.context['user'] = data
        return attrs
        




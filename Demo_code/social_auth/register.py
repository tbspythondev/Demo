
import os
import random

# Django imports
from decouple import config
from django.contrib.auth import authenticate, login
from accounts.models import User
from accounts.serializers import TokenObtainPairSerializer

# Rest framework imports
from rest_framework.exceptions import AuthenticationFailed


def generate_username(name):

    username = "".join(name.split(' ')).lower()
    if not User.objects.filter(username=username).exists():
        return username
    else:
        random_username = username + str(random.randint(0, 1000))
        return generate_username(random_username)


def register_social_user(provider, user_id, email, name, company):
    print(email,"============")
    filtered_user_by_email = User.objects.filter(email=email)
    print(filtered_user_by_email,"--")
    
    if filtered_user_by_email.exists():
        if provider == filtered_user_by_email[0].auth_provider:
            print("already exists and login")
            registered_user = authenticate(email=email, password=config('SOCIAL_SECRET'))
            print(registered_user,"USER")
    
            return {
                'username': registered_user.username,
                'email': registered_user.email,
                'tokens': registered_user.tokens()
               }

        else:
            raise AuthenticationFailed(
                detail='Please continue your login using ' + filtered_user_by_email[0].auth_provider)

    else:
        user = {'email': email,'password': config('SOCIAL_SECRET'),
                'company' : company, 'full_name' : name}
        user = User.objects.create_superuser(**user)
        user.is_verified = True
        user.auth_provider = provider
        user.save()

        new_user = authenticate(
            email=email, password=config('SOCIAL_SECRET'))
        # login(request, new_user)
        return {
            'email': new_user.email,
            'username': new_user.username,
            'tokens': new_user.tokens(),
            'company': new_user.company
        }


def signup_social_user(provider, user_id, email, name, company):
    print(email, "============")
    filtered_user_by_email = User.objects.filter(email=email)
    print(filtered_user_by_email, "--")
    user = {'email': email, 'password': config('SOCIAL_SECRET'),
             'company': company, 'full_name': name}
    user = User.objects.create_superuser(**user)
    user.is_verified = True
    user.auth_provider = provider
    user.save()

    return {
        'email': user.email,
        'username': user.username,
        'tokens': user.tokens()
    }
from collections import OrderedDict

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

# model imports
from drf_yasg import openapi
from drf_yasg.inspectors import PaginatorInspector
from rest_framework.pagination import PageNumberPagination

from accounts.models import LoginInformation
from datetime import datetime
from django.utils.formats import get_format

# other imports
import httpagentparser
import requests


def returnNotMatches(a, b):
    return [[x for x in a if x not in b], [x for x in b if x not in a]]


def sendmail(user_id, data):
    try:
        link = "http://localhost:8000/accounts/change_password/" + str(user_id) + "/"
        message_text = "Demo_CRM Platform : Successfull Registration \n\nYou have been successfully added as a user, Please find your credentials below \n\n" + "Email :  " + \
                       data['email'] + "\nPassword : " + data[
                           'password'] + "\n\nYou can change your password click link below.\n\n" + link
        send_mail('Demo_CRM Platform', message_text, settings.EMAIL_HOST_USER, [data['email']],
                  fail_silently=False)
        return True
    except Exception as e:
        return e


def visitor_ip_address(META):
    x_forwarded_for = META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = META.get('REMOTE_ADDR')
    return ip


def deviceDetails(request, email):
    try:
        META = request.META
        print("META", META)

        # ip = visitor_ip_address(META) # extract ip from META
        data = META["HTTP_USER_AGENT"]
        user_agent = httpagentparser.simple_detect(data)

        obj = LoginInformation(email=email, ip_address=META["REMOTE_ADDR"],
                               latitude=META["location"]["latitude"],
                               longitude=META["location"]["longitude"],
                               country=META["location"]["country"],
                               city=META["location"]["city"],
                               browser_name=user_agent[1], os=user_agent[0],
                               login_date=timezone.now(),
                               device_name="Desktop")
        obj.save()
        return "success"
    except Exception as e:
        return str(e)


class LimitOffsetPaginatorInspectorClass(PaginatorInspector):

    def get_paginated_response(self, paginator, response_schema):
        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict((
                ('count', openapi.Schema(type=openapi.TYPE_INTEGER)),
                ('next', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, x_nullable=True)),
                ('previous', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, x_nullable=True)),
                ('results', response_schema),
            )),
            required=['results']
        )


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


def parse_date(date_str):
    try:
        """Email date : Tue, 05 Oct 2021 10:24:45 -0000"""
        date_str = date_str.split(",")[1]
        date_str = date_str.split("-")[0]
        date_str = date_str.split("+")[0]
        date_str = date_str.strip()
        """String Now: 05 Oct 2021 10:24:45"""
        return datetime.strptime(date_str, "%d %b %Y %H:%M:%S")
    except:
        print(date_str)

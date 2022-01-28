from django.db import ProgrammingError
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import exception_handler
from rest_framework.renderers import JSONRenderer

from Multitenant.classes import SchemaFromRequest


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if response.status_code >= 400:
            return APIFailure(
                status = response.status_code,
                message = exc.detail
            )
    return response


class APISuccess:
    def __new__(cls,  message = 'Success', data={}, status=HTTP_200_OK):
        return Response(
            {
                'status': "Success",
                'message': message,
                'data': data
            },
            status
        )

class APIFailure:
    def __new__(cls, message = 'Error', status=HTTP_400_BAD_REQUEST):
        return Response(
            {
                'status': 'Failed',
                'message': message
            },
            status
        )


class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = {
            'status': renderer_context['response'].status_code < 400,
            'message': data.pop('message'),
            'data': data
        }
        return super(CustomJSONRenderer, self).render(data, accepted_media_type, renderer_context)


def tenant_api_exception(func):
    def inner(self, request, *args, **kwargs):
        try:
            schema = SchemaFromRequest(request)
            with schema_context(schema):
                try:
                    return func(self, request, *args, **kwargs)
                except ProgrammingError as p:
                    return APIFailure(message=p.__str__().split('\n')[0], status=status.HTTP_404_NOT_FOUND)
                except Exception as e:
                    error_msg = e.__str__().split('\n')[0]
                    return APIFailure(message=error_msg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_msg = e.__str__().split('\n')[0]
            return APIFailure(message=error_msg, status=status.HTTP_400_BAD_REQUEST)
    return inner

def tenant_api(func):
    def inner(self, request, *args, **kwargs):
        schema = SchemaFromRequest(request)
        with schema_context(schema):
            return func(self, request, *args, **kwargs)
    return inner


def api_exception(func):
    def inner(self, request, *args, **kwargs):
        try:
            return func(self, request, *args, **kwargs)
        except Exception as e:
            error_msg = e.__str__().split('\n')[0]
            return APIFailure(message=error_msg, status=status.HTTP_400_BAD_REQUEST)
    return inner
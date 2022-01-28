from django.db import connection
from django_tenants.middleware import TenantMainMiddleware

from Multitenant.classes import SchemaFromRequest, SchemaToTenant


class TenantMiddleware(TenantMainMiddleware):
    def __init__(self, get_response=None):
        super().__init__(get_response=get_response)

    def process_request(self, request):
        # Connection needs first to be at the public schema, as this is where
        # the tenant metadata is stored.
        schema = SchemaFromRequest(request)
        if schema == 'public':
            connection.set_schema_to_public()
        else:
            tenant = SchemaToTenant(schema)
            connection.set_tenant(tenant)

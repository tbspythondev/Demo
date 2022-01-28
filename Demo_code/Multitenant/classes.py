from decouple import config

from Demo_CRM import settings
from Tenant.models import Company, Domain
from Tenant.serializer import CompanySerializer


class CreateTenant:

    def __new__(cls, request):
        tenant_serializer = CompanySerializer(data=request.data, context=request.data.get('company'))
        if tenant_serializer.is_valid():
            tenant = tenant_serializer.save()
            return tenant, CompanySerializer(tenant).data
        return [NameToSchema(request.data.get('company'))]


# getters

class SchemaFromRequest:
    def __new__(cls, request, public=settings.DOMAIN, tenant_model=Company):
        schema = request.META.get('HTTP_COMPANY', None)
        if schema is None:
            return "public"
        domain = Domain.objects.filter(domain__istartswith=str(schema).lower()).first()
        if domain is None:
            raise Exception('This company does not exist')
        return domain.tenant.schema_name



class SchemaToName:
    def __new__(cls, schema: str):
        company = Company.objects.filter(schema_name=schema).first()
        if company is None:
            raise Exception('No company with this schema exists')
        return company.name

class SchemaToTenant:
    def __new__(cls, schema: str):
        url = '.'.join([schema.replace('_', '-').lower(), config('DOMAIN')])
        tenant = Company.objects.filter(schema_name=schema).first()
        if tenant is None:
            name = SchemaToName(schema)
            raise Exception(f'The Company "{name}" does not exist.')
        return tenant

# setters

class NameToUrl:
    def __new__(cls, name: str):
        return '.'.join([name.replace(' ', '-').lower(), config('DOMAIN')])

class NameToSchema:
    def __new__(cls, name: str):
        return name.replace(' ', '_').lower()




from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        return None, None

    def authenticate_header(self, request):
        return 'JWT'


class JWTScheme(OpenApiAuthenticationExtension):
    target_class = JWTAuthentication
    name = 'JWTAuthentication'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }

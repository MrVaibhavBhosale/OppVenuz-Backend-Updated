from rest_framework.authentication import get_authorization_header

def swagger_auto_bearer(get_response):
    def middleware(request):
        auth = get_authorization_header(request).decode('utf-8')
        if auth and not auth.startswith('Bearer '):
            request.META['HTTP_AUTHORIZATION'] = f"Bearer {auth}"
        return get_response(request)
    return middleware

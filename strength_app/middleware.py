class PermissionsPolicyMiddleware:
    """Add Permissions-Policy header to allow camera access on deployed site."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Permissions-Policy'] = 'camera=(self), microphone=(self)'
        return response

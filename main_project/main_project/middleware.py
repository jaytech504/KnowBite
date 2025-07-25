from django.conf import settings

class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add CSP headers
        if hasattr(settings, 'CSP_HEADER'):
            csp_parts = []
            for directive, sources in settings.CSP_HEADER.items():
                if sources:
                    # Join the sources with spaces and add to CSP parts
                    csp_parts.append(f"{directive} {' '.join(sources)}")
            
            if csp_parts:
                # Join all parts with semicolons and set the header
                response["Content-Security-Policy"] = "; ".join(csp_parts)
                # Also set the report-only header for testing
                response["Content-Security-Policy-Report-Only"] = "; ".join(csp_parts)
        
        return response

import ipaddress
import os

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import resolve


ALLOWED_IPS = getattr(settings, 'ALLOWED_IPS', None)

if ALLOWED_IPS is None:
    ips = os.environ.get('ALLOWED_IPS', '')
    ALLOWED_IPS = [ip.strip() for ip in ips.split(',') if ip != '']

ALLOWED_IP_RANGES = getattr(settings, 'ALLOWED_IP_RANGES', None)

if ALLOWED_IP_RANGES is None:
    ranges = os.environ.get('ALLOWED_IP_RANGES', '')
    ALLOWED_IP_RANGES = [rnge.strip() for rnge in ranges.split(',') if rnge != '']

RESTRICT_IPS = getattr(settings, 'RESTRICT_IPS', None)

if RESTRICT_IPS is None:
    RESTRICT_IPS = os.environ.get('RESTRICT_IPS', '').lower() == 'true' or os.environ.get('RESTRICT_IPS') == '1'

ALLOW_ADMIN = getattr(settings, 'ALLOW_ADMIN', None)

if ALLOW_ADMIN is None:
    ALLOW_ADMIN = os.environ.get('ALLOW_ADMIN', '').lower() == 'true' or os.environ.get('ALLOW_ADMIN') == '1'

ALLOW_AUTHENTICATED = getattr(settings, 'ALLOW_AUTHENTICATED', None)

if ALLOW_AUTHENTICATED is None:
    allow_auth = os.environ.get('ALLOW_AUTHENTICATED', '')
    ALLOW_AUTHENTICATED = allow_auth.lower() == 'true' or allow_auth == '1'


class IpWhitelister():
    """
    Simple middlware to allow IP addresses via settings variables ALLOWED_IPS, ALLOWED_IP_RANGES.

    The settings must have RESTRICT_IPS = True for IP checking to perform, else the middlware does nothing.
    """

    def get_client_ip(self, request):
        """
        Get the incoming request's originating IP, looks first for X_FORWARDED_FOR header, which is provided by some
        PaaS platforms, since the Django REMOTE_ADDR is affected by internal routing.  Fallback to the REMOTE_ADDR if
        the header is not present
        """

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        return ip

    def process_request(self, request):
        if RESTRICT_IPS:
            # Get the app name
            app_name = resolve(request.path).app_name
            authenticated = request.user.is_authenticated()

            # Allow access to the admin
            if app_name == 'admin' and ALLOW_ADMIN:
                return None

            # Allow access to authenticated users
            if authenticated and ALLOW_AUTHENTICATED:
                return None

            block_request = True
            # Get the incoming IP address
            request_ip_str = self.get_client_ip(request)
            request_ip = ipaddress.ip_address(request_ip_str)

            # If it's in the ALLOWED_IPS, don't block it
            if request_ip_str in ALLOWED_IPS:
                block_request = False

            # If it's within a ALLOWED_IP_RANGE, don't block it
            for allowed_range in ALLOWED_IP_RANGES:
                if request_ip in ipaddress.ip_network(allowed_range):
                    block_request = False
                    break

            # Otherwise, 403 Forbidden
            if block_request:
                raise PermissionDenied()

        return None

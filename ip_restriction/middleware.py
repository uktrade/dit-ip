import os
import ipaddress
import logging

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import resolve
from django.conf import settings


class IpWhitelister():
    """
    Simple middlware to allow IP addresses via settings variables ALLOWED_IPS, ALLOWED_IP_RANGES.

    Made to be compatible with Django 1.9 and also 1.10+
    """

    logger = logging.getLogger(__name__)

    def __init__(self, get_response=None):
        self.get_response = get_response
        self.RESTRICT_IPS = self._get_config_var('RESTRICT_IPS', bool)
        self.ALLOWED_IPS = self._get_config_var('ALLOWED_IPS', list)
        self.ALLOWED_IP_RANGES = self._get_config_var('ALLOWED_IP_RANGES', list)
        self.ALLOW_ADMIN = self._get_config_var('ALLOW_ADMIN', bool)
        self.ALLOW_AUTHENTICATED = self._get_config_var('ALLOW_AUTHENTICATED', bool)

    def __call__(self, request):
        response = self.process_request(request)
        
        if not response and self.get_response:
            response = self.get_response(request)
        
        return response

    def _get_config_var(self, name, vartype):
        """
        Get the whitelist config variable from the Django settings, or from the environment.
        Environment variables take preference over Django settings
        """

        env_val = os.environ.get(name)
        setting_val = getattr(settings, name, None)

        if vartype == bool:
            if env_val is None:
                return setting_val is True
            else:
                return env_val.lower() == 'true' or env_val == '1'
        else:
            if env_val is None:
                return setting_val if setting_val is not None else []
            else:
                return [val.strip() for val in env_val.split(',') if val != '']

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
        if self.RESTRICT_IPS:
            # Get the app name
            app_name = resolve(request.path).app_name
            authenticated = request.user.is_authenticated()

            # Allow access to the admin
            if app_name == 'admin' and self.ALLOW_ADMIN:
                return None

            # Allow access to authenticated users
            if authenticated and self.ALLOW_AUTHENTICATED:
                return None

            block_request = True
            # Get the incoming IP address
            request_ip_str = self.get_client_ip(request)
            request_ip = ipaddress.ip_address(request_ip_str)

            # If it's in the ALLOWED_IPS, don't block it
            if request_ip_str in self.ALLOWED_IPS:
                block_request = False

            # If it's within a ALLOWED_IP_RANGE, don't block it
            for allowed_range in self.ALLOWED_IP_RANGES:
                try:
                    network = ipaddress.ip_network(allowed_range)
                except ValueError as e:
                    self.logger.warning('Failed to parse specific network address: {}'.format("".join(e.args)))
                    continue

                if request_ip in network:
                    block_request = False
                    break

            # Otherwise, 403 Forbidden
            if block_request:
                raise PermissionDenied()

        return None

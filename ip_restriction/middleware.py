import os
import ipaddress
import logging

from django.core.exceptions import PermissionDenied
try:
    from django.core.urlresolvers import resolve
except ImportError:
    from django.urls import resolve
from django.conf import settings
from django.http import Http404
from django import VERSION


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
        self.RESTRICT_ADMIN_BY_IPS = self._get_config_var('RESTRICT_ADMIN_BY_IPS', bool)
        self.ALLOWED_ADMIN_IPS = self._get_config_var('ALLOWED_ADMIN_IPS', list)
        self.ALLOWED_ADMIN_IP_RANGES = self._get_config_var('ALLOWED_ADMIN_IP_RANGES', list)

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

    def get_client_ip_list(self, request):
        """
        Get the incoming request's originating IP, looks first for X_FORWARDED_FOR header, which is provided by some
        PaaS platforms, since the Django REMOTE_ADDR is affected by internal routing.  Fallback to the REMOTE_ADDR if
        the header is not present
        """

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:
            ips = x_forwarded_for.split(',')
            ips = map(str.strip, ips)
        else:
            ips = [request.META.get('REMOTE_ADDR')]

        return ips

    def is_blocked_ip(self, request, allowed_ips, allowed_ip_ranges):
        # Default blocked
        block_request = True

        # Get the incoming IP address
        request_ips = self.get_client_ip_list(request)

        for request_ip_str in request_ips:
            request_ip = ipaddress.ip_address(request_ip_str)

            # If it's in the ALLOWED_IPS, don't block it
            if request_ip_str in allowed_ips:
                block_request = False
                break

            # If it's within a ALLOWED_IP_RANGE, don't block it
            for allowed_range in allowed_ip_ranges:
                try:
                    network = ipaddress.ip_network(allowed_range)
                except ValueError as e:
                    self.logger.warning('Failed to parse specific network address: {}'.format("".join(e.args)))
                    continue

                if request_ip in network:
                    block_request = False
                    break

            if block_request is False:
                break                

        return block_request

    def process_request(self, request):
        # Get the app name
        app_name = resolve(request.path).app_name
        if self.RESTRICT_IPS:

            if VERSION >= (1, 10):
                authenticated = request.user.is_authenticated
            else:
                authenticated = request.user.is_authenticated()

            # Allow access to the admin
            if app_name == 'admin' and self.ALLOW_ADMIN:
                return None

            # Allow access to authenticated users
            if authenticated and self.ALLOW_AUTHENTICATED:
                return None

            block_request = self.is_blocked_ip(
                request,
                allowed_ips=self.ALLOWED_IPS,
                allowed_ip_ranges=self.ALLOWED_IP_RANGES
            )

            # Otherwise, 403 Forbidden
            if block_request:
                raise PermissionDenied()

        if self.RESTRICT_ADMIN_BY_IPS and app_name == 'admin':
            block_request = self.is_blocked_ip(
                request,
                allowed_ips=self.ALLOWED_ADMIN_IPS,
                allowed_ip_ranges=self.ALLOWED_ADMIN_IP_RANGES
            )
            # raise 404
            if block_request:
                raise Http404()

        return None

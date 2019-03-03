from unittest.mock import patch

from django.test import TestCase, override_settings
from django.test.client import Client
try:
    from django.core.urlresolvers import reverse_lazy
except ImportError:
    from django.urls import reverse_lazy
from django.contrib.auth.models import User

from .decorators import override_environment


example_url = reverse_lazy('example')


class TestIPRestriction(TestCase):
    """
    Test various aspects of the IpWhitelister middelware by changing Django settings.
    Other test in test_config, already test the difference between changing Django's
    settings and setting environemnt variable.  Here we just use the one method.
    """

    @classmethod
    def setUpClass(cls):
        cls.username = 'testuser'
        cls.password = '12345'
        cls.user = User.objects.create(username=cls.username)
        cls.user.set_password('12345')
        cls.user.is_superuser = True
        cls.user.save()

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()

    def _get_response_code_for_ip(self, ip, url=example_url, login=False):
        # Helper function to set an originating IP address to the given IP, and request
        # our one example view, returning the response's status code
        client = Client(REMOTE_ADDR=ip)

        if login:
            client.login(username=self.user.username, password=self.password)

        resp = client.get(url)
        return resp.status_code

    def _get_response_code_for_header(self, ips, url=example_url, login=False):
        # Helper function to set an originating IP address to the given IP, and request
        # our one example view, returning the response's status code
        client = Client(HTTP_X_FORWARDED_FOR=ips)

        if login:
            client.login(username=self.user.username, password=self.password)

        resp = client.get(url)
        return resp.status_code

    def test_default_no_ip_restriction(self):
        # By default, without specifying in settings or environment variables
        # requests should be allowed and not interefed with by the middleware
        resp = self.client.get(example_url)
        self.assertEqual(resp.status_code, 200)

    @override_settings(RESTRICT_IPS=False)
    def test_no_ip_restriction(self):
        # Specifying in settings that IPs should not be restricted and confirm
        # requests are allowed and not interefed with by the middleware
        resp = self.client.get(example_url)
        self.assertEqual(resp.status_code, 200)

    @override_settings(RESTRICT_IPS=True)
    def test_basic_ip_restriction(self):
        # Enable IP restriction, but set no allowed IPs or network ranges,
        # confirm that requests return a 403
        resp = self.client.get(example_url)
        self.assertEqual(resp.status_code, 403)

    @override_settings(RESTRICT_IPS=True, ALLOWED_IPS=['127.0.0.1', '192.168.0.1'])
    def test_allowed_ips(self):
        # Restict IPs to a list of known IPs and check that they are allowed, but other IPs
        # are forbidden
        code = self._get_response_code_for_ip('127.0.0.1')
        self.assertEqual(code, 200)

        code = self._get_response_code_for_ip('192.168.0.1')
        self.assertEqual(code, 200)

        code = self._get_response_code_for_ip('127.0.0.2')
        self.assertEqual(code, 403)

        code = self._get_response_code_for_ip('192.168.0.2')
        self.assertEqual(code, 403)

        # Check multiple IPs in the header, first 2 bad IPs
        code = self._get_response_code_for_header('127.0.0.2, 192.168.0.2')
        self.assertEqual(code, 403)

        # Check a blocked one, and an allowed one
        code = self._get_response_code_for_header('127.0.0.2, 192.168.0.1')
        self.assertEqual(code, 200)

        # Check an allowed one, and a blocked one
        code = self._get_response_code_for_header('127.0.0.1, 192.168.0.2')
        self.assertEqual(code, 200)

    @override_settings(RESTRICT_IPS=True, ALLOWED_IP_RANGES=['192.168.0.0/31'])
    def test_allowed_ip_ranges(self):
        # Specift a very limited IP range, and check that the 2 IP within it receive a 200
        # and that an IP just beyond the range is forbidden
        code = self._get_response_code_for_ip('192.168.0.0')
        self.assertEqual(code, 200)

        code = self._get_response_code_for_ip('192.168.0.1')
        self.assertEqual(code, 200)

        code = self._get_response_code_for_ip('192.168.0.2')
        self.assertEqual(code, 403)

        # Check multiple IPs in the header, first 2 bad IPs
        code = self._get_response_code_for_header('127.0.0.2, 192.168.0.2')
        self.assertEqual(code, 403)

        # Check a blocked one, and an allowed one
        code = self._get_response_code_for_header('127.0.0.2, 192.168.0.1')
        self.assertEqual(code, 200)

        # Check an allowed one, and a blocked one
        code = self._get_response_code_for_header('192.168.0.1, 127.0.0.1')
        self.assertEqual(code, 200)

    @patch('ip_restriction.IpWhitelister.logger')
    @override_settings(RESTRICT_IPS=True, ALLOWED_IP_RANGES=['127.0.0.1/30'])
    def test_invalid_network_range_logging(self, mock_logger):
        # Supply a 'broken' format of CIDR ip range, check that the request is forbidden
        # and that a warning log message is produced
        code = self._get_response_code_for_ip('127.0.0.1')
        self.assertEqual(code, 403)
        self.assertTrue(mock_logger.warning.called)

    @override_settings(RESTRICT_IPS=True, ALLOW_ADMIN=True)
    def test_allow_admin(self):
        # with IP restriction on, with no allowed IPs, but ALLOWED_ADMIN=True, all views
        # be forbidden, except the admin views
        resp = self.client.get(example_url)
        self.assertEqual(resp.status_code, 403)

        # The admin views are allowed and return 200
        resp = self.client.get(reverse_lazy('admin:login'))
        self.assertEqual(resp.status_code, 200)

        # But without ALLOW_AUTHENTICATED, logging in still forbids access to the views
        code = self._get_response_code_for_ip('127.0.0.1', example_url, login=True)
        self.assertEqual(code, 403)


    @override_settings(RESTRICT_IPS=True, ALLOW_AUTHENTICATED=True)
    def test_authenticated_allowed(self):
        # Access to the views are disallowed, even the admin views, but when authenticated
        # no restrictions are in place
        resp = self.client.get(example_url)
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get(reverse_lazy('admin:login'))
        self.assertEqual(resp.status_code, 403)

        code = self._get_response_code_for_ip('127.0.0.1', example_url, login=True)
        self.assertEqual(code, 200)

    @override_environment(
        RESTRICT_IPS=False,
        RESTRICT_ADMIN_BY_IPS=True,
        ALLOWED_ADMIN_IPS=['127.0.0.1', '192.168.0.1'])
    def test_allow_all_views_restrict_admin_views(self):
        resp = self.client.get(example_url)
        self.assertEqual(resp.status_code, 200)

        admin_url = reverse_lazy('admin:login')
        # get admin view from allowed IP
        response_code = self._get_response_code_for_ip(
            '127.0.0.1',
            url=admin_url
        )
        self.assertEqual(response_code, 200)

        # get admin view from blocked IP
        response_code = self._get_response_code_for_ip(
            '1.1.1.1',
            url=admin_url
        )
        self.assertEqual(response_code, 404)

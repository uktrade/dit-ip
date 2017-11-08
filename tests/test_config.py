from django.test import TestCase, override_settings

from ip_restriction import IpWhitelister
from .decorators import override_environment


class TestIPRestrictionConfig(TestCase):

    def test_default_config(self):
        restrictor = IpWhitelister()
        self.assertFalse(restrictor.RESTRICT_IPS)
        self.assertFalse(restrictor.ALLOW_ADMIN)
        self.assertFalse(restrictor.ALLOW_AUTHENTICATED)
        self.assertEquals(restrictor.ALLOWED_IPS, [])
        self.assertEquals(restrictor.ALLOWED_IP_RANGES, [])
        self.assertFalse(restrictor.RESTRICT_ADMIN_BY_IPS)
        self.assertEqual(restrictor.ALLOWED_ADMIN_IPS, [])
        self.assertEqual(restrictor.ALLOWED_ADMIN_IP_RANGES, [])

    @override_settings(
        RESTRICT_IPS=True,
        ALLOW_ADMIN=True,
        ALLOW_AUTHENTICATED=True,
        ALLOWED_IPS=['192.168.0.1'],
        ALLOWED_IP_RANGES=['192.168.0.0/24'],
        RESTRICT_ADMIN_BY_IPS=True,
        ALLOWED_ADMIN_IPS=['192.168.0.1'],
        ALLOWED_ADMIN_IP_RANGES=['192.168.0.0/24'],
    )
    def test_django_settings(self):
        restrictor = IpWhitelister()
        self.assertTrue(restrictor.RESTRICT_IPS)
        self.assertTrue(restrictor.ALLOW_ADMIN)
        self.assertTrue(restrictor.ALLOW_AUTHENTICATED)
        self.assertEquals(restrictor.ALLOWED_IPS, ['192.168.0.1'])
        self.assertEquals(restrictor.ALLOWED_IP_RANGES, ['192.168.0.0/24'])
        self.assertTrue(restrictor.RESTRICT_ADMIN_BY_IPS)
        self.assertEquals(restrictor.ALLOWED_ADMIN_IPS, ['192.168.0.1'])
        self.assertEquals(
            restrictor.ALLOWED_ADMIN_IP_RANGES,
            ['192.168.0.0/24']
        )

    @override_settings(
        RESTRICT_IPS=False,
        ALLOW_ADMIN=False,
        ALLOW_AUTHENTICATED=False,
        ALLOWED_IPS=['192.168.0.1'],
        ALLOWED_IP_RANGES=['192.168.0.0/24'],
        RESTRICT_ADMIN_BY_IPS=False,
        ALLOWED_ADMIN_IPS=['192.168.0.1'],
        ALLOWED_ADMIN_IP_RANGES=['192.168.0.0/24'],
    )
    @override_environment(
        RESTRICT_IPS=True,
        ALLOW_ADMIN=True,
        ALLOW_AUTHENTICATED=True,
        ALLOWED_IPS=['192.168.0.2'],
        ALLOWED_IP_RANGES=['192.168.0.0/20'],
        RESTRICT_ADMIN_BY_IPS=True,
        ALLOWED_ADMIN_IPS=['192.168.0.2'],
        ALLOWED_ADMIN_IP_RANGES=['192.168.0.0/20'],
    )
    def test_environment_trumps_settings(self):
        restrictor = IpWhitelister()
        self.assertTrue(restrictor.RESTRICT_IPS)
        self.assertTrue(restrictor.ALLOW_ADMIN)
        self.assertTrue(restrictor.ALLOW_AUTHENTICATED)
        self.assertEquals(restrictor.ALLOWED_IPS, ['192.168.0.2'])
        self.assertEquals(restrictor.ALLOWED_IP_RANGES, ['192.168.0.0/20'])
        self.assertTrue(restrictor.RESTRICT_ADMIN_BY_IPS)
        self.assertEquals(restrictor.ALLOWED_ADMIN_IPS, ['192.168.0.2'])
        self.assertEquals(
            restrictor.ALLOWED_ADMIN_IP_RANGES,
            ['192.168.0.0/20']
        )

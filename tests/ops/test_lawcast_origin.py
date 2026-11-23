import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class LawcastOriginTests(unittest.TestCase):
    def test_missing_and_malformed_credentials_fail_closed(self):
        for value in ("", "short", "g" * 64):
            result = subprocess.run(
                [sys.executable, str(ROOT / "ops/lawcast-origin/check-env.py")],
                env={**os.environ, "LAWCAST_API_SERVICE_TOKEN": value},
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            if value:
                self.assertNotIn(value.encode(), result.stderr)

    def test_valid_credentials_are_accepted_without_output(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "ops/lawcast-origin/check-env.py")],
            env={**os.environ, "LAWCAST_API_SERVICE_TOKEN": "a" * 64},
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"")

    def test_proxy_authentication_precedes_loopback_forwarding(self):
        source = (ROOT / "ops/lawcast-origin/Caddyfile").read_text()
        self.assertLess(source.index('respond @unauthorized "Forbidden" 403'), source.index("reverse_proxy @api"))
        self.assertIn("header_up -X-Lawcast-Service-Token", source)
        self.assertIn("request>headers>X-Lawcast-Service-Token delete", source)
        self.assertIn("disable_http_challenge", source)
        self.assertIn("127.0.0.1:3001", source)

    def test_service_is_independent_and_unprivileged(self):
        source = (ROOT / "ops/lawcast-origin/lawcast-origin.service").read_text()
        self.assertIn("DynamicUser=yes", source)
        self.assertIn("CapabilityBoundingSet=CAP_NET_BIND_SERVICE", source)
        self.assertIn("EnvironmentFile=/etc/lawcast-origin/service.env", source)
        self.assertNotIn("Requires=nginx", source)
        self.assertNotIn("Requires=docker", source)

import os
import sys
import types
from unittest import TestCase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from hf_diagnose import diagnose  # noqa: E402


def http_error(status, text=""):
    exc = Exception("boom")
    exc.response = types.SimpleNamespace(status_code=status, text=text)
    return exc


class HfDiagnoseTests(TestCase):
    def test_status_to_code(self):
        cases = [
            (401, "", "TOKEN_INVALID"),
            (403, "forbidden", "TOKEN_FORBIDDEN"),
            (402, "", "PLAN_REQUIRED"),
            (403, "Add a payment method", "PLAN_REQUIRED"),
            (409, "", "ALREADY_EXISTS"),
            (500, "oops", "UNKNOWN"),
        ]
        for status, text, code in cases:
            self.assertEqual(diagnose(http_error(status, text), "create_repo")["code"], code, (status, text))

    def test_already_exists_is_not_a_failure(self):
        self.assertTrue(diagnose(http_error(409), "create_repo")["ok"])
        self.assertFalse(diagnose(http_error(403), "create_repo")["ok"])

    def test_no_response_is_unknown(self):
        self.assertEqual(diagnose(ValueError("net down"), "whoami")["code"], "UNKNOWN")

    def test_message_truncated_and_secret_redacted(self):
        leaked = "hf_" + "a" * 30
        v = diagnose(http_error(403, leaked + "x" * 2000), "whoami")
        self.assertLessEqual(len(v["message"]), 500)
        self.assertNotIn(leaked, v["message"])

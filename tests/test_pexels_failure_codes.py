"""Safe Pexels one-item failure diagnostics never copy source URLs or keys."""
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from v12_pexels_audition import safe_failure_code


class PexelsFailureCodesTests(unittest.TestCase):
    def test_known_finite_failure_states(self):
        self.assertEqual(safe_failure_code(RuntimeError(
            "Video exceeds safe single-asset size limit")), "SOURCE_OVER_FILE_SIZE_LIMIT")
        self.assertEqual(safe_failure_code(RuntimeError(
            "Official URL did not return a video file")), "NOT_A_VIDEO_RESPONSE")
        self.assertEqual(safe_failure_code(RuntimeError(
            "Redirect outside official Pexels video delivery host")), "UNTRUSTED_REDIRECT_REJECTED")
        self.assertEqual(safe_failure_code(RuntimeError(
            "Unsupported duration")), "SOURCE_DURATION_UNSUPPORTED")

    def test_http_network_and_unknown_codes(self):
        self.assertEqual(safe_failure_code(HTTPError(
            "https://www.pexels.com/video/example-123/", 403, "denied", {}, None)),
            "HTTP_REJECTED_OR_UNAVAILABLE")
        self.assertEqual(safe_failure_code(URLError("proxy connection failed")),
                         "NETWORK_UNAVAILABLE_OR_TIMEOUT")
        reason=safe_failure_code(RuntimeError("token SECRET_CREDENTIAL_xxx"))
        self.assertEqual(reason, "OTHER_FILE_OR_DOWNLOAD_ERROR")
        self.assertNotIn("SECRET", reason)


if __name__ == "__main__":
    unittest.main()

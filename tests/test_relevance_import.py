import os
import sys
import unittest
from unittest.mock import patch


class RelevanceImportTest(unittest.TestCase):
    def test_relevance_module_imports_when_socks_proxy_is_set(self):
        proxy_env = {
            "HTTP_PROXY": "socks5://127.0.0.1:1080",
            "HTTPS_PROXY": "socks5://127.0.0.1:1080",
            "ALL_PROXY": "socks5://127.0.0.1:1080",
        }

        sys.modules.pop("relevance", None)

        with patch.dict(os.environ, proxy_env, clear=False):
            import relevance

        self.assertTrue(hasattr(relevance, "check_website_relevance"))


if __name__ == "__main__":
    unittest.main()

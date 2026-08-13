import unittest

from relevance import _check_with_heuristics


class HeuristicRelevanceTest(unittest.TestCase):
    def test_detects_guest_post_page(self):
        result = _check_with_heuristics(
            "Sports Guest Post | Write for us",
            "https://www.thesportsmirror.com/sports-guest-post-write-for-us",
            "sports",
            "UAE",
            "Submit your sports guest post. Write for us and contribute articles.",
        )

        self.assertIn("Guest post potential: High", result)
        self.assertIn("Industry match: High", result)
        self.assertRegex(result, r"Relevance score: (8[0-9]|9[0-9]|100)")

    def test_rejects_marketplace(self):
        result = _check_with_heuristics(
            "Guest Posting Service",
            "https://prposting.com/publishers/links-uae",
            "sports",
            "UAE",
            "Buy guest post and link building service.",
        )

        self.assertIn("Guest post potential: Low", result)
        self.assertIn("Relevance score: 10", result)


if __name__ == "__main__":
    unittest.main()

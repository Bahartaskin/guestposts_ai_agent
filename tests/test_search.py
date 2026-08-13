import unittest

from search import create_search_query, is_excluded_domain, remove_duplicate_urls


class SearchQueryTest(unittest.TestCase):
    def test_create_search_query_targets_guest_posts(self):
        query = create_search_query("sports", "UAE")

        self.assertIn("guest post", query)
        self.assertIn("write for us", query)
        self.assertIn("sports", query)
        self.assertIn("UAE", query)


class DomainFilterTest(unittest.TestCase):
    def test_excludes_wikipedia(self):
        self.assertTrue(
            is_excluded_domain(
                "https://en.wikipedia.org/wiki/Sport_in_the_United_Arab_Emirates"
            )
        )

    def test_excludes_semrush(self):
        self.assertTrue(
            is_excluded_domain(
                "https://www.semrush.com/trending-websites/ae/sports"
            )
        )

    def test_allows_blog_sites(self):
        self.assertFalse(
            is_excluded_domain("https://www.arabianbusiness.com/sports")
        )


class DuplicateUrlTest(unittest.TestCase):
    def test_remove_duplicate_urls(self):
        results = [
            {"title": "A", "url": "https://Example.com/page/"},
            {"title": "B", "url": "https://example.com/page"},
        ]

        unique = remove_duplicate_urls(results)

        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0]["url"], "https://example.com/page")


if __name__ == "__main__":
    unittest.main()

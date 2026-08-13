import os
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from tavily import TavilyClient


load_dotenv()


class SearchProvider:
    def search(self, query):
        raise NotImplementedError


class TavilySearchProvider(SearchProvider):

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY is not set."
            )

        self.client = TavilyClient(
            api_key=api_key
        )

    def search(self, query):

        response = self.client.search(
            query=query,
            search_depth="advanced",
            max_results=10
        )

        return response["results"]


EXCLUDED_DOMAINS = [
    "wikipedia.org",
    "wikimedia.org",
    "semrush.com",
    "similarweb.com",
    "alexa.com",
    "noon.com",
    "amazon.",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "linkpublishers.com",
    "prposting.com",
    "guestpostlinks.net",
    "feedspot.com",
    "brandmajlis.com",
    "blogspot.com",
    "blogger.com",
    "yoursite.com",
    "example.com",
    "example.org",
    "example.net",
]

EXCLUDED_RESULT_KEYWORDS = [
    "link building agency",
    "link building service",
    "guest posting service",
    "guest post service",
    "seo agency",
    "seo services",
    "backlink service",
    "buy backlinks",
    "sell backlinks",
    "link building",
    "example",
    "test",
    "sample",
    "placeholder",
]
def create_search_query(industry, geography):
    return (
        f"{industry} blog OR magazine OR news "
        f'"write for us" OR "guest post" OR contribute '
        f"{geography}"
    )


def is_excluded_domain(url):
    """Skip aggregators, social media, and major e-commerce sites."""
    domain = urlparse(url).netloc.lower()

    return any(
        excluded in domain
        for excluded in EXCLUDED_DOMAINS
    )

def is_excluded_result(result):
    """
    Detects search results that are likely to be
    SEO/link-building services rather than publishers.
    """

    title = result.get("title", "").lower()
    url = result.get("url", "").lower()

    text = f"{title} {url}"

    return any(
        keyword in text
        for keyword in EXCLUDED_RESULT_KEYWORDS
    )
def normalize_url(url):
    """
    Converts a URL into a consistent format.
    """

    # Remove Markdown formatting if it exists
    if url.startswith("[") and "](" in url:
        url = url.split("](")[1].rstrip(")")

    url = url.strip()

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    # Remove trailing slash
    path = parsed.path.rstrip("/")

    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        "",
        "",
        ""
    ))

    return normalized


def remove_duplicate_urls(results):
    """
    Removes duplicate URLs from search results.
    """

    unique_results = []
    seen_urls = set()

    for result in results:

        url = normalize_url(result["url"])

        if url not in seen_urls:

            seen_urls.add(url)

            result["url"] = url

            unique_results.append(result)

    return unique_results


def get_search_results(query, search_provider):

    results = search_provider.search(query)
    results = remove_duplicate_urls(results)

    filtered_results = []

    for result in results:

        if is_excluded_domain(result["url"]):
            continue

        if is_excluded_result(result):
            continue

        filtered_results.append(result)

    return filtered_results
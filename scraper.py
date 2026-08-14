import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

from logger import logger


# ============================================================
# Constants
# ============================================================

EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE
)

CONTACT_EMAIL_KEYWORDS = [
    "info",
    "contact",
    "hello",
    "office",
    "general",
    "admin",
    "marketing",
    "media",
    "press",
    "editorial",
    "editor",
    "content",
    "partnership",
    "partnerships",
    "business",
    "collab",
    "collaboration",
    "sales",
    "support"
]

EXCLUDED_EMAIL_KEYWORDS = [
    "privacy",
    "legal",
    "abuse",
    "security",
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "unsubscribe"
]

EXCLUDED_LINK_KEYWORDS = [
    "privacy",
    "legal",
    "terms",
    "cookie",
    "donate",
    "login",
    "signup",
    "register",
    "category",
    "tag",
    "search",
    "cart",
    "checkout",
    "account",
    "wishlist",
    "javascript:"
]

EXCLUDED_EMAIL_DOMAINS = [
    "blogspot.com",
    "blogger.com",
    "example.com",
    "example.org",
    "example.net",
    "yoursite.com",
    "yourdomain.com",
    "domain.com",
    "test.com",
]

EXCLUDED_EMAIL_LOCAL_PARTS = [
    "test",
    "testing",
    "example",
    "user",
    "username",
    "name",
    "yourname",
    "firstname",
    "lastname",
    "email",
    "youremail",
    "your-email",
    "your_email",

]
# ============================================================
# Website filtering
# ============================================================

EXCLUDED_WEBSITE_DOMAINS = [
    "fiverr.com",
    "upwork.com",
    "freelancer.com",
    "peopleperhour.com",

    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "twitter.com",
    "x.com",
    "reddit.com",

    "amazon.com",
    "amazon.ae",
    "noon.com",

    "wikipedia.org",
    "wikimedia.org",

    "semrush.com",
    "similarweb.com",
    "alexa.com",

    "prnews.io",
    "feedspot.com",
]

EXCLUDED_WEBSITE_SIGNALS = [
    "guest post marketplace",
    "guest posting marketplace",
    "link building service",
    "link-building service",
    "seo agency",
    "seo services",
    "guest posting service",
    "buy guest posts",
    "buy guest post",
    "guest post packages",
    "guest post pricing",
    "sponsored post packages",
]

INCLUDE_LINK_KEYWORDS = [
    "contact",
    "contact-us",
    "contactus",
    "guest-post",
    "guestpost",
    "guest_post",
    "write-for-us",
    "writeforus",
    "write_for_us",
    "contribute",
    "contributor",
    "editorial",
    "advertise",
    "advertising",
    "partnership",
    "partnerships",
    "partners",
    "collaborate",
    "collaboration",
    "media",
    "press",
    "blog",
    "news"
]


# ============================================================
# Session
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9"
})


# ============================================================
# Email normalization
# ============================================================

def normalize_email(email):
    """
    Cleans and normalizes an email address.
    """

    email = unquote(email)

    email = email.strip()

    # Remove mailto prefix
    if email.lower().startswith("mailto:"):
        email = email[7:]

    # Remove query parameters
    email = email.split("?")[0]

    # Remove surrounding characters
    email = email.strip(
        " <>[](){}\"'.,;:"
    )

    return email.lower()


def normalize_obfuscated_email(text):
    """
    Converts common obfuscated email formats into
    normal email format.

    Examples:

    info [at] example [dot] com
    info (at) example (dot) com
    info at example dot com
    """

    normalized = text

    replacements = [
        (r"\s*\[\s*at\s*\]\s*", "@"),
        (r"\s*\(\s*at\s*\)\s*", "@"),
        (r"\s+at\s+", "@"),

        (r"\s*\[\s*dot\s*\]\s*", "."),
        (r"\s*\(\s*dot\s*\)\s*", "."),
        (r"\s+dot\s+", ".")
    ]

    for pattern, replacement in replacements:
        normalized = re.sub(
            pattern,
            replacement,
            normalized,
            flags=re.IGNORECASE
        )

    return normalized


# ============================================================
# Email validation
# ============================================================

def is_valid_email(email):
    """
    Checks whether an email has a valid format.
    """

    if not email:
        return False

    email = normalize_email(email)

    if not EMAIL_REGEX.fullmatch(email):
        return False

    return True


# ============================================================
# Extract emails
# ============================================================

def extract_emails_from_html(html):
    """
    Extracts emails from both visible text and mailto links.
    Also detects common obfuscated email formats.
    """

    emails = set()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # --------------------------------------------------------
    # 1. mailto links
    # --------------------------------------------------------

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"].strip()

        if href.lower().startswith("mailto:"):

            email = normalize_email(href)

            if is_valid_email(email):
                emails.add(email)

    # --------------------------------------------------------
    # 2. Visible page text
    # --------------------------------------------------------

    text = soup.get_text(
        " ",
        strip=True
    )

    # Normal emails
    for email in EMAIL_REGEX.findall(text):

        email = normalize_email(email)

        if is_valid_email(email):
            emails.add(email)

    # --------------------------------------------------------
    # 3. Obfuscated emails
    # --------------------------------------------------------

    obfuscated_text = normalize_obfuscated_email(text)

    for email in EMAIL_REGEX.findall(
        obfuscated_text
    ):

        email = normalize_email(email)

        if is_valid_email(email):
            emails.add(email)

    return sorted(emails)


# ============================================================
# Scrape website
# ============================================================

def scrape_website(url):
    """
    Downloads a webpage and extracts email addresses.
    """

    try:

        response = session.get(
            url,
            timeout=(5, 15)
        )

        response.raise_for_status()

        emails = extract_emails_from_html(
            response.text
        )

        logger.info(
            f"Email extraction: {url} | "
            f"Emails found: {len(emails)}"
        )

        return emails

    except requests.exceptions.Timeout:

        print(
            f"Timeout while accessing: {url}"
        )

        logger.warning(
            f"Timeout while accessing: {url}"
        )

        return []

    except requests.exceptions.RequestException as e:

        print(
            f"Request failed for {url}: {e}"
        )

        logger.error(
            f"Request failed for {url}: {e}"
        )

        return []

    except Exception as e:

        print(
            f"Unexpected error for {url}: {e}"
        )

        logger.error(
            f"Unexpected error for {url}: {e}"
        )

        return []


# ============================================================
# Extract links
# ============================================================

def extract_links(url):
    """
    Extracts same-domain hyperlinks from a website.
    """

    try:

        response = session.get(
            url,
            timeout=(5, 15)
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        base_domain = urlparse(url).netloc.lower()

        links = set()

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link["href"].strip()

            if not href:
                continue

            if href.startswith(
                (
                    "#",
                    "javascript:",
                    "tel:",
                    "mailto:"
                )
            ):
                continue

            absolute_url = urljoin(
                url,
                href
            )

            parsed = urlparse(
                absolute_url
            )

            # Only HTTP/HTTPS
            if parsed.scheme not in [
                "http",
                "https"
            ]:
                continue

            # Only same website
            if parsed.netloc.lower() != base_domain:
                continue

            # Remove fragments
            clean_url = (
                f"{parsed.scheme}://"
                f"{parsed.netloc}"
                f"{parsed.path}"
            )

            if parsed.query:
                clean_url += f"?{parsed.query}"

            links.add(clean_url)

        return list(links)

    except requests.exceptions.Timeout:

        print(
            f"Timeout while extracting links: {url}"
        )

        logger.warning(
            f"Timeout while extracting links: {url}"
        )

        return []

    except requests.exceptions.RequestException as e:

        print(
            f"Request failed while extracting links: {url}"
        )

        logger.error(
            f"Request failed while extracting links: "
            f"{url} | {e}"
        )

        return []

    except Exception as e:

        print(
            f"Unexpected error while extracting links: {url}"
        )

        logger.error(
            f"Unexpected error while extracting links: "
            f"{url} | {e}"
        )

        return []


# ============================================================
# Find relevant links
# ============================================================

def find_relevant_links(links):
    """
    Finds pages that may contain contact,
    guest-post, editorial, blog, or partnership opportunities.
    """

    relevant_links = []

    for link in links:

        link_lower = link.lower()

        # ----------------------------------------------------
        # Exclude irrelevant URLs
        # ----------------------------------------------------

        if any(
            keyword in link_lower
            for keyword in EXCLUDED_LINK_KEYWORDS
        ):
            continue

        # ----------------------------------------------------
        # Include useful pages
        # ----------------------------------------------------

        if any(
            keyword in link_lower
            for keyword in INCLUDE_LINK_KEYWORDS
        ):

            relevant_links.append(link)

    # Remove duplicates
    relevant_links = list(
        dict.fromkeys(relevant_links)
    )

    # Limit crawling
    # Prevent hundreds of unnecessary requests
    return relevant_links[:15]


# ============================================================
# Scrape relevant pages
# ============================================================

def scrape_relevant_pages(relevant_links):
    """
    Visits relevant pages and extracts email addresses.
    """

    page_emails = {}

    for link in relevant_links:

        print(
            f"\nProcessing relevant page: {link}"
        )

        emails = scrape_website(
            link
        )

        page_emails[link] = emails

        print(
            "Emails found:",
            emails
        )

        logger.info(
            f"Relevant page processed: {link} | "
            f"Emails found: {len(emails)}"
        )

    return page_emails


# ============================================================
# Email validation
# ============================================================

def validate_emails(emails):
    """
    Separates useful contact emails from
    privacy/legal/system/placeholder emails.
    """

    valid_emails = []
    excluded_emails = []

    for email in emails:

        email = normalize_email(email)

        if not is_valid_email(email):
            continue

        local_part, domain = email.split("@", 1)

        local_part = local_part.lower().strip()
        domain = domain.lower().strip()

        # ----------------------------------------------------
        # Exclude clearly non-contact emails
        # ----------------------------------------------------

        if any(
            keyword in local_part
            for keyword in EXCLUDED_EMAIL_KEYWORDS
        ):
            excluded_emails.append(email)
            continue

        # ----------------------------------------------------
        # Exclude placeholder/test local parts
        # ----------------------------------------------------

        if local_part in EXCLUDED_EMAIL_LOCAL_PARTS:
            excluded_emails.append(email)
            continue

        # ----------------------------------------------------
        # Exclude placeholder/test domains
        # ----------------------------------------------------

        if any(
            domain == excluded_domain
            or domain.endswith("." + excluded_domain)
            for excluded_domain in EXCLUDED_EMAIL_DOMAINS
        ):
            excluded_emails.append(email)
            continue

        # ----------------------------------------------------
        # Exclude obvious placeholder domains
        # ----------------------------------------------------

        if (
            "example" in domain
            or "yourdomain" in domain
            or "yoursite" in domain
        ):
            excluded_emails.append(email)
            continue

        # ----------------------------------------------------
        # Otherwise keep the email
        # ----------------------------------------------------

        valid_emails.append(email)

    # Remove duplicates
    valid_emails = sorted(
        set(valid_emails)
    )

    excluded_emails = sorted(
        set(excluded_emails)
    )

    return (
        valid_emails,
        excluded_emails
    )


# ============================================================
# Score emails
# ============================================================

def score_email(email):
    """
    Gives higher scores to emails that are more useful
    for guest-post outreach.
    """

    local_part = email.split("@")[0].lower()

    score = 0

    # Strong outreach contacts
    if local_part in [
        "partnership",
        "partnerships",
        "marketing",
        "media",
        "press",
        "editorial",
        "editor",
        "content"
    ]:
        score += 10

    # General contacts
    elif local_part in [
        "info",
        "contact",
        "hello",
        "office",
        "business"
    ]:
        score += 7

    # Other potentially useful contacts
    elif local_part in [
        "sales",
        "support",
        "admin"
    ]:
        score += 4

    return score


def get_best_contact_emails(emails, max_emails=5):
    """
    Sorts contact emails by outreach usefulness.
    """

    valid_emails, excluded_emails = validate_emails(
        emails
    )

    valid_emails = sorted(
        valid_emails,
        key=score_email,
        reverse=True
    )

    return (
        valid_emails[:max_emails],
        excluded_emails
    )


# ============================================================
# Get website text
# ============================================================

def get_website_text(url):
    """
    Downloads a website and returns its visible text.
    Used by the AI relevance checker.
    """

    try:

        response = session.get(
            url,
            timeout=(5, 15)
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for element in soup([
            "script",
            "style",
            "noscript",
            "svg"
        ]):

            element.decompose()

        text = soup.get_text(
            " ",
            strip=True
        )

        # Remove excessive whitespace
        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text[:8000]

    except requests.exceptions.Timeout:

        print(
            f"Timeout while getting website text: {url}"
        )

        logger.warning(
            f"Timeout while getting website text: {url}"
        )

        return ""

    except requests.exceptions.RequestException as e:

        print(
            f"Request failed while getting website text: {url}"
        )

        logger.error(
            f"Request failed while getting website text: "
            f"{url} | {e}"
        )

        return ""

    except Exception as e:

        print(
            f"Unexpected error while getting website text: {e}"
        )

        logger.error(
            f"Unexpected error while getting website text: "
            f"{url} | {e}"
        )

        return ""

    # ============================================================
# Website filtering helpers
# ============================================================

def get_domain(url):
    """
    Returns the normalized domain name.
    """

    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def is_excluded_website_domain(url):
    """
    Checks whether the website belongs to a known
    marketplace, social platform, aggregator, or
    major e-commerce platform.
    """

    domain = get_domain(url)

    for excluded_domain in EXCLUDED_WEBSITE_DOMAINS:

        excluded_domain = excluded_domain.lower()

        if (
            domain == excluded_domain
            or domain.endswith("." + excluded_domain)
        ):
            return True

    return False


def detect_website_type(title, url, website_text):
    """
    Classifies a website into a simple category.

    Possible values:

        publisher
        marketplace
        agency
        directory
        ecommerce
        social
        unknown
    """

    domain = get_domain(url)

    combined_text = " ".join([
        title or "",
        url or "",
        website_text or "",
    ]).lower()

    # --------------------------------------------------------
    # Known excluded domains
    # --------------------------------------------------------

    if is_excluded_website_domain(url):

        if any(
            platform in domain
            for platform in [
                "fiverr.com",
                "upwork.com",
                "freelancer.com",
                "peopleperhour.com",
            ]
        ):
            return "marketplace"

        if any(
            platform in domain
            for platform in [
                "facebook.com",
                "instagram.com",
                "linkedin.com",
                "youtube.com",
                "twitter.com",
                "x.com",
                "reddit.com",
            ]
        ):
            return "social"

        if any(
            platform in domain
            for platform in [
                "amazon.com",
                "amazon.ae",
                "noon.com",
            ]
        ):
            return "ecommerce"

        if any(
            platform in domain
            for platform in [
                "wikipedia.org",
                "wikimedia.org",
                "feedspot.com",
                "prnews.io",
            ]
        ):
            return "directory"

        return "unknown"

    # --------------------------------------------------------
    # Marketplace / link building
    # --------------------------------------------------------

    marketplace_signals = [
        "guest post marketplace",
        "guest posting marketplace",
        "link building service",
        "link-building service",
        "guest posting service",
        "buy guest posts",
        "buy guest post",
        "guest post packages",
        "guest post pricing",
        "sponsored post packages",
    ]

    if any(
        signal in combined_text
        for signal in marketplace_signals
    ):
        return "marketplace"

    # --------------------------------------------------------
    # SEO / digital marketing agency
    # --------------------------------------------------------

    agency_signals = [
        "seo agency",
        "seo services",
        "digital marketing agency",
        "link building agency",
        "search engine optimization agency",
    ]

    if any(
        signal in combined_text
        for signal in agency_signals
    ):
        return "agency"

    # --------------------------------------------------------
    # Directory / aggregator
    # --------------------------------------------------------

    directory_signals = [
        "directory of websites",
        "list of guest post sites",
        "guest posting sites",
        "top guest post sites",
        "best guest posting sites",
        "list of blogs",
        "website directory",
    ]

    if any(
        signal in combined_text
        for signal in directory_signals
    ):
        return "directory"

    # --------------------------------------------------------
    # E-commerce
    # --------------------------------------------------------

    ecommerce_signals = [
        "add to cart",
        "shopping cart",
        "checkout",
        "buy now",
        "shop now",
        "product catalog",
    ]

    ecommerce_hits = sum(
        1
        for signal in ecommerce_signals
        if signal in combined_text
    )

    if ecommerce_hits >= 2:
        return "ecommerce"

    # --------------------------------------------------------
    # Publisher signals
    # --------------------------------------------------------

    publisher_signals = [
        "news",
        "magazine",
        "journal",
        "blog",
        "articles",
        "latest news",
        "editorial",
        "contributors",
        "write for us",
        "guest post",
        "submit article",
    ]

    publisher_hits = sum(
        1
        for signal in publisher_signals
        if signal in combined_text
    )

    if publisher_hits >= 2:
        return "publisher"

    return "unknown"


def is_acceptable_website_type(
    title,
    url,
    website_text
):
    """
    Determines whether the website is suitable for
    further guest-post processing.

    Returns:

        accepted: bool
        website_type: str
        reason: str
    """

    website_type = detect_website_type(
        title,
        url,
        website_text
    )

    if website_type == "marketplace":

        return (
            False,
            website_type,
            "Website is a guest-post or link-building marketplace."
        )

    if website_type == "agency":

        return (
            False,
            website_type,
            "Website is an SEO or digital marketing agency."
        )

    if website_type == "directory":

        return (
            False,
            website_type,
            "Website is an aggregator or directory rather than a publisher."
        )

    if website_type == "ecommerce":

        return (
            False,
            website_type,
            "Website appears to be an e-commerce platform."
        )

    if website_type == "social":

        return (
            False,
            website_type,
            "Website is a social media platform."
        )

    if website_type == "publisher":

        return (
            True,
            website_type,
            "Website appears to be a content publisher."
        )

    # --------------------------------------------------------
    # Unknown websites are not automatically rejected.
    #
    # Relevance analysis may still determine that they
    # are legitimate publishers.
    # --------------------------------------------------------

    return (
        True,
        website_type,
        "Website type could not be determined automatically."
    )
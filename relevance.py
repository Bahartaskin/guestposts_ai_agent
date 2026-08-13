import os
import time
import re

from dotenv import load_dotenv


load_dotenv()


# ============================================================
# API CONFIGURATION
# ============================================================

gemini_api_key = os.getenv("GEMINI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
ai_provider = os.getenv("AI_PROVIDER", "auto").lower()


# ============================================================
# FALLBACK RESPONSES
# ============================================================

UNAVAILABLE_RESPONSE = (
    "Relevance score: 0\n"
    "Industry match: Low\n"
    "Geography match: Low\n"
    "Guest post potential: Low\n"
    "Analysis method: Unavailable\n"
    "Reason: AI relevance analysis was unavailable."
)


# ============================================================
# GUEST POST SIGNALS
# ============================================================

GUEST_POST_SIGNALS = [
    "write for us",
    "write-for-us",
    "guest post",
    "guest-post",
    "submit article",
    "submit your article",
    "contribute",
    "contributor",
    "contributors",
    "editorial guidelines",
    "submission guidelines",
    "become a contributor",
    "guest author",
    "guest contributor",
]


# ============================================================
# MARKETPLACE / BAD SITE SIGNALS
# ============================================================

MARKETPLACE_SIGNALS = [
    "buy guest post",
    "buy guest posts",
    "link building service",
    "link building agency",
    "guest posting service",
    "guest post service",
    "guest posting services",
    "guest post marketplace",
    "guest post marketplace",
    "paid backlinks",
    "backlink marketplace",
    "seo marketplace",
    "publishers/links",
    "seo agency",
]


# ============================================================
# GENERIC NON-PUBLISHER SIGNALS
# ============================================================

NON_PUBLISHER_SIGNALS = [
    "shopping cart",
    "add to cart",
    "buy now",
    "product catalog",
    "checkout",
    "official government",
]


# ============================================================
# GEOGRAPHY ALIASES
# ============================================================

GEOGRAPHY_ALIASES = {
    "uae": [
        "uae",
        "united arab emirates",
        "dubai",
        "abu dhabi",
        "sharjah",
        "ajman",
        "fujairah",
        "ras al khaimah",
        "ras al-khaimah",
        "umm al quwain",
        "umm al-quwain",
        ".ae",
    ],
    "united arab emirates": [
        "uae",
        "united arab emirates",
        "dubai",
        "abu dhabi",
        "sharjah",
        "ajman",
        "fujairah",
        "ras al khaimah",
        "ras al-khaimah",
        "umm al quwain",
        "umm al-quwain",
        ".ae",
    ],
}


# ============================================================
# PROMPT
# ============================================================

def _build_prompt(
    title,
    url,
    industry,
    geography,
    website_text
):
    return f"""
You are evaluating a website for a guest-post outreach campaign.

Target industry: {industry}
Target geography: {geography}

Website title:
{title}

Website URL:
{url}

Website content:
{website_text[:10000]}

Evaluate whether this website is a realistic guest-post outreach opportunity.

Return exactly these fields:

Relevance score: a number from 0 to 100
Industry match: High, Medium, or Low
Geography match: High, Medium, or Low
Guest post potential: High, Medium, or Low
Analysis method: AI
Reason: one short sentence

Rules:

1. Industry match:
Evaluate whether the website genuinely covers the target industry.

2. Geography match:
Evaluate whether the website has a genuine connection to the target geography.
Do not consider the geography a match merely because the target geography appears
inside the search query or because the URL was found through a geographic search.

3. Guest post potential:
High means the website appears to accept external guest articles or contributor submissions.
Medium means there is some evidence but it is uncertain.
Low means it is unlikely to accept external guest posts.

4. Reject:
- SEO agencies
- link-building agencies
- guest-post marketplaces
- backlink sellers
- directories and aggregators
- e-commerce stores
- government websites
- social media platforms
- websites that only advertise guest-post services

5. A website can be highly relevant to the industry but still have Low geography match.

6. A website can have High geography match but Low industry match.

7. Do not automatically give a high score just because the website contains the target keywords.

8. The score should represent the overall suitability for the target campaign.

Keep the answer concise.
"""


# ============================================================
# GEMINI CLIENT
# ============================================================

def _get_gemini_client():
    """
    Creates Gemini client lazily.

    Removes SOCKS proxy variables when necessary because
    some local environments cause google client import errors.
    """

    if not gemini_api_key:
        return None

    proxy_vars = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]

    has_socks_proxy = any(
        os.getenv(var, "").lower().startswith("socks")
        for var in proxy_vars
    )

    if has_socks_proxy:
        for var in proxy_vars:
            os.environ.pop(var, None)

    try:
        from google import genai

        return genai.Client(
            api_key=gemini_api_key
        )

    except ImportError as exc:

        if "socksio" in str(exc).lower():
            return None

        raise


# ============================================================
# GEMINI
# ============================================================

def _check_with_gemini(prompt):

    client = _get_gemini_client()

    if not gemini_api_key:
        return None

    if client is None:
        print(
            "Gemini client could not be created."
        )
        return None

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        if not response or not response.text:
            return None

        return response.text

    except Exception as e:

        error_text = str(e).lower()

        is_rate_limited = (
            "429" in str(e)
            or "rate" in error_text
            or "quota" in error_text
            or "resource_exhausted" in error_text
        )

        if is_rate_limited:

            print(
                "Gemini quota/rate limit reached. "
                "Skipping Gemini retries for this run."
            )

        else:

            print(
                f"Gemini relevance check failed: {e}"
            )

        return None


# ============================================================
# OPENAI
# ============================================================

def _check_with_openai(prompt):

    if not openai_api_key:
        return None

    try:

        from openai import OpenAI

        client = OpenAI(
            api_key=openai_api_key
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
        )

        if not response.choices:
            return None

        content = response.choices[0].message.content

        if not content:
            return None

        return content

    except Exception as e:

        print(
            f"OpenAI relevance check failed: {e}"
        )

        return None


# ============================================================
# TEXT HELPERS
# ============================================================

def _normalize_text(text):
    """
    Normalizes text for keyword matching.
    """

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def _industry_match(
    industry,
    title,
    url,
    website_text
):
    """
    Conservative industry matching.

    IMPORTANT:
    The target industry itself is NOT injected into the text.
    We only search the actual website content.
    """

    industry = _normalize_text(industry)

    content = _normalize_text(
        " ".join([
            title,
            url,
            website_text[:12000],
        ])
    )

    # Exact industry phrase
    if industry in content:
        return True, 3

    # Individual words for multi-word industries
    words = [
        word
        for word in re.findall(
            r"[a-z0-9]+",
            industry
        )
        if len(word) >= 4
    ]

    if not words:
        return False, 0

    hits = sum(
        1
        for word in words
        if re.search(
            rf"\b{re.escape(word)}\b",
            content
        )
    )

    if hits >= max(1, len(words) // 2):
        return True, 2

    if hits >= 1:
        return True, 1

    return False, 0


def _geography_match(
    geography,
    title,
    url,
    website_text
):
    """
    Conservative geography matching.

    For UAE we recognize UAE, United Arab Emirates,
    major UAE cities, and .ae domains.

    Geography is calculated only from website content,
    title and URL.
    """

    geography_key = _normalize_text(
        geography
    )

    aliases = GEOGRAPHY_ALIASES.get(
        geography_key,
        [geography_key]
    )

    title_text = _normalize_text(title)
    url_text = _normalize_text(url)
    website_content = _normalize_text(
        website_text[:12000]
    )

    full_content = " ".join([
        title_text,
        url_text,
        website_content,
    ])

    matches = []

    for alias in aliases:

        if alias in full_content:
            matches.append(alias)

    unique_matches = set(matches)

    # Strong signals
    strong_aliases = {
        "uae",
        "united arab emirates",
        ".ae",
    }

    strong_matches = (
        unique_matches.intersection(
            strong_aliases
        )
    )

    # Strong geographic signal
    if strong_matches:
        return True, "High"

    # Multiple city signals
    city_matches = [
        alias
        for alias in unique_matches
        if alias not in strong_aliases
    ]

    if len(city_matches) >= 2:
        return True, "High"

    # One genuine geographic signal
    if len(city_matches) == 1:
        return True, "Medium"

    return False, "Low"


def _guest_post_match(
    title,
    url,
    website_text
):
    """
    Detects guest-post signals in actual website content.
    """

    content = _normalize_text(
        " ".join([
            title,
            url,
            website_text[:12000],
        ])
    )

    hits = []

    for signal in GUEST_POST_SIGNALS:

        if signal in content:
            hits.append(signal)

    return hits


def _marketplace_match(
    title,
    url,
    website_text
):
    """
    Detects SEO/link-building marketplaces.
    """

    content = _normalize_text(
        " ".join([
            title,
            url,
            website_text[:12000],
        ])
    )

    for signal in MARKETPLACE_SIGNALS:

        if signal in content:
            return True

    return False


# ============================================================
# HEURISTIC FALLBACK
# ============================================================

def _check_with_heuristics(
    title,
    url,
    industry,
    geography,
    website_text
):
    """
    Conservative fallback when AI providers are unavailable.

    This is intentionally stricter than the previous version.
    """

    industry_hit, industry_strength = _industry_match(
        industry,
        title,
        url,
        website_text
    )

    geography_hit, geography_level = _geography_match(
        geography,
        title,
        url,
        website_text
    )

    guest_post_hits = _guest_post_match(
        title,
        url,
        website_text
    )

    is_marketplace = _marketplace_match(
        title,
        url,
        website_text
    )

    if is_marketplace:

        return (
            "Relevance score: 5\n"
            "Industry match: Low\n"
            "Geography match: Low\n"
            "Guest post potential: Low\n"
            "Analysis method: Heuristic\n"
            "Reason: Detected as an SEO or link-building marketplace rather than a publisher."
        )

    # --------------------------------------------------------
    # INDUSTRY MATCH
    # --------------------------------------------------------

    if industry_strength >= 3:
        industry_match = "High"
    elif industry_strength >= 1:
        industry_match = "Medium"
    else:
        industry_match = "Low"

    # --------------------------------------------------------
    # GUEST POST POTENTIAL
    # --------------------------------------------------------

    guest_count = len(
        set(guest_post_hits)
    )

    if guest_count >= 2:
        guest_post_potential = "High"
    elif guest_count == 1:
        guest_post_potential = "Medium"
    else:
        guest_post_potential = "Low"

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = 0

    # Industry
    if industry_match == "High":
        score += 35
    elif industry_match == "Medium":
        score += 20

    # Geography
    if geography_level == "High":
        score += 30
    elif geography_level == "Medium":
        score += 15

    # Guest post
    if guest_post_potential == "High":
        score += 30
    elif guest_post_potential == "Medium":
        score += 15

    # Small bonus for strong combination
    if (
        industry_match == "High"
        and geography_level == "High"
        and guest_post_potential == "High"
    ):
        score += 5

    score = min(
        score,
        100
    )

    # --------------------------------------------------------
    # REASON
    # --------------------------------------------------------

    if (
        industry_match == "High"
        and geography_level == "High"
        and guest_post_potential == "High"
    ):

        reason = (
            "Strong industry, geography, and guest-post signals "
            "were detected."
        )

    elif (
        industry_match == "High"
        and geography_level == "Low"
        and guest_post_potential == "High"
    ):

        reason = (
            "The website appears relevant to the industry and accepts "
            "guest posts, but no strong target-geography connection was detected."
        )

    elif (
        industry_match == "High"
        and geography_level != "Low"
        and guest_post_potential == "Medium"
    ):

        reason = (
            "The website matches the target industry and geography, "
            "but guest-post acceptance is not strongly confirmed."
        )

    elif not industry_hit:

        reason = (
            "No strong target-industry signals were detected."
        )

    elif not geography_hit:

        reason = (
            "No strong target-geography signals were detected."
        )

    elif not guest_post_hits:

        reason = (
            "No clear guest-post submission signals were detected."
        )

    else:

        reason = (
            "Some industry, geography, and guest-post signals were detected, "
            "but the match is not strong enough for automatic qualification."
        )

    return (
        f"Relevance score: {score}\n"
        f"Industry match: {industry_match}\n"
        f"Geography match: {geography_level}\n"
        f"Guest post potential: {guest_post_potential}\n"
        f"Analysis method: Heuristic\n"
        f"Reason: {reason}"
    )


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def check_website_relevance(
    title,
    url,
    industry,
    geography,
    website_text
):
    """
    Main relevance analysis function.

    Priority:
        1. Gemini
        2. OpenAI
        3. Conservative heuristic
    """

    prompt = _build_prompt(
        title,
        url,
        industry,
        geography,
        website_text
    )

    # --------------------------------------------------------
    # HEURISTIC ONLY MODE
    # --------------------------------------------------------

    if ai_provider == "heuristic":

        return _check_with_heuristics(
            title,
            url,
            industry,
            geography,
            website_text
        )

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    if (
        ai_provider in ["auto", "gemini"]
        and gemini_api_key
    ):

        result = _check_with_gemini(
            prompt
        )

        if result:

            return result

        if ai_provider == "gemini":

            return _check_with_heuristics(
                title,
                url,
                industry,
                geography,
                website_text
            )

    # --------------------------------------------------------
    # OPENAI
    # --------------------------------------------------------

    if (
        ai_provider in ["auto", "openai"]
        and openai_api_key
    ):

        result = _check_with_openai(
            prompt
        )

        if result:

            return result

    # --------------------------------------------------------
    # HEURISTIC FALLBACK
    # --------------------------------------------------------

    print(
        "Falling back to conservative heuristic relevance analysis..."
    )

    return _check_with_heuristics(
        title,
        url,
        industry,
        geography,
        website_text
    )
import os
import re
import time

from dotenv import load_dotenv


load_dotenv()


gemini_api_key = os.getenv("GEMINI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
ai_provider = os.getenv("AI_PROVIDER", "auto").lower()


GUEST_POST_SIGNALS = [
    "write for us",
    "write-for-us",
    "guest post",
    "guest-post",
    "submit article",
    "submit a guest post",
    "contribute",
    "editorial guidelines",
    "become a contributor",
    "guest contributor",
]

MARKETPLACE_SIGNALS = [
    "buy guest post",
    "buy guest posts",
    "guest posting service",
    "guest post service",
    "guest posting services",
    "link building service",
    "link building agency",
    "link-building agency",
    "seo agency",
    "seo marketplace",
    "guest post marketplace",
    "paid guest posting service",
    "guest post packages",
    "backlink marketplace",
]

AGGREGATOR_SIGNALS = [
    "top guest posting sites",
    "guest posting sites",
    "guest post websites",
    "list of guest post sites",
    "best guest post sites",
    "free guest posting sites",
    "guest post opportunities list",
]

LOW_QUALITY_SIGNALS = [
    "fiverr.com",
    "upwork.com",
    "slideserve.com",
    "prnews.io",
]

GEOGRAPHY_ALIASES = {
    "uae": [
        "uae",
        "united arab emirates",
        "dubai",
        "abu dhabi",
        "sharjah",
        "ajman",
        "ras al khaimah",
        "ras al-khaimah",
        "fujairah",
        "umm al quwain",
        ".ae",
    ],
    "uk": [
        "uk",
        "united kingdom",
        "england",
        "london",
        "manchester",
        ".co.uk",
        ".uk",
    ],
    "usa": [
        "usa",
        "united states",
        "america",
        "new york",
        "los angeles",
        "california",
        ".com",
    ],
}


def _build_prompt(
    title,
    url,
    industry,
    geography,
    website_text,
):
    return f"""
You are evaluating a website for a guest-post outreach campaign.

Target industry: {industry}
Target geography: {geography}

Website title: {title}
Website URL: {url}

Website content:
{website_text[:8000]}

Evaluate whether this website is a realistic guest-post outreach opportunity.

Return exactly:

Relevance score: a number from 0 to 100
Industry match: High, Medium, or Low
Geography match: High, Medium, or Low
Guest post potential: High, Medium, or Low
Reason: one short sentence

Important rules:

1. Industry match:
- High only if the website clearly focuses on the target industry.
- Medium if the industry is related but not the main focus.
- Low if there is little or no industry relevance.

2. Geography match:
- High only if the website clearly targets the requested geography.
- Medium if there is some meaningful geographic connection.
- Low if the website clearly focuses on another country or there is no meaningful geographic evidence.
- Do NOT assume geography from generic words.

3. Guest post potential:
- High if the website clearly accepts guest contributions.
- Medium if guest contributions appear possible but are not clearly established.
- Low if there is no real guest-post opportunity.

4. Reject:
- SEO agencies
- link-building agencies
- guest-post marketplaces
- backlink sellers
- Fiverr/Upwork-style services
- guest-post directories and aggregators

Do not give a high relevance score merely because the page contains
the words "write for us" or "guest post".

Keep the answer concise.
"""


def _get_gemini_client():
    """Create Gemini client lazily."""

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


def _check_with_gemini(prompt):
    client = _get_gemini_client()

    if not gemini_api_key:
        return None

    if client is None:
        print(
            "Gemini client could not be created. "
            "SOCKS proxy support is unavailable."
        )
        return None

    max_attempts = 2

    for attempt in range(1, max_attempts + 1):

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            return response.text

        except Exception as e:

            error_text = str(e).lower()

            is_rate_limited = (
                "429" in str(e)
                or "rate" in error_text
                or "quota" in error_text
            )

            if is_rate_limited and attempt < max_attempts:

                wait_seconds = 2 ** attempt

                print(
                    f"Gemini rate limited. Retrying in "
                    f"{wait_seconds}s..."
                )

                time.sleep(wait_seconds)

                continue

            print(
                f"Gemini relevance check failed: {e}"
            )

            return None


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
                    "content": prompt,
                }
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content

    except Exception as e:

        print(
            f"OpenAI relevance check failed: {e}"
        )

        return None


def _get_domain(url):
    url = url.lower()

    url = re.sub(
        r"^https?://",
        "",
        url,
    )

    return url.split("/")[0]


def _contains_any(text, signals):
    return any(
        signal.lower() in text
        for signal in signals
    )


def _count_signals(text, signals):
    return sum(
        1
        for signal in signals
        if signal.lower() in text
    )


def _get_geography_score(
    url,
    website_text,
    target_geography,
):
    """
    Determine geography relevance independently.

    This prevents a generic keyword such as "UAE" in the
    search context from automatically making a website
    geographically relevant.
    """

    target = target_geography.lower().strip()

    aliases = GEOGRAPHY_ALIASES.get(
        target,
        [target],
    )

    url_lower = url.lower()
    text_lower = website_text.lower()

    domain = _get_domain(url)

    # Strong domain-level evidence.
    if target == "uae" and domain.endswith(".ae"):
        return 30, "High"

    if target == "uk" and (
        domain.endswith(".co.uk")
        or domain.endswith(".uk")
    ):
        return 30, "High"

    # Strong URL evidence.
    url_hits = sum(
        1
        for alias in aliases
        if alias in url_lower
    )

    if url_hits >= 1:
        return 25, "High"

    # Count evidence in actual website content.
    content_hits = sum(
        1
        for alias in aliases
        if alias in text_lower
    )

    # Detect obvious competing geography.
    competing_geographies = {
        "uae": [
            ".co.uk",
            "united kingdom",
            "london",
            "england",
            "usa",
            "united states",
            "canada",
            "australia",
        ],
        "uk": [
            ".ae",
            "uae",
            "dubai",
            "abu dhabi",
            "united states",
            "usa",
        ],
    }

    competing = competing_geographies.get(
        target,
        [],
    )

    competing_hits = sum(
        1
        for signal in competing
        if signal in url_lower or signal in text_lower
    )

    if competing_hits > 0 and content_hits == 0:
        return 0, "Low"

    if content_hits >= 3:
        return 20, "High"

    if content_hits >= 1:
        return 10, "Medium"

    return 0, "Low"


def _check_with_heuristics(
    title,
    url,
    industry,
    geography,
    website_text,
):
    """
    Conservative fallback scoring.

    This function intentionally avoids giving a website 100
    simply because it contains guest-post keywords.
    """

    title_lower = title.lower()
    url_lower = url.lower()
    text_lower = website_text.lower()

    combined = " ".join(
        [
            title_lower,
            url_lower,
            text_lower,
        ]
    )

    # ---------------------------------------------------------
    # 1. Reject obvious marketplaces / agencies / aggregators
    # ---------------------------------------------------------

    if _contains_any(
        combined,
        MARKETPLACE_SIGNALS,
    ):
        return (
            "Relevance score: 0\n"
            "Industry match: Low\n"
            "Geography match: Low\n"
            "Guest post potential: Low\n"
            "Reason: This website appears to be an SEO or guest-post marketplace rather than a publisher."
        )

    if _contains_any(
        combined,
        AGGREGATOR_SIGNALS,
    ):
        return (
            "Relevance score: 0\n"
            "Industry match: Low\n"
            "Geography match: Low\n"
            "Guest post potential: Low\n"
            "Reason: This website appears to aggregate guest-post opportunities rather than publish content directly."
        )

    if _contains_any(
        url_lower,
        LOW_QUALITY_SIGNALS,
    ):
        return (
            "Relevance score: 0\n"
            "Industry match: Low\n"
            "Geography match: Low\n"
            "Guest post potential: Low\n"
            "Reason: This appears to be a third-party marketplace or distribution platform rather than a target publisher."
        )

    # ---------------------------------------------------------
    # 2. Industry scoring
    # ---------------------------------------------------------

    industry_lower = industry.lower()

    industry_aliases = [
        industry_lower,
    ]

    if industry_lower == "sports":
        industry_aliases.extend(
            [
                "sports",
                "sport",
                "athletics",
                "fitness",
                "football",
                "soccer",
                "basketball",
                "tennis",
                "golf",
                "running",
            ]
        )

    industry_hits = sum(
        1
        for signal in set(industry_aliases)
        if signal in combined
    )

    if industry_hits >= 3:
        industry_score = 40
        industry_match = "High"

    elif industry_hits >= 1:
        industry_score = 25
        industry_match = "Medium"

    else:
        industry_score = 0
        industry_match = "Low"

    # ---------------------------------------------------------
    # 3. Geography scoring
    # ---------------------------------------------------------

    geography_score, geography_match = _get_geography_score(
        url,
        website_text,
        geography,
    )

    # ---------------------------------------------------------
    # 4. Guest-post scoring
    # ---------------------------------------------------------

    guest_post_hits = _count_signals(
        combined,
        GUEST_POST_SIGNALS,
    )

    if guest_post_hits >= 3:
        guest_score = 20
        guest_potential = "High"

    elif guest_post_hits >= 1:
        guest_score = 12
        guest_potential = "Medium"

    else:
        guest_score = 0
        guest_potential = "Low"

    # ---------------------------------------------------------
    # 5. Publisher quality
    # ---------------------------------------------------------

    publisher_score = 0

    if (
        "blog" in combined
        or "magazine" in combined
        or "news" in combined
        or "publication" in combined
    ):
        publisher_score += 5

    if guest_post_hits >= 1:
        publisher_score += 3

    if industry_match == "High":
        publisher_score += 2

    publisher_score = min(
        publisher_score,
        10,
    )

    # ---------------------------------------------------------
    # 6. Final score
    # ---------------------------------------------------------

    score = (
        industry_score
        + geography_score
        + guest_score
        + publisher_score
    )

    score = min(
        score,
        100,
    )

    # Strong geographic mismatch should prevent qualification.
    if geography_match == "Low":
        score = min(
            score,
            59,
        )

    if industry_match == "Low":
        score = min(
            score,
            39,
        )

    if guest_potential == "Low":
        score = min(
            score,
            49,
        )

    # ---------------------------------------------------------
    # 7. Reason
    # ---------------------------------------------------------

    if geography_match == "Low":
        reason = (
            "The website may match the industry and guest-post criteria, "
            "but it lacks a meaningful connection to the target geography."
        )

    elif industry_match == "Low":
        reason = (
            "The website does not have a strong enough connection to the target industry."
        )

    elif guest_potential == "Low":
        reason = (
            "The website is relevant to the target audience but does not show clear guest-post opportunities."
        )

    elif geography_match == "High" and industry_match == "High":
        reason = (
            "The website strongly matches the target industry and geography and shows clear guest-post signals."
        )

    elif geography_match == "High":
        reason = (
            "The website has a strong geographic connection and shows guest-post potential, but industry relevance is limited."
        )

    else:
        reason = (
            "The website shows some industry and guest-post relevance, but the match is not strong enough."
        )

    return (
        f"Relevance score: {score}\n"
        f"Industry match: {industry_match}\n"
        f"Geography match: {geography_match}\n"
        f"Guest post potential: {guest_potential}\n"
        f"Reason: {reason}"
    )


def _parse_result(result):
    """
    Normalizes AI output and ensures all fields use valid values.
    """

    if not result:
        return None

    result = result.strip()

    # AI occasionally returns numbered output.
    result = re.sub(
        r"^\s*\d+\.\s*",
        "",
        result,
        flags=re.MULTILINE,
    )

    return result


def check_website_relevance(
    title,
    url,
    industry,
    geography,
    website_text,
):
    """
    Evaluate website relevance.

    Priority:
        1. Gemini
        2. OpenAI
        3. Conservative heuristic fallback
    """

    prompt = _build_prompt(
        title,
        url,
        industry,
        geography,
        website_text,
    )

    # Explicit heuristic mode.
    if ai_provider == "heuristic":
        return _check_with_heuristics(
            title,
            url,
            industry,
            geography,
            website_text,
        )

    # ---------------------------------------------------------
    # No API keys
    # ---------------------------------------------------------

    if not gemini_api_key and not openai_api_key:

        print(
            "Neither GEMINI_API_KEY nor OPENAI_API_KEY is set."
        )

        return _check_with_heuristics(
            title,
            url,
            industry,
            geography,
            website_text,
        )

    # ---------------------------------------------------------
    # Gemini
    # ---------------------------------------------------------

    result = _check_with_gemini(
        prompt
    )

    if result:
        return _parse_result(
            result
        )

    # ---------------------------------------------------------
    # OpenAI
    # ---------------------------------------------------------

    if ai_provider != "gemini":

        print(
            "Falling back to OpenAI for relevance analysis..."
        )

        result = _check_with_openai(
            prompt
        )

        if result:
            return _parse_result(
                result
            )

    # ---------------------------------------------------------
    # Heuristic fallback
    # ---------------------------------------------------------

    print(
        "Falling back to conservative heuristic relevance analysis..."
    )

    return _check_with_heuristics(
        title,
        url,
        industry,
        geography,
        website_text,
    )
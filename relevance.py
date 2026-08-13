import os
import time

from dotenv import load_dotenv


load_dotenv()


gemini_api_key = os.getenv("GEMINI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
ai_provider = os.getenv("AI_PROVIDER", "auto").lower()

UNAVAILABLE_RESPONSE = (
    "Relevance score: 0\n"
    "Industry match: Low\n"
    "Guest post potential: Low\n"
    "Reason: AI relevance analysis was unavailable."
)

GUEST_POST_SIGNALS = [
    "write for us",
    "guest post",
    "guest-post",
    "submit article",
    "contribute",
    "editorial guidelines",
    "become a contributor",
]

MARKETPLACE_SIGNALS = [
    "buy guest post",
    "link building service",
    "guest posting service",
    "publishers/links",
]


def _build_prompt(title, url, industry, geography, website_text):
    return f"""
You are evaluating a website for a guest-post outreach campaign.

Target industry: {industry}
Target geography: {geography}

Website title: {title}
Website URL: {url}

Website content:
{website_text[:8000]}

Evaluate this website and return exactly:

1. Relevance score: a number from 0 to 100
2. Industry match: High, Medium, or Low
3. Guest post potential: High, Medium, or Low
4. Reason: one short sentence

Important:
- Use ONLY High, Medium, or Low for Industry match.
- Use ONLY High, Medium, or Low for Guest post potential.
- Do NOT use values such as Medium-High or Low-Medium.
- Do NOT add extra categories.
- Reject SEO/link-building marketplaces and aggregator directories.

Focus on whether the website is relevant to the target
industry and geography and whether it could realistically
be suitable for guest-post outreach.

Keep the answer concise.
"""


def _get_gemini_client():
    """Create the Gemini client lazily and avoid SOCKS-proxy import crashes."""
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
        return genai.Client(api_key=gemini_api_key)
    except ImportError as exc:
        if "socksio" in str(exc).lower():
            return None
        raise


def _check_with_gemini(prompt):
    client = _get_gemini_client()

    if not gemini_api_key:
        return None

    if client is None:
        print("Gemini client could not be created. SOCKS proxy support is unavailable.")
        return None

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
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
                    f"Gemini rate limited. Retrying in {wait_seconds}s "
                    f"(attempt {attempt}/{max_attempts})..."
                )
                time.sleep(wait_seconds)
                continue

            print(f"Gemini relevance check failed: {e}")
            return None


def _check_with_heuristics(title, url, industry, geography, website_text):
    """Fallback scoring when AI providers are unavailable."""
    combined = " ".join([
        title.lower(),
        url.lower(),
        website_text.lower(),
        industry.lower(),
        geography.lower(),
    ])

    if any(signal in combined for signal in MARKETPLACE_SIGNALS):
        return (
            "Relevance score: 10\n"
            "Industry match: Low\n"
            "Guest post potential: Low\n"
            "Reason: Detected as an SEO marketplace rather than a publisher."
        )

    guest_post_hits = sum(
        1 for signal in GUEST_POST_SIGNALS
        if signal in combined
    )
    industry_hit = industry.lower() in combined
    geography_hit = geography.lower() in combined or ".ae" in url.lower()

    score = 40
    if industry_hit:
        score += 25
    if geography_hit:
        score += 20
    score += min(guest_post_hits * 10, 30)
    score = min(score, 100)

    if guest_post_hits >= 2 and industry_hit:
        potential = "High"
        industry_match = "High" if geography_hit else "Medium"
    elif guest_post_hits >= 1 or (industry_hit and geography_hit):
        potential = "Medium"
        industry_match = "Medium" if industry_hit else "Low"
    else:
        potential = "Low"
        industry_match = "Low"

    reason = (
        "Heuristic match based on guest-post signals and target keywords."
        if guest_post_hits
        else "Limited guest-post signals found without AI analysis."
    )

    return (
        f"Relevance score: {score}\n"
        f"Industry match: {industry_match}\n"
        f"Guest post potential: {potential}\n"
        f"Reason: {reason}"
    )


def _check_with_openai(prompt):
    if not openai_api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"OpenAI relevance check failed: {e}")
        return None


def check_website_relevance(
    title,
    url,
    industry,
    geography,
    website_text
):
    """
    Uses Gemini (with OpenAI fallback) to evaluate whether a website
    is suitable for guest-post opportunities.
    """

    prompt = _build_prompt(
        title,
        url,
        industry,
        geography,
        website_text
    )

    if ai_provider == "heuristic":
        return _check_with_heuristics(
            title,
            url,
            industry,
            geography,
            website_text
        )

    if not gemini_api_key and not openai_api_key:
        print("Neither GEMINI_API_KEY nor OPENAI_API_KEY is set.")
        return (
            "Relevance score: 0\n"
            "Industry match: Low\n"
            "Guest post potential: Low\n"
            "Reason: No AI API key is configured."
        )

    result = _check_with_gemini(prompt)

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

    print("Falling back to OpenAI for relevance analysis...")
    result = _check_with_openai(prompt)

    if result:
        return result

    print("Falling back to heuristic relevance analysis...")
    return _check_with_heuristics(
        title,
        url,
        industry,
        geography,
        website_text
    )


import csv
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from outreach import prepare_outreach_action
from logger import logger
from relevance import check_website_relevance
from scraper import (
    extract_links,
    find_relevant_links,
    get_best_contact_emails,
    get_website_text,
    scrape_relevant_pages,
    scrape_website,
)
from search import (
    TavilySearchProvider,
    create_search_query,
    get_search_results,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_JSON_PATH = "results.json"
DEFAULT_CSV_PATH = "results.csv"

MAX_CONTACT_EMAILS = 5


# ============================================================
# PARSE RELEVANCE RESULT
# ============================================================

def parse_relevance_result(
    result: str,
) -> Tuple[int, str, str, str, str, str]:
    """
    Parse the structured relevance response.

    Expected fields:

        Relevance score: 85
        Industry match: High
        Geography match: High
        Guest post potential: High
        Analysis method: AI
        Reason: ...

    Returns:

        (
            score,
            industry_match,
            geography_match,
            guest_post_potential,
            analysis_method,
            reason,
        )
    """

    if not result:
        return (
            0,
            "Low",
            "Low",
            "Low",
            "Unavailable",
            "No relevance analysis result.",
        )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score_match = re.search(
        r"Relevance score:\s*(\d+)",
        result,
        re.IGNORECASE,
    )

    score = (
        int(score_match.group(1))
        if score_match
        else 0
    )

    # Keep score inside 0-100.
    score = max(0, min(score, 100))

    # --------------------------------------------------------
    # INDUSTRY
    # --------------------------------------------------------

    industry_match = re.search(
        r"Industry match:\s*(High|Medium|Low)",
        result,
        re.IGNORECASE,
    )

    industry_match_value = (
        industry_match.group(1).capitalize()
        if industry_match
        else "Low"
    )

    # --------------------------------------------------------
    # GEOGRAPHY
    # --------------------------------------------------------

    geography_match = re.search(
        r"Geography match:\s*(High|Medium|Low)",
        result,
        re.IGNORECASE,
    )

    geography_match_value = (
        geography_match.group(1).capitalize()
        if geography_match
        else "Low"
    )

    # --------------------------------------------------------
    # GUEST POST POTENTIAL
    # --------------------------------------------------------

    potential_match = re.search(
        r"Guest post potential:\s*(High|Medium|Low)",
        result,
        re.IGNORECASE,
    )

    potential = (
        potential_match.group(1).capitalize()
        if potential_match
        else "Low"
    )

    # --------------------------------------------------------
    # ANALYSIS METHOD
    # --------------------------------------------------------

    method_match = re.search(
        r"Analysis method:\s*(AI|Heuristic|Unavailable)",
        result,
        re.IGNORECASE,
    )

    if method_match:
        analysis_method = (
            method_match.group(1).capitalize()
        )
    else:
        analysis_method = "AI"

    # --------------------------------------------------------
    # REASON
    # --------------------------------------------------------

    reason_match = re.search(
        r"Reason:\s*(.+)",
        result,
        re.IGNORECASE,
    )

    reason = (
        reason_match.group(1).strip()
        if reason_match
        else "No reason provided."
    )

    return (
        score,
        industry_match_value,
        geography_match_value,
        potential,
        analysis_method,
        reason,
    )


# ============================================================
# QUALIFICATION LOGIC
# ============================================================


def is_qualified(
    score,
    industry_match,
    geography_match,
    guest_post_potential,
    analysis_method,
):
    """
    Determines whether a website is a qualified
    guest-post opportunity.

    Qualification is based on:
    - valid analysis method
    - industry relevance
    - geography relevance
    - guest-post potential
    - overall relevance score
    """

    # --------------------------------------------------------
    # ANALYSIS METHOD
    # --------------------------------------------------------

    if analysis_method == "Unavailable":
        return False

    # --------------------------------------------------------
    # INDUSTRY
    # --------------------------------------------------------

    if industry_match == "Low":
        return False

    # Medium industry relevance is acceptable
    # when the overall opportunity is strong.
    if industry_match == "Medium" and score < 70:
        return False

    # --------------------------------------------------------
    # GEOGRAPHY
    # --------------------------------------------------------

    if geography_match == "Low":
        return False

    # --------------------------------------------------------
    # GUEST POST POTENTIAL
    # --------------------------------------------------------

    if guest_post_potential != "High":
        return False

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    # AI and heuristic analyses use the same
    # qualification threshold.
    #
    # This prevents the result from changing merely
    # because an AI provider is temporarily unavailable
    # and the system falls back to heuristics.

    if score < 70:
        return False

    return True



    # --------------------------------------------------------
    # HEURISTIC ANALYSIS
    # --------------------------------------------------------

    if analysis_method == "Heuristic":

        # Direct industry match
        if industry_match == "High":

            return score >= 75

        # Cross-industry but geographically strong
        if (
            industry_match == "Medium"
            and geography_match == "High"
        ):

            return score >= 65

        return False

    # --------------------------------------------------------
    # UNKNOWN METHOD
    # --------------------------------------------------------

    return False


# ============================================================
# PROCESS ONE SEARCH RESULT
# ============================================================

def process_search_result(
    result: Dict[str, Any],
    industry: str,
    geography: str,
    relevance_checker: Callable[..., str] = check_website_relevance,
) -> Optional[Dict[str, Any]]:
    """
    Process a single search result.

    Flow:

        Search result
            ↓
        Website text
            ↓
        AI relevance check
            ↓
        Qualification
            ↓
        Website email scraping
            ↓
        Relevant link extraction
            ↓
        Contact page scraping
            ↓
        Email validation / ranking
            ↓
        Qualified opportunity
    """

    title = result.get(
        "title",
        "Untitled website",
    )

    url = result.get(
        "url",
        "",
    )

    if not url:
        logger.warning(
            "Skipping search result without URL: %s",
            title,
        )

        return None

    print("\n" + "=" * 60)
    print(f"Title: {title}")
    print(f"URL: {url}")
    print("=" * 60)

    logger.info(
        "Processing website: %s",
        url,
    )

    # ========================================================
    # WEBSITE TEXT
    # ========================================================

    print("\nGetting website content...")

    try:
        website_text = get_website_text(url)

    except Exception as exc:
        logger.exception(
            "Failed to retrieve website text: %s",
            url,
        )

        print(
            f"Could not retrieve website content: {exc}"
        )

        return None

    if not website_text:

        print(
            "Could not retrieve website content "
            "for AI analysis."
        )

        logger.info(
            "Website content unavailable: %s",
            url,
        )

        return None

    # ========================================================
    # AI RELEVANCE ANALYSIS
    # ========================================================

    print("\nAI relevance analysis...")

    try:

        relevance_result = relevance_checker(
            title,
            url,
            industry,
            geography,
            website_text,
        )

    except Exception as exc:

        print(
            f"Relevance analysis failed: {exc}"
        )

        logger.exception(
            "Relevance analysis failed for %s",
            url,
        )

        return None

    print("\nAI Relevance Result:")
    print(relevance_result)

    # ========================================================
    # PARSE RELEVANCE RESULT
    # ========================================================

    (
        score,
        industry_match,
        geography_match,
        guest_post_potential,
        analysis_method,
        reason,
    ) = parse_relevance_result(
        relevance_result
    )

    print(
        f"\nParsed relevance score: {score}"
    )

    print(
        f"Parsed industry match: "
        f"{industry_match}"
    )

    print(
        f"Parsed geography match: "
        f"{geography_match}"
    )

    print(
        f"Parsed guest post potential: "
        f"{guest_post_potential}"
    )

    print(
        f"Analysis method: "
        f"{analysis_method}"
    )

    print(
        f"Parsed reason: "
        f"{reason}"
    )

    # ========================================================
    # QUALIFICATION
    # ========================================================

    qualified = is_qualified(
        score,
        industry_match,
        geography_match,
        guest_post_potential,
        analysis_method,
    )

    if not qualified:

        print(
            "\nSkipping website - "
            "not a qualified guest post opportunity."
        )

        logger.info(
            "Website skipped: %s | "
            "Score: %s | "
            "Industry: %s | "
            "Geography: %s | "
            "Potential: %s | "
            "Method: %s",
            url,
            score,
            industry_match,
            geography_match,
            guest_post_potential,
            analysis_method,
        )

        return None

    print(
        "\nWebsite passed relevance check."
    )

    logger.info(
        "Website passed relevance check: %s",
        url,
    )

    # ========================================================
    # SCRAPE MAIN WEBSITE EMAILS
    # ========================================================

    print("\nScraping website...")

    try:

        emails = scrape_website(
            url
        )

    except Exception as exc:

        logger.exception(
            "Website email scraping failed: %s",
            url,
        )

        print(
            f"Website email scraping failed: {exc}"
        )

        emails = []

    print(
        "\nEmails found:",
        emails,
    )

    # ========================================================
    # EXTRACT LINKS
    # ========================================================

    print("\nExtracting links...")

    try:

        links = extract_links(
            url
        )

    except Exception as exc:

        logger.exception(
            "Could not extract links from %s: %s",
            url,
            exc,
        )

        print(
            f"Could not extract links: {exc}"
        )

        links = []

    print(
        f"Links found: {len(links)}"
    )

    # ========================================================
    # FIND RELEVANT LINKS
    # ========================================================

    relevant_links = find_relevant_links(
        links
    )

    print("\nRelevant links:")

    if relevant_links:

        for link in relevant_links:

            print(
                "-",
                link,
            )

    else:

        print(
            "- No relevant contact/guest-post pages found."
        )

    logger.info(
        "Relevant links found: %s | URL: %s",
        len(relevant_links),
        url,
    )

    # ========================================================
    # SCRAPE RELEVANT PAGES
    # ========================================================

    page_emails = {}

    if relevant_links:

        try:

            page_emails = scrape_relevant_pages(
                relevant_links
            )

        except Exception as exc:

            logger.exception(
                "Relevant page scraping failed for %s: %s",
                url,
                exc,
            )

            print(
                f"Relevant page scraping failed: {exc}"
            )

            page_emails = {}

    # ========================================================
    # COLLECT ALL EMAILS
    # ========================================================

    all_emails = []

    all_emails.extend(
        emails or []
    )

    for page_email_list in page_emails.values():

        if page_email_list:

            all_emails.extend(
                page_email_list
            )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    all_emails = sorted(
        set(
            email.strip().lower()
            for email in all_emails
            if email
        )
    )

    # ========================================================
    # VALIDATE + RANK CONTACT EMAILS
    # ========================================================

    try:

        best_contact_emails, excluded_emails = (
            get_best_contact_emails(
                all_emails,
                max_emails=MAX_CONTACT_EMAILS,
            )
        )

    except Exception as exc:

        logger.exception(
            "Email validation failed for %s: %s",
            url,
            exc,
        )

        print(
            f"Email validation failed: {exc}"
        )

        best_contact_emails = []
        excluded_emails = []

    # ========================================================
    # PRINT EMAIL RESULTS
    # ========================================================

    print(
        "\nValid / best contact emails:"
    )

    if best_contact_emails:

        for email in best_contact_emails:

            print(
                "-",
                email,
            )

    else:

        print(
            "- No valid contact emails found."
        )

    print(
        "\nExcluded emails:"
    )

    if excluded_emails:

        for email in excluded_emails:

            print(
                "-",
                email,
            )

    else:

        print(
            "- None"
        )

    logger.info(
        "Email validation completed: %s | "
        "Best contacts: %s | "
        "Excluded: %s",
        url,
        len(best_contact_emails),
        len(excluded_emails),
    )

    # ========================================================
    # PREPARE OUTREACH ACTION
    # ========================================================

    try:

        outreach_action = prepare_outreach_action(
            website_title=title,
            website_url=url,
            industry=industry,
            geography=geography,
            best_contact_emails=best_contact_emails,
            source_pages=relevant_links,
            discovered_links=links,
            website_text=website_text,
        )

    except Exception as exc:

        logger.exception(
            "Outreach preparation failed for %s: %s",
            url,
            exc,
        )

        print(
            f"Outreach preparation failed: {exc}"
        )

        outreach_action = {
            "action": "Manual Review",
            "status": "Required",
            "target": url,
            "details": {
                "channel": "Manual Review",
                "status": "Required",
                "message": (
                    "Outreach preparation failed. "
                    "Manual review is required."
                ),
            },
        }

    print(
        "\nOutreach action:"
    )

    print(
        f"- Action: {outreach_action.get('action')}"
    )

    print(
        f"- Status: {outreach_action.get('status')}"
    )

    print(
        f"- Target: {outreach_action.get('target')}"
    )

    # ========================================================
    # BUILD OPPORTUNITY
    # ========================================================



    opportunity = {
        "title": title,
        "url": url,
        "score": score,
        "industry_match": industry_match,
        "geography_match": geography_match,
        "potential": guest_post_potential,
        "analysis_method": analysis_method,
        "reason": reason,
        "emails": best_contact_emails,
        "excluded_emails": excluded_emails,
        "source_pages": relevant_links,
        "outreach": outreach_action,
    }

    print(
        "\nQualification: QUALIFIED"
    )

    logger.info(
        "Website qualified: %s | "
        "Score: %s | "
        "Best contacts: %s",
        url,
        score,
        len(best_contact_emails),
    )

    return opportunity


# ============================================================
# RUN CAMPAIGN
# ============================================================

def run_campaign(
    industry: str,
    geography: str,
    search_provider: Optional[Any] = None,
    relevance_checker: Callable[..., str] = check_website_relevance,
) -> List[Dict[str, Any]]:
    """
    Run the complete guest-post discovery campaign.
    """

    industry = industry.strip()
    geography = geography.strip()

    if not industry:
        raise ValueError(
            "Industry is required."
        )

    if not geography:
        raise ValueError(
            "Geography is required."
        )

    # ========================================================
    # CREATE SEARCH QUERY
    # ========================================================

    query = create_search_query(
        industry,
        geography,
    )

    print("\nSearch query:")
    print(query)

    logger.info(
        "Search started: %s",
        query,
    )

    # ========================================================
    # SEARCH PROVIDER
    # ========================================================

    provider = (
        search_provider
        if search_provider is not None
        else TavilySearchProvider()
    )

    # ========================================================
    # SEARCH
    # ========================================================

    print(
        "\nSearching the web..."
    )

    try:

        results = get_search_results(
            query,
            provider,
        )

    except Exception as exc:

        logger.exception(
            "Search failed: %s",
            exc,
        )

        print(
            f"\nSearch failed: {exc}"
        )

        return []

    print(
        f"\nFound {len(results)} results."
    )

    logger.info(
        "Search completed. Results found: %s",
        len(results),
    )

    # ========================================================
    # PROCESS RESULTS
    # ========================================================

    qualified_sites = []

    for result in results:

        try:

            opportunity = process_search_result(
                result,
                industry,
                geography,
                relevance_checker=relevance_checker,
            )

            if opportunity is not None:

                qualified_sites.append(
                    opportunity
                )

        except Exception as exc:

            url = result.get(
                "url",
                "unknown",
            )

            logger.exception(
                "Unexpected error while processing %s: %s",
                url,
                exc,
            )

            print(
                f"\nUnexpected error processing "
                f"{url}: {exc}"
            )

            # Continue with the next website.
            continue

    return qualified_sites


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    qualified_sites: Iterable[Dict[str, Any]],
    json_path: str = DEFAULT_JSON_PATH,
    csv_path: str = DEFAULT_CSV_PATH,
) -> None:
    """
    Save qualified opportunities to JSON and CSV.
    """

    sites = list(
        qualified_sites
    )

    json_file = Path(
        json_path
    )

    csv_file = Path(
        csv_path
    )

    # ========================================================
    # JSON
    # ========================================================

    json_file.write_text(
        json.dumps(
            sites,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # CSV
    # ========================================================

    fieldnames = [
    "title",
    "url",
    "score",
    "industry_match",
    "geography_match",
    "potential",
    "analysis_method",
    "reason",
    "emails",
    "excluded_emails",
    "source_pages",
    "outreach_action",
    "outreach_status",
    "outreach_target",
    "outreach_channel",
    "outreach_subject",
    "outreach_message",
]

    with csv_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for site in sites:

            writer.writerow(
                {
                    "title": site.get(
                        "title",
                        "",
                    ),
                    "url": site.get(
                        "url",
                        "",
                    ),
                    "score": site.get(
                        "score",
                        0,
                    ),
                    "industry_match": site.get(
                        "industry_match",
                        "",
                    ),
                    "geography_match": site.get(
                        "geography_match",
                        "",
                    ),
                    "potential": site.get(
                        "potential",
                        "",
                    ),
                    "analysis_method": site.get(
                        "analysis_method",
                        "",
                    ),
                    "reason": site.get(
                        "reason",
                        "",
                    ),
                    "emails": ", ".join(
                        site.get(
                            "emails",
                            [],
                        )
                    ),
                    "excluded_emails": ", ".join(
                        site.get(
                            "excluded_emails",
                            [],
                        )
                    ),
                    "source_pages": ", ".join(
                        site.get(
                            "source_pages",
                            [],
                        )
                    ),
                    "outreach_action": site.get(
    "outreach",
    {},
).get(
    "action",
    "",
),
"outreach_status": site.get(
    "outreach",
    {},
).get(
    "status",
    "",
),
"outreach_target": site.get(
    "outreach",
    {},
).get(
    "target",
    "",
),
"outreach_channel": site.get(
    "outreach",
    {},
).get(
    "details",
    {},
).get(
    "channel",
    "",
),
"outreach_subject": site.get(
    "outreach",
    {},
).get(
    "details",
    {},
).get(
    "subject",
    "",
),
"outreach_message": site.get(
    "outreach",
    {},
).get(
    "details",
    {},
).get(
    "body",
    site.get(
        "outreach",
        {},
    ).get(
        "details",
        {},
    ).get(
        "message",
        "",
    ),
),


                }
            )

    logger.info(
        "Results saved: JSON=%s | CSV=%s | Count=%s",
        json_path,
        csv_path,
        len(sites),
    )


# ============================================================
# PRINT FINAL RESULTS
# ============================================================

def print_final_results(
    qualified_sites: List[Dict[str, Any]],
) -> None:
    """
    Display the final qualified opportunities.
    """

    print(
        "\n"
        + "=" * 60
    )

    print(
        "QUALIFIED GUEST POST OPPORTUNITIES"
    )

    print(
        "=" * 60
    )

    if not qualified_sites:

        print(
            "\nNo qualified opportunities found."
        )

        return

    for index, site in enumerate(
        qualified_sites,
        start=1,
    ):

        print(
            f"\n[{index}] {site['title']}"
        )

        print(
            f"URL: {site['url']}"
        )

        print(
            f"Relevance Score: "
            f"{site['score']}"
        )

        print(
            f"Industry Match: "
            f"{site['industry_match']}"
        )

        print(
            f"Geography Match: "
            f"{site['geography_match']}"
        )

        print(
            f"Guest Post Potential: "
            f"{site['potential']}"
        )

        print(
            f"Analysis Method: "
            f"{site['analysis_method']}"
        )

        print(
            f"Reason: "
            f"{site['reason']}"
        )

        print(
            "Contact Emails:"
        )

        emails = site.get(
            "emails",
            [],
        )

        if emails:

            for email in emails:

                print(
                    f"- {email}"
                )

        else:

            print(
                "- No valid contact email found."
            )

        source_pages = site.get(
            "source_pages",
            [],
        )

        if source_pages:

            print(
                "Relevant Pages:"
            )

            for page in source_pages:

                print(
                    f"- {page}"
                )

    print(
        "\n"
        + "=" * 60
    )

    print(
        f"Total qualified opportunities: "
        f"{len(qualified_sites)}"
    )

    print(
        "=" * 60
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    CLI entry point.
    """

    print(
        "\n"
        + "=" * 60
    )

    print(
        "GuestPosts.biz AI Agent"
    )

    print(
        "Guest Post Discovery Pipeline"
    )

    print(
        "=" * 60
    )

    # ========================================================
    # INPUT
    # ========================================================

    industry = input(
        "\nEnter industry: "
    ).strip()

    geography = input(
        "Enter geography: "
    ).strip()

    if not industry:

        print(
            "\nError: Industry is required."
        )

        return

    if not geography:

        print(
            "\nError: Geography is required."
        )

        return

    # ========================================================
    # RUN CAMPAIGN
    # ========================================================

    try:

        qualified_sites = run_campaign(
            industry,
            geography,
        )

    except KeyboardInterrupt:

        print(
            "\n\nCampaign interrupted by user."
        )

        logger.info(
            "Campaign interrupted by user."
        )

        return

    except Exception as exc:

        print(
            f"\nCampaign failed: {exc}"
        )

        logger.exception(
            "Campaign failed: %s",
            exc,
        )

        return

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    print_final_results(
        qualified_sites
    )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    try:

        save_results(
            qualified_sites
        )

        print(
            "\nResults saved to results.json"
        )

        print(
            "Results saved to results.csv"
        )

    except Exception as exc:

        print(
            f"\nCould not save results: {exc}"
        )

        logger.exception(
            "Could not save results: %s",
            exc,
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

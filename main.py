import re
import json
import csv

from scraper import (
    scrape_website,
    extract_links,
    find_relevant_links,
    scrape_relevant_pages,
    validate_emails,
    get_website_text,
)

from search import (
    create_search_query,
    get_search_results,
    TavilySearchProvider,
)

from logger import logger
from relevance import check_website_relevance


# ============================================================
# PARSE RELEVANCE RESULT
# ============================================================

def parse_relevance_result(result):
    """
    Extracts:
        - relevance score
        - industry match
        - geography match
        - guest post potential
        - analysis method
        - reason
    """

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

    analysis_method = (
        method_match.group(1).capitalize()
        if method_match
        else "AI"
    )

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
    Determines whether the website is a qualified
    guest-post opportunity.

    The geography requirement is important because
    the campaign has a target geography.

    Heuristic results are treated more conservatively
    than AI results.
    """

    # --------------------------------------------------------
    # BASIC REQUIREMENTS
    # --------------------------------------------------------

    if industry_match != "High":
        return False

    if geography_match == "Low":
        return False

    if guest_post_potential != "High":
        return False

    # --------------------------------------------------------
    # SCORE REQUIREMENT
    # --------------------------------------------------------

    if analysis_method == "Heuristic":

        # Conservative fallback.
        return score >= 75

    if analysis_method == "Unavailable":

        return False

    # AI result
    return score >= 70


# ============================================================
# GET SEARCH PARAMETERS
# ============================================================

industry = input(
    "Enter industry: "
).strip()

geography = input(
    "Enter geography: "
).strip()


# ============================================================
# CREATE SEARCH QUERY
# ============================================================

query = create_search_query(
    industry,
    geography,
)

print("\nSearch query:")
print(query)

logger.info(
    f"Search started: {query}"
)


# ============================================================
# INITIALIZE SEARCH PROVIDER
# ============================================================

search_provider = TavilySearchProvider()


# ============================================================
# SEARCH THE WEB
# ============================================================

print("\nSearching the web...")

results = get_search_results(
    query,
    search_provider,
)

print(
    f"\nFound {len(results)} results."
)

logger.info(
    f"Search completed. Results found: {len(results)}"
)


# ============================================================
# STORE QUALIFIED WEBSITES
# ============================================================

qualified_sites = []


# ============================================================
# PROCESS SEARCH RESULTS
# ============================================================

for result in results:

    title = result.get(
        "title",
        "Untitled website",
    )

    url = result.get(
        "url",
        "",
    )

    print(
        "\n" + "=" * 60
    )

    print(
        f"Title: {title}"
    )

    print(
        f"URL: {url}"
    )

    print(
        "=" * 60
    )

    logger.info(
        f"Processing website: {url}"
    )

    # --------------------------------------------------------
    # GET WEBSITE CONTENT
    # --------------------------------------------------------

    print(
        "\nGetting website content..."
    )

    website_text = get_website_text(
        url
    )

    if not website_text:

        print(
            "Could not retrieve website content "
            "for AI analysis."
        )

        logger.info(
            f"Website content unavailable: {url}"
        )

        continue

    # --------------------------------------------------------
    # AI RELEVANCE ANALYSIS
    # --------------------------------------------------------

    print(
        "\nAI relevance analysis..."
    )

    relevance_result = check_website_relevance(
        title,
        url,
        industry,
        geography,
        website_text,
    )

    print(
        "\nAI Relevance Result:"
    )

    print(
        relevance_result
    )

    # --------------------------------------------------------
    # PARSE RESULT
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # QUALIFICATION
    # --------------------------------------------------------

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
            f"Website skipped: {url} | "
            f"Score: {score} | "
            f"Industry: {industry_match} | "
            f"Geography: {geography_match} | "
            f"Potential: {guest_post_potential} | "
            f"Method: {analysis_method}"
        )

        continue

    print(
        "\nWebsite passed relevance check."
    )

    # --------------------------------------------------------
    # SCRAPE WEBSITE EMAILS
    # --------------------------------------------------------

    print(
        "\nScraping website..."
    )

    emails = scrape_website(
        url
    )

    print(
        "\nEmails found:",
        emails
    )

    # --------------------------------------------------------
    # EXTRACT LINKS
    # --------------------------------------------------------

    print(
        "\nExtracting links..."
    )

    try:

        links = extract_links(
            url
        )

    except Exception as e:

        print(
            f"Could not extract links: {e}"
        )

        links = []

    print(
        f"Links found: {len(links)}"
    )

    # --------------------------------------------------------
    # FIND RELEVANT LINKS
    # --------------------------------------------------------

    relevant_links = find_relevant_links(
        links
    )

    print(
        "\nRelevant links:"
    )

    for link in relevant_links:

        print(
            "-",
            link
        )

    logger.info(
        f"Relevant links found: "
        f"{len(relevant_links)}"
    )

    # --------------------------------------------------------
    # SCRAPE RELEVANT PAGES
    # --------------------------------------------------------

    page_emails = scrape_relevant_pages(
        relevant_links
    )

    # --------------------------------------------------------
    # COLLECT ALL EMAILS
    # --------------------------------------------------------

    all_emails = []

    all_emails.extend(
        emails
    )

    for page_email_list in page_emails.values():

        all_emails.extend(
            page_email_list
        )

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    all_emails = list(
        set(all_emails)
    )

    # --------------------------------------------------------
    # VALIDATE EMAILS
    # --------------------------------------------------------

    valid_emails, excluded_emails = validate_emails(
        all_emails
    )

    print(
        "\nValid contact emails:"
    )

    for email in valid_emails:

        print(
            "-",
            email
        )

    print(
        "\nExcluded emails:"
    )

    for email in excluded_emails:

        print(
            "-",
            email
        )

    logger.info(
        f"Email validation completed: "
        f"{url} | "
        f"Valid: {len(valid_emails)} | "
        f"Excluded: {len(excluded_emails)}"
    )

    # --------------------------------------------------------
    # SAVE QUALIFIED SITE
    # --------------------------------------------------------

    qualified_sites.append(
        {
            "title": title,
            "url": url,
            "score": score,
            "industry_match": industry_match,
            "geography_match": geography_match,
            "potential": guest_post_potential,
            "analysis_method": analysis_method,
            "reason": reason,
            "emails": valid_emails,
        }
    )

    print(
        "\nQualification: QUALIFIED"
    )

    logger.info(
        f"Website qualification: {url} | "
        f"Status: QUALIFIED | "
        f"Score: {score} | "
        f"Industry: {industry_match} | "
        f"Geography: {geography_match} | "
        f"Potential: {guest_post_potential}"
    )


# ============================================================
# FINAL QUALIFIED OPPORTUNITIES
# ============================================================

print("\n")

print(
    "=" * 60
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

else:

    for site in qualified_sites:

        print(
            "\nWebsite:",
            site["title"]
        )

        print(
            "URL:",
            site["url"]
        )

        print(
            "Relevance Score:",
            site["score"]
        )

        print(
            "Industry Match:",
            site["industry_match"]
        )

        print(
            "Geography Match:",
            site["geography_match"]
        )

        print(
            "Guest Post Potential:",
            site["potential"]
        )

        print(
            "Analysis Method:",
            site["analysis_method"]
        )

        print(
            "Reason:",
            site["reason"]
        )

        print(
            "Contact Emails:"
        )

        if site["emails"]:

            for email in site["emails"]:

                print(
                    "-",
                    email
                )

        else:

            print(
                "- No valid contact email found"
            )


# ============================================================
# SUMMARY
# ============================================================

print("\n")

print(
    "=" * 60
)

print(
    f"Total qualified opportunities: "
    f"{len(qualified_sites)}"
)

print(
    "=" * 60
)


# ============================================================
# SAVE JSON
# ============================================================

with open(
    "results.json",
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        qualified_sites,
        file,
        indent=4,
        ensure_ascii=False,
    )

print(
    "\nResults saved to results.json"
)


# ============================================================
# SAVE CSV
# ============================================================

with open(
    "results.csv",
    "w",
    newline="",
    encoding="utf-8",
) as file:

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
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames,
    )

    writer.writeheader()

    for site in qualified_sites:

        writer.writerow(
            {
                "title": site["title"],
                "url": site["url"],
                "score": site["score"],
                "industry_match": site[
                    "industry_match"
                ],
                "geography_match": site[
                    "geography_match"
                ],
                "potential": site[
                    "potential"
                ],
                "analysis_method": site[
                    "analysis_method"
                ],
                "reason": site["reason"],
                "emails": ", ".join(
                    site["emails"]
                ),
            }
        )

print(
    "Results saved to results.csv"
)
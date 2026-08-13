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
    get_best_contact_emails
)

from search import (
    create_search_query,
    get_search_results,
    TavilySearchProvider
)

from logger import logger
from relevance import check_website_relevance


def parse_relevance_result(result):
    """
    Extracts relevance score, industry match,
    guest post potential, and reason from AI response.
    """

    score_match = re.search(
        r"Relevance score:\s*(\d+)",
        result,
        re.IGNORECASE
    )

    industry_match = re.search(
        r"Industry match:\s*(High|Medium|Low)",
        result,
        re.IGNORECASE
    )

    potential_match = re.search(
        r"Guest post potential:\s*(High|Medium|Low|Medium-High|High-Medium)",
        result,
        re.IGNORECASE
    )

    reason_match = re.search(
        r"Reason:\s*(.+)",
        result,
        re.IGNORECASE
    )

    score = (
        int(score_match.group(1))
        if score_match
        else 0
    )

    industry_match_value = (
        industry_match.group(1).capitalize()
        if industry_match
        else "Low"
    )

    if potential_match:

        potential = potential_match.group(1).lower()

        if potential in ["medium-high", "high-medium"]:
            potential = "High"
        else:
            potential = potential.capitalize()

    else:
        potential = "Low"

    reason = (
        reason_match.group(1).strip()
        if reason_match
        else "No reason provided."
    )

    return (
        score,
        industry_match_value,
        potential,
        reason
    )


# ============================================================
# GET SEARCH PARAMETERS
# ============================================================

industry = input("Enter industry: ")
geography = input("Enter geography: ")


# ============================================================
# CREATE SEARCH QUERY
# ============================================================

query = create_search_query(
    industry,
    geography
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
    search_provider
)

print(f"\nFound {len(results)} results.")

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

    title = result["title"]
    url = result["url"]

    print("\n" + "=" * 60)
    print(f"Title: {title}")
    print(f"URL: {url}")
    print("=" * 60)

    logger.info(
        f"Processing website: {url}"
    )


    # ========================================================
    # GET WEBSITE TEXT
    # ========================================================

    print("\nGetting website content...")

    website_text = get_website_text(url)

    if not website_text:

        print(
            "Could not retrieve website content "
            "for AI analysis."
        )

        logger.info(
            f"AI relevance skipped: {url}"
        )

        continue


    # ========================================================
    # AI RELEVANCE CHECK
    # ========================================================

    print("\nAI relevance analysis...")

    relevance_result = check_website_relevance(
        title,
        url,
        industry,
        geography,
        website_text
    )

    print("\nAI Relevance Result:")
    print(relevance_result)


    # ========================================================
    # PARSE AI RESULT
    # ========================================================

    (
        score,
        industry_match,
        guest_post_potential,
        reason
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
        f"Parsed guest post potential: "
        f"{guest_post_potential}"
    )

    print(
        f"Parsed reason: "
        f"{reason}"
    )


    # ========================================================
    # QUALIFICATION CHECK
    # ========================================================

    if (
        score < 70
        or guest_post_potential not in ("High", "Medium")
    ):

        print(
            "\nSkipping website - "
            "not a qualified guest post opportunity."
        )

        logger.info(
            f"Website skipped: {url} | "
            f"Score: {score} | "
            f"Potential: {guest_post_potential}"
        )

        continue


    print(
        "\nWebsite passed AI relevance check."
    )


    # ========================================================
    # SCRAPE WEBSITE
    # ========================================================

    print("\nScraping website...")

    emails = scrape_website(url)

    print(
        "\nEmails found:",
        emails
    )


    # ========================================================
    # EXTRACT LINKS
    # ========================================================

    print("\nExtracting links...")

    links = extract_links(url)

    print(
        f"Links found: {len(links)}"
    )

    logger.info(
        f"Links extracted: {url} | "
        f"Links found: {len(links)}"
    )


    # ========================================================
    # FIND RELEVANT LINKS
    # ========================================================

    relevant_links = find_relevant_links(
        links
    )

    print("\nRelevant links:")

    for link in relevant_links:
        print("-", link)

    logger.info(
        f"Relevant links found: "
        f"{len(relevant_links)}"
    )


    # ========================================================
    # SCRAPE RELEVANT PAGES
    # ========================================================

    page_emails = scrape_relevant_pages(
        relevant_links
    )


    # ========================================================
    # COLLECT ALL EMAILS
    # ========================================================

    all_page_emails = []

    for page_email_list in page_emails.values():

        all_page_emails.extend(
            page_email_list
        )


    # Include homepage emails

    all_page_emails.extend(
        emails
    )


    # Remove duplicates

    all_page_emails = list(
        set(all_page_emails)
    )


    # ========================================================
    # VALIDATE EMAILS
    # ========================================================

    valid_emails, excluded_emails = get_best_contact_emails(
    all_page_emails,
    max_emails=5
)


    # ========================================================
    # DISPLAY EMAILS
    # ========================================================

    print("\nValid contact emails:")

    for email in valid_emails:
        print("-", email)


    print("\nExcluded emails:")

    for email in excluded_emails:
        print("-", email)


    logger.info(
        f"Email validation completed: {url} | "
        f"Valid: {len(valid_emails)} | "
        f"Excluded: {len(excluded_emails)}"
    )


    # ========================================================
    # STORE QUALIFIED WEBSITE
    # ========================================================

    qualified_sites.append({

        "title": title,

        "url": url,

        "score": score,

        "industry_match": industry_match,

        "potential": guest_post_potential,

        "reason": reason,

        "emails": valid_emails

    })


    print(
        "\nQualification: QUALIFIED"
    )

    logger.info(
        f"Website qualified: {url} | "
        f"Score: {score} | "
        f"Potential: {guest_post_potential}"
    )


# ============================================================
# FINAL QUALIFIED OPPORTUNITIES
# ============================================================

print("\n")
print("=" * 60)
print("QUALIFIED GUEST POST OPPORTUNITIES")
print("=" * 60)


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
            "Guest Post Potential:",
            site["potential"]
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
                print("-", email)

        else:

            print(
                "- No valid contact email found"
            )


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 60)

print(
    f"Total qualified opportunities: "
    f"{len(qualified_sites)}"
)

print("=" * 60)


# ============================================================
# SAVE JSON
# ============================================================

with open(
    "results.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        qualified_sites,
        file,
        indent=4,
        ensure_ascii=False
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
    encoding="utf-8"
) as file:

    fieldnames = [
        "title",
        "url",
        "score",
        "industry_match",
        "potential",
        "reason",
        "emails"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for site in qualified_sites:

        writer.writerow({

            "title": site["title"],

            "url": site["url"],

            "score": site["score"],

            "industry_match":
                site["industry_match"],

            "potential":
                site["potential"],

            "reason":
                site["reason"],

            "emails":
                ", ".join(site["emails"])

        })


print(
    "Results saved to results.csv"
)
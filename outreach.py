import re
from urllib.parse import urlparse


PHONE_REGEX = re.compile(
    r"(?:\+?\d[\d\s().-]{7,}\d)",
    re.IGNORECASE,
)


def build_email_draft(
    recipient_email,
    website_title,
    industry,
    geography,
):
    """
    Prepare an email outreach draft.

    Dry-run only:
    This function does NOT send email.
    """

    subject = (
        f"Guest Post Opportunity – "
        f"{industry.title()} Content for {website_title}"
    )

    body = f"""Hello,

I came across {website_title} while researching {industry} websites
relevant to the {geography} market.

We would be interested in contributing a high-quality,
original guest post related to {industry}.

The article would be written specifically for your audience
and would provide useful, relevant content.

Please let me know if you are currently accepting guest
post contributions and what your submission requirements are.

Best regards
"""

    return {
        "channel": "Email",
        "status": "Prepared",
        "recipient": recipient_email,
        "subject": subject,
        "body": body,
    }


def find_whatsapp_links(links):
    """
    Find WhatsApp links from discovered website links.
    """

    whatsapp_links = []

    for link in links:
        link_lower = link.lower()

        if (
            "wa.me/" in link_lower
            or "whatsapp.com/" in link_lower
            or "api.whatsapp.com/" in link_lower
        ):
            whatsapp_links.append(link)

    return list(dict.fromkeys(whatsapp_links))


def extract_phone_numbers(text):
    """
    Extract possible phone numbers from website text.
    """

    if not text:
        return []

    matches = PHONE_REGEX.findall(text)

    cleaned = []

    for number in matches:
        number = re.sub(r"\s+", " ", number).strip()

        if number not in cleaned:
            cleaned.append(number)

    return cleaned[:5]


def build_whatsapp_draft(
    whatsapp_target,
    website_title,
    industry,
    geography,
):
    """
    Prepare a WhatsApp outreach draft.

    Dry-run only:
    This function does NOT send WhatsApp messages.
    """

    message = f"""Hello,

I came across {website_title} while researching
{industry} websites relevant to the {geography} market.

We are interested in contributing a relevant guest post
to your website.

Could you please let me know if you currently accept
guest post submissions and what your requirements are?

Thank you.
"""

    return {
        "channel": "WhatsApp",
        "status": "Prepared",
        "recipient": whatsapp_target,
        "message": message,
    }


def find_contact_form(source_pages):
    """
    Identify likely contact/submission pages.
    """

    for page in source_pages:
        page_lower = page.lower()

        if any(
            keyword in page_lower
            for keyword in [
                "contact",
                "contact-us",
                "contactus",
                "write-for-us",
                "guest-post",
                "submission",
                "contribute",
            ]
        ):
            return page

    return None


def build_contact_form_action(form_url):
    """
    Prepare a contact-form action.

    Dry-run only:
    This function does NOT submit the form.
    """

    return {
        "channel": "Contact Form",
        "status": "Prepared",
        "url": form_url,
        "message": (
            "Guest post outreach message prepared "
            "for manual/form submission."
        ),
    }


def prepare_outreach_action(
    website_title,
    website_url,
    industry,
    geography,
    best_contact_emails,
    source_pages,
    discovered_links=None,
    website_text="",
):
    """
    Decide the next outreach action.

    Priority:
        1. Email
        2. WhatsApp
        3. Contact form

    This function is intentionally dry-run only.
    """

    discovered_links = discovered_links or []

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    if best_contact_emails:

        email = best_contact_emails[0]

        return {
            "action": "Email",
            "status": "Prepared",
            "target": email,
            "details": build_email_draft(
                email,
                website_title,
                industry,
                geography,
            ),
        }

    # --------------------------------------------------------
    # WHATSAPP LINK
    # --------------------------------------------------------

    whatsapp_links = find_whatsapp_links(
        discovered_links
    )

    if whatsapp_links:

        target = whatsapp_links[0]

        return {
            "action": "WhatsApp",
            "status": "Prepared",
            "target": target,
            "details": build_whatsapp_draft(
                target,
                website_title,
                industry,
                geography,
            ),
        }

    # --------------------------------------------------------
    # PHONE NUMBER
    # --------------------------------------------------------

    phone_numbers = extract_phone_numbers(
        website_text
    )

    if phone_numbers:

        target = phone_numbers[0]

        return {
            "action": "WhatsApp",
            "status": "Prepared",
            "target": target,
            "details": build_whatsapp_draft(
                target,
                website_title,
                industry,
                geography,
            ),
        }

    # --------------------------------------------------------
    # CONTACT FORM
    # --------------------------------------------------------

    form_url = find_contact_form(
        source_pages
    )

    if form_url:

        return {
            "action": "Contact Form",
            "status": "Prepared",
            "target": form_url,
            "details": build_contact_form_action(
                form_url
            ),
        }

    # --------------------------------------------------------
    # NOTHING FOUND
    # --------------------------------------------------------

    return {
        "action": "Manual Review",
        "status": "Required",
        "target": website_url,
        "details": {
            "channel": "Manual Review",
            "status": "Required",
            "message": (
                "No usable email, WhatsApp contact, "
                "or contact form was detected."
            ),
        },
    }
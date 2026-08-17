from outreach import (
    build_email_draft,
    build_whatsapp_draft,
    extract_phone_numbers,
    find_contact_form,
    find_whatsapp_links,
    prepare_outreach_action,
)


def test_build_email_draft():
    result = build_email_draft(
        "info@example.com",
        "Example Sports",
        "sports",
        "UAE",
    )

    assert result["channel"] == "Email"
    assert result["status"] == "Prepared"
    assert result["recipient"] == "info@example.com"
    assert "sports" in result["subject"].lower()
    assert "UAE" in result["body"]
    assert "guest post" in result["body"].lower()


def test_find_whatsapp_links():
    links = [
        "https://example.com/about",
        "https://wa.me/971501234567",
        "https://example.com/contact",
        "https://api.whatsapp.com/send?phone=971501234567",
        "https://wa.me/971501234567",
    ]

    result = find_whatsapp_links(links)

    assert len(result) == 2
    assert "https://wa.me/971501234567" in result
    assert (
        "https://api.whatsapp.com/send?phone=971501234567"
        in result
    )


def test_extract_phone_numbers():
    text = """
    Contact us:
    +971 50 123 4567
    +971-4-123-4567
    """

    result = extract_phone_numbers(text)

    assert "+971 50 123 4567" in result
    assert "+971-4-123-4567" in result


def test_find_contact_form():
    pages = [
        "https://example.com/about",
        "https://example.com/blog",
        "https://example.com/write-for-us",
    ]

    result = find_contact_form(pages)

    assert result == "https://example.com/write-for-us"


def test_prepare_outreach_prefers_email():
    result = prepare_outreach_action(
        website_title="Example Sports",
        website_url="https://example.com",
        industry="sports",
        geography="UAE",
        best_contact_emails=["info@example.com"],
        source_pages=[],
        discovered_links=[
            "https://wa.me/971501234567",
        ],
        website_text="+971 50 123 4567",
    )

    assert result["action"] == "Email"
    assert result["status"] == "Prepared"
    assert result["target"] == "info@example.com"


def test_prepare_outreach_uses_whatsapp_when_no_email():
    result = prepare_outreach_action(
        website_title="Example Sports",
        website_url="https://example.com",
        industry="sports",
        geography="UAE",
        best_contact_emails=[],
        source_pages=[],
        discovered_links=[
            "https://wa.me/971501234567",
        ],
        website_text="",
    )

    assert result["action"] == "WhatsApp"
    assert result["status"] == "Prepared"
    assert result["target"] == "https://wa.me/971501234567"


def test_prepare_outreach_uses_phone_when_no_email_or_whatsapp():
    result = prepare_outreach_action(
        website_title="Example Sports",
        website_url="https://example.com",
        industry="sports",
        geography="UAE",
        best_contact_emails=[],
        source_pages=[],
        discovered_links=[],
        website_text="Call us at +971 50 123 4567",
    )

    assert result["action"] == "WhatsApp"
    assert result["status"] == "Prepared"
    assert result["target"] == "+971 50 123 4567"


def test_prepare_outreach_uses_contact_form_as_last_option():
    result = prepare_outreach_action(
        website_title="Example Sports",
        website_url="https://example.com",
        industry="sports",
        geography="UAE",
        best_contact_emails=[],
        source_pages=[
            "https://example.com/about",
            "https://example.com/contact-us",
        ],
        discovered_links=[],
        website_text="",
    )

    assert result["action"] == "Contact Form"
    assert result["status"] == "Prepared"
    assert result["target"] == "https://example.com/contact-us"


def test_prepare_outreach_returns_manual_review_when_nothing_found():
    result = prepare_outreach_action(
        website_title="Example Sports",
        website_url="https://example.com",
        industry="sports",
        geography="UAE",
        best_contact_emails=[],
        source_pages=[
            "https://example.com/about",
        ],
        discovered_links=[],
        website_text="",
    )

    assert result["action"] == "Manual Review"
    assert result["status"] == "Required"
    assert result["target"] == "https://example.com"

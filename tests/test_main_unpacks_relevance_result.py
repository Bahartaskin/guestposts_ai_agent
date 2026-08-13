from pathlib import Path


def test_main_unpacks_all_relevance_fields():
    source = Path(__file__).resolve().parents[1] / "main.py"
    content = source.read_text()

    assert "industry_match" in content
    assert "guest_post_potential" in content
    assert "reason" in content
    assert "parse_relevance_result(" in content
    assert "score, guest_post_potential = parse_relevance_result(" not in content

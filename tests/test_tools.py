"""Tests for the three FitFindr tools.

Tool 1 covers the verification checks from its planning.md spec: null brands,
L vs XL size matching, empty results, plus price filtering, relevance
ordering, and One Size handling.

Tool 2 mocks the Groq client so tests are deterministic and keyless. Covers
both prompt branches (wardrobe vs empty wardrobe), the null notes and null
brand guards, the optional style_profile and trends sections, and the failure
contract (empty LLM response raises, Groq errors propagate).
"""
from types import SimpleNamespace

import pytest

import tools
from tools import (
    check_trends,
    compare_prices,
    create_fit_card,
    save_style_preference,
    search_listings,
    suggest_outfit,
)
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe, load_listings


# ── keyword scoring ───────────────────────────────────────────────────────────

def test_basic_search_returns_relevant_results():
    results = search_listings("vintage flannel")
    assert len(results) > 0
    # Best match first. The oversized flannel (lst_003) hits both query words.
    assert results[0]["id"] == "lst_003"


def test_results_sorted_by_score_descending():
    results = search_listings("vintage denim jacket")
    ids = {r["id"] for r in results}
    assert len(ids) == len(results)  # no duplicates
    # Recompute each result's score and confirm the ordering is non-increasing.
    query = {"vintage", "denim", "jacket"}
    def score(listing):
        parts = [listing["title"], listing["description"],
                 " ".join(listing["style_tags"]), " ".join(listing["colors"]),
                 listing["category"]]
        if listing["brand"] is not None:
            parts.append(listing["brand"])
        haystack = " ".join(parts).lower()
        return sum(1 for w in query if w in haystack.split() or w in haystack)
    scores = [score(r) for r in results]
    assert scores == sorted(scores, reverse=True)


def test_zero_score_listings_dropped():
    results = search_listings("vintage")
    for r in results:
        haystack = " ".join([
            r["title"], r["description"], " ".join(r["style_tags"]),
            " ".join(r["colors"]), r["category"], r["brand"] or "",
        ]).lower()
        assert "vintage" in haystack


def test_no_matches_returns_empty_list():
    assert search_listings("submarine periscope") == []


# ── null brand handling ───────────────────────────────────────────────────────

def test_null_brand_listings_do_not_crash_and_still_match():
    # lst_002 has brand: null but matches on title/tags.
    results = search_listings("y2k butterfly baby tee")
    assert any(r["id"] == "lst_002" for r in results)


def test_brand_is_searchable_when_present():
    results = search_listings("levi's")
    assert len(results) > 0
    assert all(r["brand"] == "Levi's" for r in results)


# ── size matching ─────────────────────────────────────────────────────────────

def test_size_l_does_not_match_xl():
    results = search_listings("vintage", size="L")
    sizes = {r["size"] for r in results}
    assert "XL" not in sizes
    assert "XL (oversized)" not in sizes
    assert "XL (fits oversized)" not in sizes


def test_size_l_matches_combo_sizes():
    # "L" should match "L/XL" and "M/L" via token splitting.
    results = search_listings("vintage", size="L")
    sizes = {r["size"] for r in results}
    assert sizes <= {"L", "L/XL", "M/L", "One Size",
                     "One Size (adjustable)", "One Size / Oversized"}


def test_size_m_matches_s_slash_m():
    results = search_listings("y2k butterfly baby tee", size="M")
    assert any(r["id"] == "lst_002" for r in results)  # size "S/M"


def test_size_match_is_case_insensitive():
    lower = search_listings("vintage", size="l")
    upper = search_listings("vintage", size="L")
    assert [r["id"] for r in lower] == [r["id"] for r in upper]


def test_one_size_matches_any_requested_size():
    # lst_034 bucket hat is "One Size".
    results = search_listings("bucket hat plaid", size="XS")
    assert any(r["id"] == "lst_034" for r in results)


def test_shoe_and_waist_sizes_match_as_strings():
    shoes = search_listings("sneakers shoes", size="US 8")
    assert all("8" in r["size"] for r in shoes)
    jeans = search_listings("levi's jeans", size="W30")
    assert any(r["id"] == "lst_001" for r in jeans)  # size "W30 L30"


# ── price filtering ───────────────────────────────────────────────────────────

def test_max_price_is_inclusive_ceiling():
    results = search_listings("vintage", max_price=25.0)
    assert len(results) > 0
    assert all(r["price"] <= 25.0 for r in results)


def test_max_price_below_minimum_returns_empty():
    # Cheapest listing is $12.00.
    assert search_listings("vintage", max_price=5.0) == []


def test_combined_filters():
    results = search_listings("vintage", size="M", max_price=30.0)
    for r in results:
        assert r["price"] <= 30.0


# ── return shape ──────────────────────────────────────────────────────────────

def test_result_dicts_have_all_spec_fields():
    results = search_listings("vintage")
    expected = {"id", "title", "description", "category", "style_tags",
                "size", "condition", "price", "colors", "brand", "platform"}
    assert expected <= set(results[0].keys())


# ══ Tool 2: suggest_outfit ════════════════════════════════════════════════════

class FakeGroqClient:
    """Stands in for the Groq client. Records the create() call, returns a
    canned reply, or raises when given an exception."""

    def __init__(self, reply="Pair it with the baggy jeans and chunky sneakers.",
                 error=None):
        self.last_kwargs = None
        outer = self

        def create(**kwargs):
            outer.last_kwargs = kwargs
            if error is not None:
                raise error
            message = SimpleNamespace(content=reply)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

    @property
    def prompt(self):
        return self.last_kwargs["messages"][-1]["content"]


@pytest.fixture
def fake_groq(monkeypatch):
    client = FakeGroqClient()
    monkeypatch.setattr(tools, "_get_groq_client", lambda: client)
    return client


def _listing(listing_id):
    return next(l for l in load_listings() if l["id"] == listing_id)


def test_wardrobe_branch_returns_reply_and_names_pieces(fake_groq):
    result = suggest_outfit(_listing("lst_002"), get_example_wardrobe())
    assert result == "Pair it with the baggy jeans and chunky sneakers."
    # Every wardrobe item is named in the prompt so the LLM can reference it.
    for item in get_example_wardrobe()["items"]:
        assert item["name"] in fake_groq.prompt
    assert "1-2 complete outfits" in fake_groq.prompt


def test_empty_wardrobe_switches_to_general_advice_prompt(fake_groq):
    result = suggest_outfit(_listing("lst_002"), get_empty_wardrobe())
    assert isinstance(result, str) and result  # no exception, non-empty
    assert "general" in fake_groq.prompt.lower()
    assert "wardrobe:" not in fake_groq.prompt.lower()


def test_null_notes_skipped_in_wardrobe_prompt(fake_groq):
    # 5 of 10 example wardrobe items have notes: null. None of them may
    # render as the string "None".
    suggest_outfit(_listing("lst_002"), get_example_wardrobe())
    assert "None" not in fake_groq.prompt


def test_null_brand_skipped_in_item_prompt(fake_groq):
    suggest_outfit(_listing("lst_002"), get_example_wardrobe())  # brand: null
    assert "Brand:" not in fake_groq.prompt


def test_brand_included_when_present(fake_groq):
    suggest_outfit(_listing("lst_001"), get_example_wardrobe())  # Levi's
    assert "Brand: Levi's" in fake_groq.prompt


def test_style_profile_included_when_given(fake_groq):
    suggest_outfit(_listing("lst_002"), get_example_wardrobe(),
                   style_profile=["streetwear", "earth tones"])
    assert "streetwear, earth tones" in fake_groq.prompt


def test_optional_sections_omitted_when_absent(fake_groq):
    suggest_outfit(_listing("lst_002"), get_example_wardrobe())
    assert "preferences" not in fake_groq.prompt.lower()
    assert "trend" not in fake_groq.prompt.lower()


def test_trends_included_when_given(fake_groq):
    trends = [{"tag": "y2k", "mentions": 120}]
    suggest_outfit(_listing("lst_002"), get_example_wardrobe(), trends=trends)
    assert '"y2k"' in fake_groq.prompt


def test_empty_llm_response_raises_runtime_error(monkeypatch):
    client = FakeGroqClient(reply="   ")
    monkeypatch.setattr(tools, "_get_groq_client", lambda: client)
    with pytest.raises(RuntimeError, match="Y2K Baby Tee"):
        suggest_outfit(_listing("lst_002"), get_example_wardrobe())


def test_groq_error_propagates_to_caller(monkeypatch):
    client = FakeGroqClient(error=ConnectionError("rate limited"))
    monkeypatch.setattr(tools, "_get_groq_client", lambda: client)
    with pytest.raises(ConnectionError):
        suggest_outfit(_listing("lst_002"), get_example_wardrobe())


def test_uses_specced_model(fake_groq):
    suggest_outfit(_listing("lst_002"), get_example_wardrobe())
    assert fake_groq.last_kwargs["model"] == "llama-3.3-70b-versatile"


# ══ Tool 3: create_fit_card ═══════════════════════════════════════════════════

OUTFIT = "Pair the baby tee with the baggy jeans and chunky white sneakers."


def test_empty_outfit_returns_error_string_not_exception(fake_groq):
    result = create_fit_card("", _listing("lst_002"))
    assert isinstance(result, str)
    # Specific and actionable: names the item and says what to do next.
    assert "Y2K Baby Tee" in result
    assert "suggest_outfit" in result
    # The guard short-circuits before any LLM call.
    assert fake_groq.last_kwargs is None


def test_whitespace_outfit_returns_error_string(fake_groq):
    result = create_fit_card("   \n  ", _listing("lst_002"))
    assert "Y2K Baby Tee" in result
    assert fake_groq.last_kwargs is None


def test_none_outfit_returns_error_string(fake_groq):
    result = create_fit_card(None, _listing("lst_002"))
    assert "Y2K Baby Tee" in result
    assert fake_groq.last_kwargs is None


def test_happy_path_returns_caption_and_prompts_with_required_fields(fake_groq):
    result = create_fit_card(OUTFIT, _listing("lst_002"))
    assert result == "Pair it with the baggy jeans and chunky sneakers."
    # The prompt carries the item, the outfit, and the three required
    # mentions (name, price, platform).
    assert "Y2K Baby Tee" in fake_groq.prompt
    assert OUTFIT in fake_groq.prompt
    assert "$18.00" in fake_groq.prompt
    assert "depop" in fake_groq.prompt


def test_uses_higher_temperature_for_variation(fake_groq):
    create_fit_card(OUTFIT, _listing("lst_002"))
    suggest_temp = 0.7  # suggest_outfit's setting
    assert fake_groq.last_kwargs["temperature"] > suggest_temp


def test_fit_card_empty_llm_response_raises_runtime_error(monkeypatch):
    client = FakeGroqClient(reply="")
    monkeypatch.setattr(tools, "_get_groq_client", lambda: client)
    with pytest.raises(RuntimeError, match="Y2K Baby Tee"):
        create_fit_card(OUTFIT, _listing("lst_002"))


def test_fit_card_groq_error_propagates(monkeypatch):
    client = FakeGroqClient(error=ConnectionError("rate limited"))
    monkeypatch.setattr(tools, "_get_groq_client", lambda: client)
    with pytest.raises(ConnectionError):
        create_fit_card(OUTFIT, _listing("lst_002"))


def test_fit_card_uses_specced_model(fake_groq):
    create_fit_card(OUTFIT, _listing("lst_002"))
    assert fake_groq.last_kwargs["model"] == "llama-3.3-70b-versatile"


# ══ Tool 4: compare_prices (stretch: Price Comparison) ════════════════════════

def test_compare_prices_returns_full_verdict_dict():
    result = compare_prices(_listing("lst_001"))  # Levi's, bottoms
    assert result["verdict"] in {"below market", "fair", "above market"}
    assert result["item_price"] == 38.00
    assert result["comparable_count"] >= 3
    assert result["comp_min"] <= result["comp_median"] <= result["comp_max"]
    assert "$38.00" in result["reasoning"]
    assert f"${result['comp_median']:.2f}" in result["reasoning"]


def test_compare_prices_excludes_item_from_own_comparables():
    # 10 bottoms exist. With lst_001 excluded, comparables can never be 10.
    result = compare_prices(_listing("lst_001"))
    assert result["comparable_count"] <= 9


def test_compare_prices_verdict_band_below_and_above():
    base = _listing("lst_001")
    cheap = {**base, "id": "test_cheap", "price": 1.00}
    pricey = {**base, "id": "test_pricey", "price": 500.00}
    assert compare_prices(cheap)["verdict"] == "below market"
    assert compare_prices(pricey)["verdict"] == "above market"


def test_compare_prices_falls_back_to_category_on_rare_tags():
    base = _listing("lst_001")
    odd = {**base, "id": "test_odd", "style_tags": ["no-such-tag"]}
    result = compare_prices(odd)
    # No shared tags, so the whole bottoms category becomes the pool.
    assert result["comparable_count"] >= 3
    assert "bottoms" in result["reasoning"]


def test_compare_prices_not_enough_data_for_accessories():
    # Only 3 accessories exist. Excluding the item leaves 2, below the
    # minimum even after the category fallback.
    accessory = next(
        l for l in load_listings() if l["category"] == "accessories"
    )
    result = compare_prices(accessory)
    assert result["verdict"] == "not enough data"
    assert result["comparable_count"] == 2
    assert result["comp_min"] is None
    assert result["comp_median"] is None
    assert result["comp_max"] is None
    assert accessory["title"] in result["reasoning"]


# ══ Tool 5: check_trends (stretch: Trend Awareness) ═══════════════════════════

def test_check_trends_returns_top5_sorted_by_mentions():
    trends = check_trends()
    assert len(trends) == 5
    mentions = [t["mentions"] for t in trends]
    assert mentions == sorted(mentions, reverse=True)
    assert {"tag", "mentions", "momentum", "in_stock"} <= set(trends[0])


def test_check_trends_in_stock_zero_when_size_is_none():
    assert all(t["in_stock"] == 0 for t in check_trends())


def test_check_trends_category_filter_drops_absent_tags():
    # "ballet flats" and "coastal grandmother" appear in trends.json but on
    # no listing, so any category filter drops them.
    tags = {t["tag"] for t in check_trends(category="tops")}
    assert "ballet flats" not in tags
    assert "coastal grandmother" not in tags
    assert "y2k" in tags  # lst_002 is a y2k top


def test_check_trends_unknown_category_returns_empty_list():
    assert check_trends(category="swimwear") == []


def test_check_trends_size_counts_in_stock():
    trends = check_trends(category="tops", size="M")
    y2k = next(t for t in trends if t["tag"] == "y2k")
    expected = sum(
        1 for l in load_listings()
        if l["category"] == "tops" and "y2k" in l["style_tags"]
        and tools._size_matches("M", l["size"])
    )
    assert y2k["in_stock"] == expected > 0


def test_check_trends_missing_file_returns_empty_list(monkeypatch):
    monkeypatch.setattr(tools, "_TRENDS_PATH", "/nonexistent/trends.json")
    assert check_trends() == []


def test_check_trends_corrupt_file_returns_empty_list(monkeypatch, tmp_path):
    bad = tmp_path / "trends.json"
    bad.write_text("{not json")
    monkeypatch.setattr(tools, "_TRENDS_PATH", str(bad))
    assert check_trends() == []


# ══ Tool 6: save_style_preference (stretch: Style Profile Memory) ═════════════

@pytest.fixture
def profile_path(monkeypatch, tmp_path):
    path = tmp_path / "style_profile.json"
    monkeypatch.setattr(tools, "_STYLE_PROFILE_PATH", str(path))
    return path


def test_save_first_preference_creates_file(profile_path):
    result = save_style_preference("loves grunge")
    assert result == ["loves grunge"]
    import json
    saved = json.loads(profile_path.read_text())
    assert saved == {"preferences": ["loves grunge"]}


def test_save_appends_and_returns_updated_list(profile_path):
    save_style_preference("loves grunge")
    result = save_style_preference("dislikes pink")
    assert result == ["loves grunge", "dislikes pink"]


def test_save_dedupes_case_insensitively(profile_path):
    save_style_preference("loves grunge")
    result = save_style_preference("LOVES GRUNGE")
    assert result == ["loves grunge"]


def test_save_corrupt_profile_treated_as_empty(profile_path):
    profile_path.write_text("{broken")
    result = save_style_preference("loves grunge")
    assert result == ["loves grunge"]


def test_save_write_failure_returns_error_string(monkeypatch, tmp_path):
    # Point the profile path at a directory so the write raises OSError.
    monkeypatch.setattr(tools, "_STYLE_PROFILE_PATH", str(tmp_path))
    result = save_style_preference("loves grunge")
    assert isinstance(result, str)
    assert "loves grunge" in result
    assert "Couldn't save" in result
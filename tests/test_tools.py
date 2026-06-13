"""Tests for the three FitFindr tools, starting with search_listings.

Covers the per-tool verification checks from the Tool 1 spec in planning.md:
null brands, L vs XL size matching, empty results, plus price filtering,
relevance ordering, and One Size handling.
"""
from tools import search_listings


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
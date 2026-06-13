# Evidence locker — paste exhibits THE MOMENT they scroll past

Format per entry:

```markdown
## <date> · <ledger row it satisfies>
`command that produced it`
<verbatim output in a code block>
One line: what this proves.
```

High-value captures to grab during this project (don't let these scroll away):
- `pytest tests/` full pass output (Milestone 3 checkpoint)
- The three Milestone 5 failure-trigger commands and their outputs (zero-result search, empty wardrobe, empty outfit string)
- `python agent.py` output showing happy path AND no-results early return side by side
- A printed `session` dict at the end of a run (state management proof)
- Two runs of `create_fit_card` on the same input producing different captions (variation requirement)

<!-- Entries below -->

## 2026-06-12 · Trend data methodology (README §Trend Awareness, data source description)
`python utils/fetch_trends.py`
```
  vintage           2904 views  momentum -9.1%
  streetwear        5592 views  momentum -8.4%
  cottagecore       8311 views  momentum -12.4%
  y2k              12612 views  momentum -1.4%
  denim            17537 views  momentum -2.7%
  dark academia     9890 views  momentum +7.0%
  tie-dye           7026 views  momentum +10.6%
  gorpcore          9694 views  momentum +8.3%
  barbiecore         121 views  momentum +9.0%
  ... (23 trends total)
wrote data/trends.json: 23 trends
```
Methodology: trends.json is a snapshot of REAL reader-interest data from the
Wikimedia Pageviews API (official, public, no key). Each of the dataset's
style tags maps to an English Wikipedia style article (e.g. y2k →
Y2K_aesthetic). mentions = that article's pageviews over the most recent 30
days, momentum = recent 30 days vs the prior 30 as a ratio minus 1. Two real
trends with no stock in the listings (gorpcore, barbiecore) are included
deliberately so check_trends can honestly report in_stock: 0. An earlier
synthetic trends.json was rejected on data-integrity grounds and replaced
with this fetch. Script committed at utils/fetch_trends.py, rerun to refresh.
What this proves: the trend tool's data source is real, current, documented,
and reproducible.

## 2026-06-12 · AI usage receipt (README §AI Usage)
During `search_listings` implementation, Claude flagged that the dataset has three
One Size variants ("One Size", "One Size (adjustable)", "One Size / Oversized") and
proposed containment matching instead of exact token equality for the One Size rule,
since plain token matching would wrongly reject "One Size (adjustable)" for every
requested size. I reviewed it against the Thursday data profile (the three variants
are real, 4 listings total) and approved it as an implementation detail consistent
with the spec wording "listings marked One Size."
What this proves: directed AI use with human review, dataset-driven verification
before accepting generated logic.

## 2026-06-12 · pytest tests, ≥1 test per failure mode, all passing (Milestone 3) — Tool 1 portion
`python3 -m pytest tests/test_tools.py -v`
```
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0 -- /Volumes/External4GB/source/AI201/Week2/ai201-project2-fitfindr-starter/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Volumes/External4GB/source/AI201/Week2/ai201-project2-fitfindr-starter
configfile: pytest.ini
plugins: anyio-4.13.0
collecting ... collected 16 items

tests/test_tools.py::test_basic_search_returns_relevant_results PASSED   [  6%]
tests/test_tools.py::test_results_sorted_by_score_descending PASSED      [ 12%]
tests/test_tools.py::test_zero_score_listings_dropped PASSED             [ 18%]
tests/test_tools.py::test_no_matches_returns_empty_list PASSED           [ 25%]
tests/test_tools.py::test_null_brand_listings_do_not_crash_and_still_match PASSED [ 31%]
tests/test_tools.py::test_brand_is_searchable_when_present PASSED        [ 37%]
tests/test_tools.py::test_size_l_does_not_match_xl PASSED                [ 43%]
tests/test_tools.py::test_size_l_matches_combo_sizes PASSED              [ 50%]
tests/test_tools.py::test_size_m_matches_s_slash_m PASSED                [ 56%]
tests/test_tools.py::test_size_match_is_case_insensitive PASSED          [ 62%]
tests/test_tools.py::test_one_size_matches_any_requested_size PASSED     [ 68%]
tests/test_tools.py::test_shoe_and_waist_sizes_match_as_strings PASSED   [ 75%]
tests/test_tools.py::test_max_price_is_inclusive_ceiling PASSED          [ 81%]
tests/test_tools.py::test_max_price_below_minimum_returns_empty PASSED   [ 87%]
tests/test_tools.py::test_combined_filters PASSED                        [ 93%]
tests/test_tools.py::test_result_dicts_have_all_spec_fields PASSED       [100%]

============================== 16 passed in 0.21s ==============================
```
What this proves: `search_listings` tested in isolation before the planning loop.
Covers the Tool 1 spec verification checks (null brands, L vs XL, empty results)
plus its failure mode (no matches returns an empty list, no exception).
Full suite including data loader smoke tests: 19 passed.

## 2026-06-12 · suggest_outfit failure mode: empty wardrobe → general advice, no exception (Error Handling row + Milestone 5 capture)
`suggest_outfit(lst_002, get_empty_wardrobe())` live against Groq, alongside the happy path:
```
Item: lst_002 Y2K Baby Tee — Butterfly Print

=== With example wardrobe ===
You can create a cute and casual outfit by pairing the Y2K Baby Tee — Butterfly Print with the Baggy straight-leg jeans, dark wash and the Chunky white sneakers. This outfit works because the fitted crop length of the tee complements the high-waisted and baggy fit of the jeans, creating a nice balance of proportions. The chunky sneakers add a fun and playful touch to the overall look, matching the Y2K vibe of the tee.

Alternatively, you can dress up the Y2K Baby Tee — Butterfly Print by pairing it with the Wide-leg khaki trousers and the Black combat boots. This outfit works because the earthy tones of the trousers bring out the pink and purple hues in the butterfly graphic, creating a nice contrast. The black combat boots add an edgy touch, which is balanced by the sweetness of the butterfly print, resulting in a unique and stylish look.

=== With empty wardrobe ===
This Y2K baby tee is a great find, and with its fitted crop length and sweet butterfly graphic, it's perfect for creating a variety of looks. To style this top, consider pairing it with high-waisted pants or skirts to balance out the cropped length. A flowy maxi skirt in a neutral color like beige or denim would create a cute, cottagecore-inspired look, while high-waisted jeans or a flowy wide-leg pant would add a more retro touch.

In terms of colors, the pastel pink and purple hues in the butterfly graphic are soft and feminine, so try pairing the tee with other soft colors like pale yellow, mint green, or lavender. You could also add a pop of contrast with a brighter color like red or coral, but keep in mind the overall Y2K vibe of the top and opt for a more subtle approach.

For shoes, sneakers like Converse or Vans would be a great match for a casual, everyday look, while sandals or ankle boots could dress up the tee for a night out or special occasion. Overall, this top suits a playful, nostalgic vibe, so don't be afraid to have fun with it and experiment with different combinations of pieces to create a look that's all your own.
```
What this proves: the empty wardrobe failure mode returns general styling advice
instead of raising, per the Error Handling table. The happy path names real
wardrobe pieces (w_001 baggy jeans, w_007 chunky white sneakers), the exact
pairing planning.md predicts for the demo query. Tool 2 verified in isolation
before the planning loop.

## 2026-06-12 · pytest tests, ≥1 test per failure mode, all passing (Milestone 3) — Tool 2 portion
`python -m pytest tests/test_tools.py -v` (Tool 2 tests mock the Groq client, deterministic and keyless)
```
tests/test_tools.py::test_wardrobe_branch_returns_reply_and_names_pieces PASSED [ 62%]
tests/test_tools.py::test_empty_wardrobe_switches_to_general_advice_prompt PASSED [ 66%]
tests/test_tools.py::test_null_notes_skipped_in_wardrobe_prompt PASSED   [ 70%]
tests/test_tools.py::test_null_brand_skipped_in_item_prompt PASSED       [ 74%]
tests/test_tools.py::test_brand_included_when_present PASSED             [ 77%]
tests/test_tools.py::test_style_profile_included_when_given PASSED       [ 81%]
tests/test_tools.py::test_optional_sections_omitted_when_absent PASSED   [ 85%]
tests/test_tools.py::test_trends_included_when_given PASSED              [ 88%]
tests/test_tools.py::test_empty_llm_response_raises_runtime_error PASSED [ 92%]
tests/test_tools.py::test_groq_error_propagates_to_caller PASSED         [ 96%]
tests/test_tools.py::test_uses_specced_model PASSED                      [100%]

============================== 27 passed in 0.21s ==============================
```
What this proves: `suggest_outfit` failure contract tested, empty wardrobe
switches to general advice without raising, empty LLM response raises
`RuntimeError`, Groq errors propagate to the executor. Both null guards
(brand, notes) and both optional prompt sections covered. Full file run,
Tool 1's 16 tests still passing alongside.

## 2026-06-12 · create_fit_card variation requirement: two runs, same input, different captions (high-value capture)
Two consecutive `create_fit_card(outfit, item)` calls, identical input, live against Groq at temperature 1.0:
```
=== Run 1 ===
I just scored the cutest Y2K Baby Tee with a butterfly print on depop for $18.00 and I'm obsessed with how it looks paired with my baggy straight-leg jeans and chunky white sneakers, it's giving me a fresh streetwear vibe with a hint of vintage charm. The fitted crop top and loose jeans are a perfect combo, and the sneakers add just the right amount of sporty edge. I've also been experimenting with dressing it up with some wide-leg khaki trousers and black combat boots for a more laid-back, earthy look.

  name x1, price x1, platform x1

=== Run 2 (same input) ===
I just scored the cutest Y2K Baby Tee with a butterfly print on depop for $18.00 and I'm obsessed with how it looks with my baggy jeans and chunky sneakers. The fitted crop top and loose pants are such a great combo, it's giving me a perfect laid-back streetwear vibe. I've also been experimenting with dressing it up with khaki trousers and combat boots for a more edgy look, and I love how the earthy tones bring out the pastel colors in the tee.

  name x1, price x1, platform x1

Captions differ: True
```
What this proves: the variation requirement (higher temperature produces
different captions for the same input) and the once-each mention rule for
item name, price, and platform, counted programmatically in the output.

## 2026-06-12 · pytest tests, ≥1 test per failure mode, all passing (Milestone 3) — Tool 3 portion, row COMPLETE
`python -m pytest tests/test_tools.py -v` (Groq mocked, deterministic and keyless)
```
tests/test_tools.py::test_empty_outfit_returns_error_string_not_exception PASSED [ 80%]
tests/test_tools.py::test_whitespace_outfit_returns_error_string PASSED  [ 82%]
tests/test_tools.py::test_none_outfit_returns_error_string PASSED        [ 85%]
tests/test_tools.py::test_happy_path_returns_caption_and_prompts_with_required_fields PASSED [ 88%]
tests/test_tools.py::test_uses_higher_temperature_for_variation PASSED   [ 91%]
tests/test_tools.py::test_fit_card_empty_llm_response_raises_runtime_error PASSED [ 94%]
tests/test_tools.py::test_fit_card_groq_error_propagates PASSED          [ 97%]
tests/test_tools.py::test_fit_card_uses_specced_model PASSED             [100%]

============================== 35 passed in 0.22s ==============================
```
What this proves: `create_fit_card`'s failure mode per the Error Handling
table, empty or missing outfit returns a descriptive error string naming the
item and the fix (run `suggest_outfit` first), never an exception, and the
LLM is never called in that branch. All three required tools now have
failure mode tests passing, completing the Milestone 3 pytest requirement.

## 2026-06-12 · Stretch tools tested in isolation, all failure modes covered (feeds Price Comparison, Trend Awareness, Style Memory rows)
`python -m pytest tests/test_tools.py -v`, 17 new tests for `compare_prices`, `check_trends`, `save_style_preference`:
```
tests/test_tools.py::test_compare_prices_returns_full_verdict_dict PASSED [ 69%]
tests/test_tools.py::test_compare_prices_excludes_item_from_own_comparables PASSED [ 71%]
tests/test_tools.py::test_compare_prices_verdict_band_below_and_above PASSED [ 73%]
tests/test_tools.py::test_compare_prices_falls_back_to_category_on_rare_tags PASSED [ 75%]
tests/test_tools.py::test_compare_prices_not_enough_data_for_accessories PASSED [ 76%]
tests/test_tools.py::test_check_trends_returns_top5_sorted_by_mentions PASSED [ 78%]
tests/test_tools.py::test_check_trends_in_stock_zero_when_size_is_none PASSED [ 80%]
tests/test_tools.py::test_check_trends_category_filter_drops_absent_tags PASSED [ 82%]
tests/test_tools.py::test_check_trends_unknown_category_returns_empty_list PASSED [ 84%]
tests/test_tools.py::test_check_trends_size_counts_in_stock PASSED       [ 86%]
tests/test_tools.py::test_check_trends_missing_file_returns_empty_list PASSED [ 88%]
tests/test_tools.py::test_check_trends_corrupt_file_returns_empty_list PASSED [ 90%]
tests/test_tools.py::test_save_first_preference_creates_file PASSED      [ 92%]
tests/test_tools.py::test_save_appends_and_returns_updated_list PASSED   [ 94%]
tests/test_tools.py::test_save_dedupes_case_insensitively PASSED         [ 96%]
tests/test_tools.py::test_save_corrupt_profile_treated_as_empty PASSED   [ 98%]
tests/test_tools.py::test_save_write_failure_returns_error_string PASSED [100%]

============================== 52 passed in 0.26s ==============================
```
What this proves: every Error Handling table row for the stretch tools is
tested. `compare_prices` returns "not enough data" with `None` stats on the
accessories category (only 2 comparables after excluding the item).
`check_trends` returns an empty list on missing file, corrupt file, and
unmatched category, never raising. `save_style_preference` returns a
descriptive error string on write failure and treats a corrupt profile as
empty on read.

## 2026-06-12 · compare_prices and check_trends live isolation run (assessment-with-reasoning, trend narrowing)
`compare_prices(lst_001)` and `check_trends(category="tops", size="M")`, pure local, no LLM:
```
=== compare_prices(lst_001 Vintage Levi's 501 Jeans — Medium Wash, $38.00) ===
{
  "verdict": "above market",
  "item_price": 38.0,
  "comparable_count": 8,
  "comp_min": 14.0,
  "comp_median": 29.5,
  "comp_max": 36.0,
  "reasoning": "At $38.00 this item sits above the $29.50 median of 8 comparable bottoms listings."
}

=== check_trends(category='tops', size='M') ===
[
  {"tag": "y2k", "mentions": 12612, "momentum": -0.014, "in_stock": 2},
  {"tag": "crochet", "mentions": 11632, "momentum": -0.03, "in_stock": 1},
  {"tag": "dark academia", "mentions": 9890, "momentum": 0.07, "in_stock": 1},
  {"tag": "cottagecore", "mentions": 8311, "momentum": -0.124, "in_stock": 4},
  {"tag": "goth", "mentions": 7452, "momentum": -0.009, "in_stock": 1}
]
```
What this proves: the price assessment comes with comparable-based reasoning
(8 comparables, tag-overlap pool), and trends narrow by category with real
in-stock counts per size. Trend figures are REAL Wikimedia Pageviews data
from `data/trends.json` (see the methodology entry at the top of this file).
Re-run 2026-06-12 after the real snapshot replaced the rejected synthetic
one. 55 tests passing against the new file shape.
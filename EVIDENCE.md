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
# IMPROVEMENTS.md

Backlog of refinements and defects found during testing. Bugs are correctness
problems worth fixing. Enhancements are beyond the assignment spec and parked
on purpose. Nothing here blocks submission unless promoted.

---

## Bugs

### B1. Multi-token size requests like "US 8" never match (+ a vacuously passing test)

**Found:** 2026-06-13, while testing "boot size 9".

**What's wrong:** `_size_matches(requested, listing_size)` tokenizes only the
listing side, then checks `requested in tokens`. A bare number works
(`_size_matches("8", "US 8")` is True), but the `"US 8"` format the router is
told to use in the system prompt fails: `_size_matches("US 8", "US 8")` is
False, because the whole string `"us 8"` is compared against the listing tokens
`{us, 8}` and equals neither.

**Impact:** medium. Shoe-size filtering by `"US N"` returns nothing, then the
two-stage retry drops the size filter, so it degrades gracefully rather than
crashing. But it is incorrect, and which path hits depends on whether the router
sends `"8"` or `"US 8"`.

**Hidden by:** `test_shoe_and_waist_sizes_match_as_strings` passes vacuously.
`search_listings("sneakers shoes", size="US 8")` returns `[]`, and
`all("8" in r["size"] for r in [])` is `True`. The test asserts nothing.

**Fix (small, safe):** tokenize the requested side too and use subset matching.
`{us,8} ⊆ {us,8}` True, `{us,9} ⊆ {us,8}` False. This preserves every current
rule: `"L"` still does not match `XL` (`{l} ⊆ {xl}` is False), `"M"` still
matches `S/M`, `W30` still matches `W30 L30`. Then tighten the test to also
assert the result list is non-empty and contains the expected id.

### B2. Retry-loosening notice is shown twice (two channels, not two rounds)

**Found:** 2026-06-13, on "jacket under $25".

**What's wrong:** the "I dropped the price cap" message appears twice. Once as a
top "Note:" block, and again woven into the LLM's own reply ("Heads up, nothing
came in under $25, so the search automatically loosened the price filter...").
It looks like a double-print but it is two separate channels surfacing the same
fact: `_run_search` appends the adjustment to `session["notices"]` (which the
app renders as the "Note:" block), AND the search observation returned to the
router includes an "Adjustments made: ..." line, which the model re-narrates in
its final message.

**Impact:** low, cosmetic, but it reads as a bug and clutters the panel right
where the demo wants a clean retry story.

**Fix (pick one channel):** keep `session["notices"]` as the single source of
the adjustment message, since it is deterministic and always fires. Drop the
"Adjustments made: ..." prose from the search observation in `_run_search` so
the router stops echoing it. The observation to the LLM only needs the result
summary ("4 results, selected lst_032"). The user-facing "what was loosened"
line then appears exactly once, from `notices`.

### B3. Shopping queries sometimes stop and ask instead of finishing with a fit card

**Found:** 2026-06-13, on "jeans under $20" and "jacket under $25".

**What's wrong:** when a shopping query returns results (especially after the
price cap was loosened), the router sometimes ends with a conversational
`response` that lists options and asks "would you like me to style one?",
instead of proceeding through `suggest_outfit` and `create_fit_card`. The user
asked to shop, so ending without a fit card is the weak outcome, and it skips
the full three-tool chain that is the multi-step-workflow exhibit.

**Impact:** medium. The required workflow point is still earned by the clean
happy path, but inconsistency here weakens the demo and feels off to the user.

**Two candidate rules (decision deferred, Brian's taste call):**
- Simple rule: any query that returns a search result proceeds to an outfit and
  fit card. Found an item, style it. No item (no search, or no results), do not.
  This is deterministic and removes the intent-classification the LLM keeps
  fumbling (the stop-and-ask flakiness IS that classification failing).
- Intent rule: only shopping requests complete to a fit card. Pure info
  questions ("what's trending", "is X a good deal") just answer.

**The only real difference between them:** a pure price question like "is the
Levi's a good deal?" returns a result, so the simple rule would style it and
add a fit card unprompted (a bonus outfit), while the intent rule would just
give the price verdict. Charming or presumptuous in a styling app, undecided.

**Either way:** does not hurt adaptiveness (no-results and no-search paths still
branch) or the stretches (price verdict still surfaces, trend-influence exhibit
is a separate query). Both are prompt nudges, no code.

**Parked sub-part:** price-aware selection. When the budget could not be met,
pick the cheapest result (closest to the stated "under $X" intent) rather than
the top relevance match. Needs its own logic since search sorts by relevance,
not price. Lower priority.

### B4. Trend output not used to drive the follow-up search

**Found:** 2026-06-13, on "show me what's popular and find me something in size M".

**What's wrong:** `check_trends(size="M")` correctly returned trends with M
in-stock counts (Y2K 3, Dark Academia 1, Denim 1, Crochet 1, 2000s 0). But the
follow-up `search_listings` was called with `description="popular trending
fashion"`, a literal nonsense phrase that matches almost nothing. It found zero
in M, loosened to a size S biker short, and then stopped to ask. The agent had
the right information (which trends have M stock) and did not use it to build
the search. It even displayed "Dark Academia, fastest rising, 1 item in M" and
still failed to search for it.

**Impact:** medium. This is the trend-to-action chain, the heart of the trend
feature. It is non-deterministic: the same query chained cleanly on Groq earlier
(trends to search to an outfit that referenced Y2K), so this is a reliability
gap, not a hard break.

**Fix (prompt instruction, no code):** when the user asks for "something
trending/popular" without naming a specific item, the router must pick a
concrete trending tag from the `check_trends` result, preferring one with
`in_stock > 0` for the requested size, and pass THAT as the search description
(for example `search_listings("y2k", size="M")`). Never search the literal
words "popular" or "trending". With this, a real M item is found and the chain
completes on its own, which also resolves the stop-and-ask in B3 for this case.

### B5. Router is blind to the saved style profile (breaks Style Memory recall) — RESOLVED 2026-06-13

**Found:** 2026-06-13, Group I session 2, "find me a tee to style" after a
grunge preference was saved.

**What's wrong:** the profile loads correctly into `session["style_profile"]`,
but it is only injected into the `suggest_outfit` prompt by the executor. The
router (the LLM choosing tools) is never told about it, it only sees the system
prompt and the query. So on "find me a tee to style" the router asked the user
for size, budget, and "style vibe", the very preference already on file. It
read the styles and then asked the user to restate them.

**Why this one matters more:** it breaks the gradable Style Memory recall
exhibit (+2). The recall moment is supposed to show the agent using a saved
preference WITHOUT the user re-stating it. Asking "what's your style vibe?"
right after loading the saved style is the visible opposite of that, even if a
later outfit would have leaned grunge.

**Two coupled causes:**
1. The router does not see `session["style_profile"]`, so it cannot skip asking
   for style or bias the search toward the saved taste.
2. It stops to ask for optional params (size, budget). Only `description` is
   required, "find me a tee" is enough to search.

**Fix (small, prompt-level):** surface the loaded profile into the router's
context, for example a line appended to the system prompt or a preamble:
"Saved style preferences: grunge. Use these to inform the search and styling,
and do not ask the user to restate them." Plus a nudge that size and price are
optional and the agent should not demand them. Then the recall is visible in the
behavior, which is what the rubric grades.

**Recommendation:** unlike the other items here, consider fixing this BEFORE the
demo, since the Style Memory recall is a +2 gradable moment and the fix is small.

**RESOLUTION (2026-06-13):** done in `agent.py`. `run_agent` now appends the
loaded `session["style_profile"]` to the router's system content at session
start, and `_SYSTEM_PROMPT` instructs the router to fold saved preferences into
search and styling, never ask the user to restate them, and treat size/price as
optional. Verified via the sidecar: "find me a tee to style" after a saved
"loves grunge" now runs `search_listings -> suggest_outfit -> create_fit_card`
with no clarifying questions, and the outfit opens "perfect match for your
grunge aesthetic". 59 tests still pass.

---

## Enhancements (beyond spec, parked)

### E1. Directional shoe sizing: too big is fine, too small only if very close

**Raised:** 2026-06-13, by Brian, after "boot size 9" surfaced the `US 8.5` boot
via retry.

**Idea:** real shoe fit is directional. A shoe larger than the requested size is
wearable. A shoe smaller is not, unless it is extremely close, roughly a half
size, and even then the agent should say so out loud.

Desired behavior for a requested shoe size:
- Exact match: ideal, surface normally.
- Larger than requested: acceptable, surface normally.
- Up to a half size smaller: acceptable, but the agent MUST mention it runs
  small (for example "this runs a half size small, US 8.5 for your 9").
- More than a half size smaller: exclude.

**Where it lives:** two parts. The matching/search layer needs numeric-aware,
directional shoe-size comparison instead of pure token equality (parse `US 8.5`
to a number, compare with direction and a tolerance). The communication layer,
the prompt, needs to flag any non-exact size on a returned item so the user is
told. Brian framed the headline as "the prompt needs to know," so the
must-mention-it piece is the priority.

**Why parked:** the spec only requires case-insensitive token matching where
"M" matches "S/M". Directional numeric sizing is a real feature with its own
parsing (shoe scale, letter scale S<M<L<XL, waist sizes), out of scope for the
graded build. Revisit only after submission, or if a demo query makes it look
bad.

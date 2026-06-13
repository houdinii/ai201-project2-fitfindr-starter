# FitFindr Build Checklist

## Setup (5 min)
- [x] `source .venv/bin/activate`
- [x] `python utils/data_loader.py` runs clean

## search_listings (no LLM, fastest win)
- [x] Implement `search_listings`
- [x] Null brand skipped, no crash
- [x] "L" does NOT match "XL"
- [x] "One Size" matches any size
- [x] Test: normal query returns results
- [x] Test: impossible query returns `[]`
- [x] Test: price filter respected
- [x] Test: size token matching
- [x] `pytest tests/` green
- [x] Paste pytest output into EVIDENCE.md

## suggest_outfit
- [x] Implement `suggest_outfit` (Groq)
- [x] Empty wardrobe → general advice, no crash
- [x] Null `notes` skipped in prompt
- [x] Optional params `style_profile`, `trends` wired
- [x] Test: empty wardrobe case
- [x] One manual run pasted into EVIDENCE.md

## create_fit_card
- [x] Implement `create_fit_card` (Groq, high temp)
- [x] Empty outfit → error string, no exception
- [x] Run twice, same input, outputs differ
- [x] Paste both runs into EVIDENCE.md
- [x] Test: empty outfit case

## stretch tools
- [x] Implement `compare_prices`
- [x] Test: under 3 comparables → "not enough data"
- [x] Implement `save_style_preference`
- [x] Writes file AND `session["style_profile"]`
- [x] Author `data/trends.json` (real tags + 2 fakes)
- [x] Implement `check_trends`
- [x] Test: missing trends.json → `[]`

## router (agent.py)
- [x] Session dict: add new fields
- [x] Tool schemas for Groq function calling
- [x] Router loop: call → validate → execute → append
- [x] Executor resolves `item_id` from session
- [x] Executor injects wardrobe / profile / trends
- [x] Guard: `MAX_ITERATIONS`
- [x] Guard: empty results → retry, drop size
- [x] Guard: retry 2, drop max_price
- [x] Guard: still empty → error, NO suggest_outfit
- [x] Guard: no fit card without outfit
- [x] Guard: empty description → ask user
- [x] Bad tool / bad ref → observation back to router
- [x] LLM failure → one retry → error
- [x] `python agent.py` happy path works
- [x] `python agent.py` ballgown path errors right
- [x] Paste both `tool_log`s into EVIDENCE.md

## failure drills
- [x] Terminal: trigger zero results → EVIDENCE.md
- [x] Terminal: trigger empty wardrobe → EVIDENCE.md
- [ ] Terminal: trigger empty outfit → EVIDENCE.md
- [ ] Screenshot one failure for the demo

## app
- [x] Implement `handle_query` in app.py
- [ ] `python app.py`: all 3 panels populate
- [ ] Two-session style memory test works

## README
- [ ] Tool inventory, 6 tools, params match code exactly
- [ ] Planning loop section (real conditional logic)
- [ ] No-results behavior with verbatim message text
- [ ] State management section
- [ ] Error handling per tool + 1 real example from EVIDENCE.md
- [ ] Spec reflection: 1 way it helped, 1 divergence + why
- [ ] AI usage: 2+ instances, what I directed, what I overrode
- [ ] Stretch: price comparison section
- [ ] Stretch: style memory section
- [ ] Stretch: trends section (name data source)
- [ ] Stretch: retry section

## demo video (3 to 5 min, hard limit)
- [ ] Write narration script from RUBRIC_LEDGER.md
- [ ] Rehearse once, time it
- [ ] Record: happy path, all 3 tools, narrated
- [ ] Record: state passing shown (print selected_item)
- [ ] Record: ballgown query, retry, graceful error
- [ ] Record: style memory across two sessions
- [ ] Record: price verdict + trend influence moments
- [ ] Confirm length is 3 to 5 minutes

## ship it
- [ ] Run /grade-sim, fix everything it flags
- [ ] `.env` NOT in the repo
- [ ] git push to fork
- [ ] planning.md in repo root on GitHub
- [ ] Submit portal: repo link + video
- [ ] Breathe

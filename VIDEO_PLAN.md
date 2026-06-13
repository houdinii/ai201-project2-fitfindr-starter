# Demo Video Plan — 3 to 5 minutes, HARD limit

Target runtime 4:30. Every shot lists the rubric points it collects.
The video carries 9 required points + all 7 stretch points. Do not improvise, read the beats.

## Pre-flight (before recording anything)
- [ ] Delete `data/style_profile.json` so the save/recall story starts clean
- [ ] Terminal font size up, dark theme, window big enough to read on a phone
- [ ] `python app.py` running and tested once off camera
- [ ] Both demo queries pasted in a scratch file, ready to copy
- [ ] Screen recorder + mic checked, do one 20-second test clip
- [ ] Rehearse the whole thing once with a timer. Over 5:00 = cut narration, not exhibits

---

## Shot 1 — Intro (0:00 to 0:15)
**On camera:** the Gradio app, open and idle.
**Say:** "This is FitFindr, a multi-tool thrifting agent. An LLM router picks the tools, hard code guards bound what it can do. Six tools, one session dict."
**Collects:** context for everything that follows.

## Shot 2 — Happy path, the big one (0:15 to 1:40)
**On camera:** Gradio. Paste query 1:
"I've been really into streetwear lately. Can you find me some vintage Levi's, waist 30, under $40? And tell me if that's a fair price, I always overpay."
**Narrate as panels fill, name each tool as it fires:**
- "It saved 'streetwear' as a style preference, that's `save_style_preference`"
- "`search_listings` parsed description, size W30, max price 40 from my sentence, found the Levi's 501s"
- "`compare_prices` says [verdict], based on comparable listings, that's the price tool"
- "`suggest_outfit` is styling it against my actual wardrobe"
- "`create_fit_card` wrote the caption, item, price, platform, ready to post"
**Collects:** all 3 required tools in one interaction (1pt), complete query-to-fit-card workflow (1pt), narration of each step (1pt), price comparison stretch (+2), the save half of style memory.

## Shot 3 — State passing, terminal (1:40 to 2:10)
**On camera:** terminal. Run the agent CLI version of the same query, show `session["tool_log"]` and the printed session.
**Say:** "The router never retypes data. It said `item_id lst_001`, three characters. The executor pulled the real dict from the session, the same object search returned is what suggest_outfit received, and the outfit string is what create_fit_card received. The user never re-entered anything."
**Point at:** `selected_item` id matching the search result, `outfit_suggestion` flowing into the fit card call.
**Collects:** item flows search → suggest without re-entry (1pt), outfit flows suggest → card without re-entry (1pt).

## Shot 4 — Style memory recall, fresh session (2:10 to 2:45)
**On camera:** restart the app or new CLI run, visibly fresh. First `cat data/style_profile.json` to show "streetwear" persisted on disk. Then query 2:
"Find me a jacket, size M, under $50."
**Say:** "New session, I never mentioned streetwear this time. The suggestion leans streetwear because the profile loaded from disk at session start."
**Collects:** style profile memory, two interactions, no re-entry (+2).

## Shot 5 — Trends (2:45 to 3:15)
**On camera:** query 3: "What's trending in my size? Style me something."
**Say:** "`check_trends` reads the trends snapshot, filters to what's actually in stock in my size, and the outfit suggestion name-checks the trend. Trend with zero stock doesn't get pushed."
**Collects:** trend info visibly influencing the suggestion (+2).

## Shot 6 — Failure, retry, adaptiveness (3:15 to 4:10)
**On camera:** the impossible query:
"I need a designer ballgown, size XXS, under $5."
**Narrate the cascade:**
- "Zero results. Watch what it does instead of crashing: retry one, size filter dropped, it tells me. Retry two, price cap dropped, it tells me."
- "Still nothing, so it stops with a specific message: what failed, that the cheapest item in stock is $12, what to change."
- "And look at the tool log next to the happy path: completely different sequence. It never called suggest_outfit with empty results. The agent adapts, it doesn't run a script."
**Collects:** different behavior for non-standard input (2pts), deliberately triggered failure (1pt), specific and actionable response (1pt), retry with explanation (+1).

## Shot 7 — Close (4:10 to 4:30)
**On camera:** the fit card from shot 2.
**Say:** "Query to shareable fit card, six tools, every failure handled. FitFindr."

---

## After recording
- [ ] Watch it once. Confirm every "Collects" line above is actually visible
- [ ] Confirm runtime is between 3:00 and 5:00
- [ ] Tick the demo rows in RUBRIC_LEDGER.md

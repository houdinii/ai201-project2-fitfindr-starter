# Demo — Two-Pass Workflow (silent capture, then voiceover)

Record the screen silently first, then narrate over it in a quiet moment. This
is easier than live narration and sounds better. Target final cut 4:30, hard
limit 3 to 5 minutes.

Workflow:
1. **Pass 1** — capture the screen silently, running each scene's query in order, holding on each result so there's footage to talk over.
2. **Pass 2** — record the voiceover from the script below, in a quiet room, scene by scene.
3. **Pass 3** — lay the voiceover over the footage in any editor (iMovie, CapCut, QuickTime), trim to length, export.

---

## Pre-flight (before Pass 1)

- [ ] Groq working (free tier resets daily). Quick test:
      `python -c "from tools import _get_groq_client,_GROQ_MODEL as m; print(_get_groq_client().chat.completions.create(model=m,messages=[{'role':'user','content':'hi'}],max_tokens=3).choices[0].message.content)"`
      Must print text, not a rate-limit error. **Record on Groq, not the sidecar.**
- [ ] Reset the saved profile for Scene 5: `rm -f data/style_profile.json`
- [ ] Launch with the log visible: `FITFINDR_LOG=1 python app.py`
- [ ] Screen arranged so BOTH show: the browser (Gradio 3 panels) and the terminal (live log). The log is your state-passing proof.
- [ ] Screen recorder ready. One throwaway test clip first.

---

## PASS 1 — Silent screen capture

Run the queries in this exact order. **No talking.** After each result finishes
rendering, **hold still for ~4 seconds** (don't move the mouse) so you have clean
footage to narrate over. If a query misbehaves, just re-run it.

You can record this as one continuous take, or stop between scenes and do
separate clips, whichever is easier to edit.

| # | TYPE THIS into Gradio | After it finishes |
|---|---|---|
| 1 | `find me a 90s track jacket` | Hold on the 3 filled panels ~4s. Then slowly move the mouse to the terminal and hold on the log showing `lst_004` flowing search → suggest → card ~5s. |
| 2 | `designer ballgown size XXS under $5` | Hold on the error message ~4s, then hold on the terminal log showing the retries ~4s. |
| 3 | `is the vintage Levi's 501 a good deal?` | Hold on the price verdict + reasoning text ~5s. |
| 4 | `what's popular right now? style me something in size M` | Hold on the outfit text where it names a trend ~5s. (If it doesn't clearly name a trend, re-run.) |
| 5a | `I'm really into grunge lately, find me a flannel` | Hold on the terminal showing `save_style_preference` ~4s. |
| 5b | reload the page, then `find me a tee to style` | Hold on the grunge-leaning outfit ~5s. |

That's the whole capture. Stop recording.

---

## PASS 2 — Voiceover script

Record these in a quiet room. Read naturally, pause between scenes. You can
record one clip per scene and line them up in editing. Rough durations in
brackets, total ~4:15 of talking.

**Scene 1 [~45s]**
"This is FitFindr, an agent that finds secondhand fashion and styles it. I asked
for a 90s track jacket in plain language. In the log you can see the router call
three tools in order: `search_listings` finds the jacket, `suggest_outfit`
styles it against my saved wardrobe naming real pieces, and `create_fit_card`
writes the shareable caption. One query, three tools, ending in a finished
outfit. And notice the item id the search returned is the exact same id passed
into the styling and the caption. The agent never re-types the item, it passes a
reference and the code resolves it. State flows through the session, not through
the language model."

**Scene 2 [~40s]**
"Now something impossible, a designer ballgown in size double-extra-small under
five dollars. Nothing matches, so instead of crashing, the agent adapts. It
retries automatically, first dropping the size filter and telling me, then
dropping the price cap and telling me again. Still nothing, so it stops with a
specific message: the cheapest item in stock is twelve dollars, try a different
description. And notice this tool sequence is completely different from the happy
path. The agent responds to what each tool returns, it never tried to build an
outfit out of nothing."

**Scene 3 [~30s]**
"Here I ask whether something's a good deal. The router calls `compare_prices`,
which gathers comparable listings in the same category and compares against their
median price. It returns a verdict with the actual numbers it used. A real price
assessment grounded in the dataset, not a guess."

**Scene 4 [~35s]**
"This one checks trends. The trend data is real, it's a snapshot of actual
Wikipedia readership for fashion styles, fetched by a script in the repo, not
invented numbers. The agent pulls what's trending and in stock in my size, and
the outfit it builds references that trend directly."

**Scene 5 [~45s]**
"Last, memory across sessions. I mention that I'm into grunge, and in the log you
can see it call `save_style_preference` and write that to disk. Now I reload, a
completely fresh session, and I ask for a tee to style without mentioning grunge
at all. But the outfit comes back grunge-leaning, because at session start it
loaded my saved preference from the file. It remembered me without my repeating
myself."

**Scene 6 [~12s]**
"So that's FitFindr. Plain-language query to a shareable fit card, six tools, an
LLM router with hard guardrails, and every failure handled gracefully. Thanks for
watching."

---

## PASS 3 — Assemble

- [ ] Drop the footage and the voiceover clips into an editor.
- [ ] Line each VO scene up with its footage. If a scene's talk runs longer than its footage, slow/extend the held shot or trim words.
- [ ] Trim the whole thing to between 3:00 and 5:00.
- [ ] Watch it once: audio clear, on-screen text readable.
- [ ] Export, upload, grab the link.

## After
- [ ] Paste the video link into README.md (TODO at the top).
- [ ] Commit + push to your fork.
- [ ] Submit repo link + video link through the Course Portal.

## Notes
- Scenes 1, 2, 3, 5 are reliable. Scene 4 (trends) is the one to re-run if the
  outfit doesn't clearly name a trend.
- If holding silent shots feels awkward, record each scene as its own clip and
  just keep the good ones.
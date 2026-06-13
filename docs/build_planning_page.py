#!/usr/bin/env python3
"""Generate planning.html (designed spec page) from planning.md.

Rerun any time planning.md changes:
    .venv/bin/python docs/build_planning_page.py
"""
import html as H
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "planning.md").read_text()


# ── inline markdown: escape, then `code`, **bold**, *em* ────────────────────
def inline(text: str) -> str:
    t = H.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    return t


def prose(block: str) -> str:
    """Paragraphs + simple bullet lists from a markdown chunk."""
    out, buf, lis = [], [], []

    def flush_p():
        if buf:
            out.append(f"<p>{inline(' '.join(buf))}</p>")
            buf.clear()

    def flush_l():
        if lis:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in lis) + "</ul>")
            lis.clear()

    for line in block.split("\n"):
        s = line.strip()
        if s.startswith("[//]:") or s == "---":
            continue
        if re.match(r"^[-*]\s+", s):
            flush_p()
            lis.append(re.sub(r"^[-*]\s+", "", s))
        elif re.match(r"^\d+\.\s+", s):
            flush_p()
            lis.append(re.sub(r"^\d+\.\s+", "", s))
        elif s:
            flush_l()
            buf.append(s)
        else:
            flush_p()
            flush_l()
    flush_p()
    flush_l()
    return "\n".join(out)


PARAM_RE = re.compile(r"^-\s+(`.+?`(?:\s*/\s*`.+?`)*)\s+\((.+?)\):\s*(.+)$")


def param_rows(block: str):
    """Return (rows, leftovers): bullets matching `name` (type): desc."""
    rows, leftovers = [], []
    for line in block.split("\n"):
        s = line.strip()
        if not s or s.startswith("[//]:"):
            continue
        m = PARAM_RE.match(s)
        if m:
            name = m.group(1).replace("`", "")
            typ = m.group(2).replace("`", "")
            rows.append((name, typ, m.group(3)))
        else:
            leftovers.append(s)
    return rows, leftovers


def param_table(rows, head=("field", "type", "description")) -> str:
    body = "".join(
        f'<tr><td class="pname">{H.escape(n)}</td>'
        f'<td class="ptype">{H.escape(t)}</td><td>{inline(d)}</td></tr>'
        for n, t, d in rows
    )
    ths = "".join(f"<th>{h}</th>" for h in head)
    return f'<table class="params"><thead><tr>{ths}</tr></thead><tbody>{body}</tbody></table>'


# ── split planning.md into ## sections ──────────────────────────────────────
sections: dict[str, str] = {}
cur, buf = "_intro", []
for line in SRC.split("\n"):
    if line.startswith("## "):
        sections[cur] = "\n".join(buf)
        cur, buf = line[3:].strip(), []
    else:
        buf.append(line)
sections[cur] = "\n".join(buf)


# ── tools ────────────────────────────────────────────────────────────────────
TOOL_KIND = {
    "search_listings": ("pure local", "local"),
    "suggest_outfit": ("LLM call", "llm"),
    "create_fit_card": ("LLM call", "llm"),
    "compare_prices": ("pure local", "local"),
    "check_trends": ("local file", "file"),
    "save_style_preference": ("writes disk", "file"),
}
FIELD_RE = re.compile(
    r"\*\*(What it does|Input parameters|What it returns|"
    r"What happens if it fails or returns nothing):\*\*"
)


def render_tool(chunk: str) -> str:
    first, _, rest = chunk.partition("\n")
    m = re.match(r"Tool\s+(\d+):\s*(\w+)", first.strip())
    if not m:
        return ""
    num, name = m.group(1), m.group(2)
    kind, kcls = TOOL_KIND.get(name, ("", "local"))

    # split off the data-notes asides (Tool 1 breakdowns)
    aside = ""
    am = re.search(r"\*\*Breakdown of Listings\*\*", rest)
    if am:
        rest, aside_src = rest[: am.start()], rest[am.start():]
        items = []
        for line in aside_src.split("\n"):
            s = line.strip()
            if s.startswith("**") or not s:
                items.append(f"<h4>{inline(s.strip('*'))}</h4>" if s else "")
            else:
                items.append(f"<p>{inline(re.sub(r'^[-0-9.]+s*', '', s))}</p>")
        aside = (
            '<details class="datanotes"><summary>Data notes '
            "(field profiles &amp; traps from exploring the dataset)</summary>"
            + "".join(items)
            + "</details>"
        )

    parts = FIELD_RE.split(rest)
    fields = dict(zip(parts[1::2], parts[2::2]))
    out = [
        f'<article class="tool" id="tool-{name}">',
        f'<header><span class="tnum">{num.zfill(2)}</span>'
        f"<h3>{name}</h3>"
        f'<span class="badge {kcls}">{kind}</span></header>',
    ]
    if "What it does" in fields:
        out.append('<div class="tfield"><h4>What it does</h4>'
                   + prose(fields["What it does"]) + "</div>")
    if "Input parameters" in fields:
        rows, extra = param_rows(fields["Input parameters"])
        out.append('<div class="tfield"><h4>Inputs</h4>')
        if rows:
            out.append(param_table(rows, ("parameter", "type", "meaning")))
        for x in extra:
            out.append(f"<p>{inline(x)}</p>")
        out.append("</div>")
    if "What it returns" in fields:
        rows, extra = param_rows(fields["What it returns"])
        out.append('<div class="tfield"><h4>Returns</h4>')
        for x in extra:
            out.append(f"<p>{inline(x)}</p>")
        if rows:
            out.append(param_table(rows))
        out.append("</div>")
    k = "What happens if it fails or returns nothing"
    if k in fields:
        out.append('<div class="tfield fail"><h4>On failure</h4>'
                   + prose(fields[k]) + "</div>")
    out.append(aside)
    out.append("</article>")
    return "\n".join(out)


tools_html = "".join(
    render_tool(c) for c in sections.get("Tools", "").split("### ")[1:]
)


# ── error handling table → classified cards ─────────────────────────────────
def error_cards(block: str) -> str:
    cards = []
    for line in block.split("\n"):
        s = line.strip()
        if not s.startswith("|") or set(s) <= set("|- ") or s.startswith("| Tool"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3:
            continue
        comp, mode, resp = cells[0], cells[1], cells[2]
        soft = any(w in resp.lower() for w in ("continue", "self-correct", "asks what"))
        cls = "soft" if soft else "hard"
        tag = "degrade &amp; continue" if soft else "stop with error"
        cards.append(
            f'<div class="ecard {cls}"><div class="ehead">'
            f'<span class="ecomp">{inline(comp)}</span>'
            f'<span class="etag">{tag}</span></div>'
            f'<p class="emode">{inline(mode)}</p>'
            f'<p class="eresp">{inline(resp)}</p></div>'
        )
    return '<div class="egrid">' + "".join(cards) + "</div>"


errors_html = error_cards(sections.get("Error Handling", ""))


# ── stretch notes → feature cards ────────────────────────────────────────────
def stretch_cards(block: str) -> str:
    intro, cards = [], []
    for line in block.split("\n"):
        s = line.strip()
        if s.startswith("[//]:") or not s:
            continue
        m = re.match(r"^-\s+\*\*(.+?)\s*\(\+(\d+)\)\.\*\*\s*(.*)$", s)
        if m:
            cards.append(
                f'<div class="scard"><div class="shead"><h4>{inline(m.group(1))}</h4>'
                f'<span class="pts">+{m.group(2)}</span></div>'
                f"<p>{inline(m.group(3))}</p></div>"
            )
        elif not s.startswith("-"):
            intro.append(f"<p>{inline(s)}</p>")
    return "".join(intro) + '<div class="sgrid">' + "".join(cards) + "</div>"


stretch_html = stretch_cards(sections.get("Stretch Notes", ""))


# ── state management: bullets → table, rest prose ────────────────────────────
def state_html(block: str) -> str:
    block = re.sub(r"\*\*How does information.*?\*\*", "", block)
    rows, _ = param_rows(block)
    no_bullets = "\n".join(
        l for l in block.split("\n") if not PARAM_RE.match(l.strip())
    )
    table = param_table(rows, ("session key", "type", "holds")) if rows else ""
    # place table after the first paragraph
    paras = prose(no_bullets).split("</p>", 1)
    if len(paras) == 2:
        return paras[0] + "</p>" + table + paras[1]
    return prose(no_bullets) + table


state = state_html(sections.get("State Management", ""))

loop_block = re.sub(
    r"\*\*How does your agent decide.*?\*\*", "",
    sections.get("Planning Loop", ""))
loop = prose(loop_block)


# ── architecture: mermaid blocks + optional images ──────────────────────────
arch_src = sections.get("Architecture", "")
mermaids = re.findall(r"```mermaid\n(.*?)```", arch_src, re.S)
images = re.findall(r"!\[(.*?)\]\((.*?)\)", arch_src)
MLABELS = ["Control flow — router, executor, guards",
           "Triggers, state flow, and failure routing"]
arch = ""
for i, mm in enumerate(mermaids):
    label = MLABELS[i] if i < len(MLABELS) else f"Diagram {i+1}"
    arch += (f'<figure class="diagram"><figcaption>{label}</figcaption>'
             f'<pre class="mermaid">{H.escape(mm)}</pre></figure>')
if images:
    arch += '<details class="datanotes"><summary>Hand-drawn versions (PNG)</summary>'
    for alt, srcp in images:
        arch += f'<p><img src="{H.escape(srcp)}" alt="{H.escape(alt)}"></p>'
    arch += "</details>"


# ── AI tool plan ─────────────────────────────────────────────────────────────
plan_src = sections.get("AI Tool Plan", "")
plan_src = re.sub(r"<!--.*?-->", "", plan_src, flags=re.S)
plan_parts = re.split(r"\*\*(Milestone \d[^*]*)\*\*", plan_src)
plan = ""
for title, body in zip(plan_parts[1::2], plan_parts[2::2]):
    plan += f'<div class="milestone"><h3>{inline(title.strip(": "))}</h3>{prose(body)}</div>'


# ── walkthrough → timeline ───────────────────────────────────────────────────
walk_src = sections.get("A Complete Interaction (Step by Step)", "")
walk_src = re.sub(r"<!--.*?-->", "", walk_src, flags=re.S)
qm = re.search(r"\*\*Example user query:\*\*\s*(.+)", walk_src)
query_html = f'<blockquote class="query">{inline(qm.group(1))}</blockquote>' if qm else ""
steps = re.split(r"\*\*(Setup|Step \d+|Final output to user):\*\*", walk_src)
timeline = ""
for title, body in zip(steps[1::2], steps[2::2]):
    body = re.sub(r"\*\*Example user query:\*\*.*", "", body)
    mark = "&#9201;" if title == "Setup" else ("&#10003;" if "Final" in title else title.split()[-1])
    timeline += (f'<li><span class="tmark">{mark}</span>'
                 f'<div><h4>{title}</h4>{prose(body)}</div></li>')
walk = query_html + f'<ol class="timeline">{timeline}</ol>'


# ── page assembly ────────────────────────────────────────────────────────────
TOC = [
    ("tools", "Tools", "01"),
    ("loop", "Planning Loop", "02"),
    ("state", "State Management", "03"),
    ("errors", "Error Handling", "04"),
    ("stretch", "Stretch Features", "05"),
    ("arch", "Architecture", "06"),
    ("plan", "AI Tool Plan", "07"),
    ("walk", "Complete Interaction", "08"),
]
toc_html = "".join(
    f'<a href="#{i}"><span>{n}</span>{t}</a>' for i, t, n in TOC
)


def section(sid, num, title, body, lede=""):
    lede_html = f'<p class="lede">{lede}</p>' if lede else ""
    return (f'<section id="{sid}" style="--n:\'{num}\'">'
            f"<h2>{title}</h2>{lede_html}{body}</section>")


body = "\n".join([
    section("tools", "01", "Tools",
            tools_html,
            "Six tools. Three required, three stretch. The router only ever sees "
            "each tool's name, input signature, and output type."),
    section("loop", "02", "Planning Loop", loop,
            "A ReAct-style router loop. The LLM proposes, the guards dispose."),
    section("state", "03", "State Management", state,
            "The session dict is the single source of truth. The LLM routes, "
            "the session carries."),
    section("errors", "04", "Error Handling", errors_html,
            "Every failure is classified: amber degrades and continues, "
            "red stops with a specific, actionable error."),
    section("stretch", "05", "Stretch Features", stretch_html),
    section("arch", "06", "Architecture", arch),
    section("plan", "07", "AI Tool Plan", plan,
            "Spec first, then the spec becomes the prompt. Generated code is "
            "verified against this document before it stays."),
    section("walk", "08", "A Complete Interaction", walk),
])

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FitFindr · Planning Spec</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #2a2d31;
  --bg-deep: #232629;
  --panel: #313539;
  --panel-2: #383d42;
  --ink: #d9dcdf;
  --ink-dim: #9aa1a8;
  --ivory: #f0ece4;
  --brass: #cfa368;
  --brass-dim: #a98a5e;
  --sage: #a3b89a;
  --rust: #c98a7d;
  --line: #43484e;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; scroll-padding-top: 2rem; }}
body {{
  margin: 0;
  background:
    radial-gradient(1200px 600px at 85% -10%, #33373c 0%, transparent 60%),
    var(--bg);
  color: var(--ink);
  font: 400 17px/1.75 "Source Sans 3", sans-serif;
}}
/* ── masthead ── */
.masthead {{
  border-bottom: 1px solid var(--line);
  padding: 4.5rem 2rem 3rem;
  background: linear-gradient(180deg, var(--bg-deep), transparent);
}}
.masthead .in {{ max-width: 1180px; margin: 0 auto; }}
.kicker {{
  font: 500 .72rem/1 var(--mono);
  letter-spacing: .28em; text-transform: uppercase;
  color: var(--brass);
}}
.masthead h1 {{
  font: 600 clamp(2.6rem, 6vw, 4.2rem)/1.05 "Fraunces", serif;
  color: var(--ivory); margin: .35rem 0 .8rem;
  letter-spacing: -.01em;
}}
.masthead h1 em {{ font-style: italic; color: var(--brass); }}
.sub {{ max-width: 56ch; color: var(--ink-dim); font-size: 1.05rem; }}
.meta {{
  display: flex; gap: 2.2rem; margin-top: 1.6rem; flex-wrap: wrap;
  font: 400 .8rem/1.5 var(--mono); color: var(--ink-dim);
}}
.meta b {{ display: block; color: var(--ivory); font-weight: 500; font-size: .92rem; }}
/* ── layout ── */
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 2rem;
        display: grid; grid-template-columns: 200px minmax(0,1fr); gap: 3.5rem; }}
nav.toc {{ position: sticky; top: 2rem; align-self: start;
          display: flex; flex-direction: column; gap: .15rem; padding-top: 2.4rem; }}
nav.toc a {{
  color: var(--ink-dim); text-decoration: none;
  font: 400 .82rem/1.4 var(--mono); padding: .42rem .6rem;
  border-left: 2px solid var(--line); transition: all .15s;
}}
nav.toc a span {{ color: var(--brass-dim); margin-right: .55em; font-size: .72rem; }}
nav.toc a:hover {{ color: var(--ivory); border-left-color: var(--brass); }}
main {{ min-width: 0; }}
/* ── sections ── */
section {{ position: relative; padding: 2.4rem 0 1rem; }}
section + section {{ border-top: 1px solid var(--line); margin-top: 2rem; }}
section::before {{
  content: var(--n);
  position: absolute; top: 1.1rem; right: 0;
  font: 700 5.5rem/1 "Fraunces", serif;
  color: var(--ivory); opacity: .045; pointer-events: none;
}}
h2 {{
  font: 600 2rem/1.2 "Fraunces", serif;
  color: var(--ivory); margin: 0 0 .4rem;
}}
.lede {{ color: var(--ink-dim); font-size: 1.02rem; max-width: 60ch;
        margin-top: 0; font-style: italic; }}
h3 {{ font: 600 1.25rem/1.3 "Fraunces", serif; color: var(--ivory); }}
p {{ max-width: 72ch; }}
ul {{ max-width: 70ch; padding-left: 1.2rem; }}
li {{ margin: .3rem 0; }}
li::marker {{ color: var(--brass); }}
strong {{ color: var(--ivory); font-weight: 600; }}
/* code: a whisper, not a chip */
code {{
  font: 500 .88em/1 var(--mono);
  color: var(--sage);
  background: none; padding: 0;
}}
blockquote.query {{
  font: italic 500 1.25rem/1.5 "Fraunces", serif;
  color: var(--ivory);
  border-left: 3px solid var(--brass);
  margin: 1.4rem 0; padding: .4rem 0 .4rem 1.2rem; max-width: 60ch;
}}
/* ── tool cards ── */
.tool {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1.5rem 1.8rem 1.2rem;
  margin: 1.4rem 0;
}}
.tool header {{
  display: flex; align-items: baseline; gap: .9rem;
  border-bottom: 1px solid var(--line);
  padding-bottom: .8rem; margin-bottom: .9rem;
}}
.tnum {{ font: 600 .9rem/1 var(--mono); color: var(--brass-dim); }}
.tool h3 {{ margin: 0; font: 500 1.3rem/1 var(--mono); color: var(--ivory); letter-spacing: -.02em; }}
.badge {{
  margin-left: auto;
  font: 500 .66rem/1 var(--mono); letter-spacing: .14em; text-transform: uppercase;
  padding: .35em .7em; border-radius: 99px; border: 1px solid;
}}
.badge.local {{ color: var(--sage); border-color: color-mix(in srgb, var(--sage) 45%, transparent); }}
.badge.llm {{ color: var(--brass); border-color: color-mix(in srgb, var(--brass) 45%, transparent); }}
.badge.file {{ color: var(--rust); border-color: color-mix(in srgb, var(--rust) 45%, transparent); }}
.tfield {{ margin: 1rem 0; }}
.tfield h4 {{
  font: 500 .68rem/1 var(--mono); letter-spacing: .22em; text-transform: uppercase;
  color: var(--brass-dim); margin: 0 0 .35rem;
}}
.tfield p {{ margin: .35rem 0; }}
.tfield.fail {{ border-left: 2px solid var(--rust); padding-left: 1rem; }}
.tfield.fail h4 {{ color: var(--rust); }}
/* params table */
table.params {{
  width: 100%; border-collapse: collapse; margin: .5rem 0 .8rem;
  font-size: .92rem;
}}
table.params th {{
  font: 500 .65rem/1 var(--mono); letter-spacing: .18em; text-transform: uppercase;
  color: var(--ink-dim); text-align: left;
  padding: .4rem .8rem .4rem 0; border-bottom: 1px solid var(--line);
}}
table.params td {{ padding: .5rem .8rem .5rem 0; border-bottom: 1px solid color-mix(in srgb, var(--line) 50%, transparent); vertical-align: top; }}
td.pname {{ font: 500 .86rem/1.5 var(--mono); color: var(--ivory); white-space: nowrap; }}
td.ptype {{ font: 400 .8rem/1.6 var(--mono); color: var(--brass-dim); white-space: nowrap; }}
details.datanotes {{
  margin: 1.1rem 0 .3rem; border: 1px dashed var(--line);
  border-radius: 8px; padding: .7rem 1.1rem;
  background: var(--bg-deep); font-size: .92rem;
}}
details.datanotes summary {{
  cursor: pointer; color: var(--ink-dim);
  font: 500 .78rem/1.4 var(--mono); letter-spacing: .06em;
}}
details.datanotes h4 {{ color: var(--brass-dim); font: 600 .9rem/1.4 "Source Sans 3", sans-serif; margin: .9rem 0 .2rem; }}
details.datanotes p {{ margin: .2rem 0; color: var(--ink-dim); }}
/* ── error cards ── */
.egrid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 1rem; margin-top: 1.4rem; }}
.ecard {{
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 1.1rem 1.3rem; font-size: .93rem;
}}
.ecard.soft {{ border-top: 3px solid var(--brass); }}
.ecard.hard {{ border-top: 3px solid var(--rust); }}
.ehead {{ display: flex; align-items: center; justify-content: space-between; gap: .8rem; }}
.ecomp {{ font: 500 .85rem/1.4 var(--mono); color: var(--ivory); }}
.etag {{ font: 500 .6rem/1 var(--mono); letter-spacing: .12em; text-transform: uppercase; }}
.ecard.soft .etag {{ color: var(--brass); }}
.ecard.hard .etag {{ color: var(--rust); }}
.emode {{ color: var(--ivory); font-weight: 600; margin: .55rem 0 .3rem; }}
.eresp {{ color: var(--ink-dim); margin: 0; }}
/* ── stretch cards ── */
.sgrid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 1rem; margin-top: 1.2rem; }}
.scard {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 1.1rem 1.3rem; font-size: .94rem; }}
.shead {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }}
.scard h4 {{ margin: 0; font: 600 1.05rem/1.3 "Fraunces", serif; color: var(--ivory); }}
.pts {{ font: 600 .8rem/1 var(--mono); color: var(--brass); white-space: nowrap; }}
.scard p {{ color: var(--ink-dim); margin: .5rem 0 0; }}
/* ── diagrams ── */
figure.diagram {{ margin: 1.6rem 0; }}
figure.diagram figcaption {{
  font: 500 .7rem/1 var(--mono); letter-spacing: .2em; text-transform: uppercase;
  color: var(--brass-dim); margin-bottom: .6rem;
}}
pre.mermaid {{
  background: var(--bg-deep); border: 1px solid var(--line);
  border-radius: 10px; padding: 1.2rem; text-align: center; overflow-x: auto;
}}
img {{ max-width: 100%; border-radius: 8px; }}
/* ── milestones ── */
.milestone {{ border-left: 2px solid var(--line); padding-left: 1.4rem; margin: 1.6rem 0; }}
.milestone h3 {{ margin: 0 0 .5rem; }}
/* ── timeline ── */
ol.timeline {{ list-style: none; padding: 0; margin: 1.6rem 0; position: relative; }}
ol.timeline::before {{
  content: ""; position: absolute; left: 17px; top: 8px; bottom: 8px;
  width: 1px; background: var(--line);
}}
ol.timeline li {{ display: flex; gap: 1.3rem; margin: 1.3rem 0; position: relative; }}
.tmark {{
  flex: 0 0 36px; height: 36px; border-radius: 50%;
  background: var(--panel-2); border: 1px solid var(--line);
  display: grid; place-items: center;
  font: 600 .85rem/1 var(--mono); color: var(--brass);
  position: relative; z-index: 1;
}}
ol.timeline h4 {{
  margin: .35rem 0 .25rem;
  font: 500 .7rem/1 var(--mono); letter-spacing: .22em; text-transform: uppercase;
  color: var(--brass-dim);
}}
ol.timeline p {{ margin: .25rem 0; font-size: .96rem; }}
/* ── responsive + entrance ── */
@media (max-width: 1000px) {{
  .wrap {{ grid-template-columns: 1fr; gap: 0; }}
  nav.toc {{ position: static; flex-direction: row; flex-wrap: wrap; padding: 1rem 0 0; }}
  nav.toc a {{ border-left: none; border-bottom: 2px solid var(--line); }}
  section::before {{ display: none; }}
}}
@keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
.masthead .in > * {{ animation: rise .6s cubic-bezier(.2,.7,.3,1) backwards; }}
.masthead .in > *:nth-child(2) {{ animation-delay: .08s; }}
.masthead .in > *:nth-child(3) {{ animation-delay: .16s; }}
.masthead .in > *:nth-child(4) {{ animation-delay: .24s; }}
</style>
</head>
<body>
<header class="masthead">
  <div class="in">
    <div class="kicker">AI201 · Project 2 · Planning Specification</div>
    <h1>FitFindr <em>agent spec</em></h1>
    <p class="sub">A multi-tool thrifting agent: a ReAct-style LLM router bounded by
    hard code guards, six tools, one session dict as the single source of truth.
    Written before implementation. The spec is the prompt.</p>
    <div class="meta">
      <div><b>6 tools</b>3 required · 3 stretch</div>
      <div><b>llama-3.3-70b</b>via Groq</div>
      <div><b>+7 stretch pts</b>all committed</div>
      <div><b>router + guards</b>LLM proposes, code disposes</div>
    </div>
  </div>
</header>
<div class="wrap">
<nav class="toc">{toc_html}</nav>
<main>
{body}
</main>
</div>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{
    startOnLoad: true, theme: "base",
    themeVariables: {{
      darkMode: true, background: "#232629",
      primaryColor: "#313539", primaryTextColor: "#d9dcdf",
      primaryBorderColor: "#43484e", lineColor: "#8a8f96",
      secondaryColor: "#383d42", tertiaryColor: "#2a2d31",
      fontFamily: "IBM Plex Mono, monospace", fontSize: "14px"
    }}
  }});
</script>
</body>
</html>
"""

(ROOT / "planning.html").write_text(page)
print("planning.html written:", len(page), "bytes")
print("tools rendered:", tools_html.count('<article class="tool"'))
print("error cards:", errors_html.count('<div class="ecard'))
print("stretch cards:", stretch_html.count('<div class="scard"'))
print("timeline items:", timeline.count("<li>"))
print("mermaid diagrams:", len(mermaids))

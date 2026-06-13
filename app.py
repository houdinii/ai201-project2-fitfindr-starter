"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── query handler ─────────────────────────────────────────────────────────────

def _format_listing_panel(item: dict) -> str:
    """Format the selected listing into readable lines for the first panel."""
    lines = [
        item["title"],
        f"${item['price']:.2f} on {item['platform']}",
        f"Size {item['size']} - condition {item['condition']}",
        f"Category: {item['category']}",
        f"Style: {', '.join(item['style_tags'])}",
    ]
    if item.get("brand"):
        lines.append(f"Brand: {item['brand']}")
    lines.append("")
    lines.append(item["description"])
    return "\n".join(lines)


def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:      The text the user typed into the search box.
        wardrobe_choice: Either "Example wardrobe" or "Empty wardrobe (new user)".

    Returns:
        A tuple of three strings (listing_text, outfit_suggestion, fit_card),
        one per output panel.

    Maps the session dict from run_agent() onto the panels. Retry notices
    (the "searched again without the size filter" messages from the stretch
    retry logic) are surfaced above the listing. Partial results are kept
    on error, so a caption failure still shows the outfit, per the Error
    Handling table in planning.md.
    """
    if not user_query or not user_query.strip():
        return ("Please describe what you're looking for, such as "
                "'vintage graphic tee under $30, size M'.", "", "")

    wardrobe = (
        get_empty_wardrobe()
        if wardrobe_choice == "Empty wardrobe (new user)"
        else get_example_wardrobe()
    )

    session = run_agent(query=user_query.strip(), wardrobe=wardrobe)

    notice_block = ""
    if session["notices"]:
        notice_block = (
            "Note:\n" + "\n".join(f"- {n}" for n in session["notices"]) + "\n\n"
        )

    item = session["selected_item"]
    outfit = session["outfit_suggestion"] or ""
    fit_card = session["fit_card"] or ""

    if session["error"]:
        # Nothing found: the error is the whole story, panel 1 carries it.
        if item is None:
            return (notice_block + session["error"], "", "")
        # Partial result: an item (and maybe an outfit) survived. Show the
        # error as a banner but keep the work the user already got.
        listing_text = (
            notice_block
            + f"[!] {session['error']}\n\n"
            + _format_listing_panel(item)
        )
        return listing_text, outfit, fit_card

    return notice_block + _format_listing_panel(item), outfit, fit_card


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()

# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## Testing

All automated tests live in `tests/` and run with pytest (configured via `pytest.ini`, no path setup needed):

```bash
pytest                                  # everything
pytest -v                               # everything, one line per test
pytest tests/test_tools.py              # one file
pytest tests/test_tools.py -k empty     # tests matching a keyword
```

Current coverage: `tests/test_data_loader.py` smoke-tests the data layer (40 listings load with all fields, example and empty wardrobes load). `tests/test_tools.py` holds the per-tool tests, at least one per failure mode, added as each tool is implemented.

Note: tests for the pure-local tools (`search_listings`, `compare_prices`) run offline. Tests touching the LLM tools need `GROQ_API_KEY` in `.env`.

**Manual failure drills** (each must return a message, never a traceback):

```bash
# zero results, no exception
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"

# empty wardrobe, still useful output
python -c "
from tools import search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(suggest_outfit(results[0], get_empty_wardrobe()))
"

# empty outfit string, error message not exception
python -c "
from tools import search_listings, create_fit_card
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(create_fit_card('', results[0]))
"
```

**End-to-end:** `python agent.py` runs the built-in happy path plus the no-results path. `python app.py` serves the Gradio interface (URL prints in the terminal).

## Debug Logging

Set `FITFINDR_LOG=1` to stream a one-line trace of every LLM call, tool call, and file read/write to stderr, each timestamped to the millisecond. It is off by default, so pytest and normal runs stay quiet, and it is gated by `utils/trace.py`. Turn it on to watch a run unfold or to debug a misbehaving query:

```bash
FITFINDR_LOG=1 python app.py
FITFINDR_LOG=1 python agent.py
```

A healthy happy path reads top to bottom like this:

```
21:51:04.830 session START query='vintage graphic tee under $30' wardrobe=10 items
21:51:04.830 file read  data/style_profile.json (none, new profile)
21:51:04.867 llm  call  router iter 1 (msgs=2, temp=0.2)
21:51:05.398 llm  resp  router iter 1 (531ms) -> ['search_listings']
21:51:05.398 tool call  search_listings args={'description': 'vintage graphic tee', 'max_price': 30}
21:51:05.398 file read  data/listings.json (40 listings)
21:51:05.399 tool ret   search_listings -> 20 result(s), best match first: lst_002 ...
21:51:06.001 llm  resp  router iter 3 (253ms) -> ['suggest_outfit']
21:51:07.069 llm  resp  suggest_outfit (1054ms, 855 chars)
21:51:07.983 tool ret   create_fit_card -> Fit card created. The interaction is complete.
21:51:07.983 session END fit_card (iters=4, tools=4)
```

Long values are truncated to one line, and secrets (the API key, `.env`) are never logged. See `HUMAN_TEST.md` for a poll of queries to run with logging on.

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

---

`item_id` is a foreign key and the session is the database. In production those lookups would be real DB calls, here they're dict lookups against `session`. Same architecture, smaller hardware.
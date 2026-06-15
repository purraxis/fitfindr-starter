# FitFindr

FitFindr is a small Gradio shopping assistant for mock secondhand clothing
listings. A user describes what they want, optionally includes a size and budget,
and the app searches `data/listings.json`. If a listing is found, the agent
selects the top match, asks the LLM for an outfit idea using the user's wardrobe,
and asks the LLM for a short shareable fit card.

The current implementation is intentionally simple: listing search is local and
deterministic, while outfit and caption generation use Groq through
`GROQ_API_KEY`.

## Tool Inventory

### `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`

Purpose: search the mock listings dataset.

Inputs:
- `description`: search terms such as `"vintage graphic tee"`.
- `size`: optional size filter such as `"M"` or `"XXS"`.
- `max_price`: optional inclusive price ceiling.

Output:
- A list of matching listing dictionaries, sorted by keyword overlap and then
  lower price.
- Returns `[]` when no listing matches.

Implementation notes:
- Uses `load_listings()` from `utils/data_loader.py`.
- Filters by `max_price` before scoring.
- Filters by size when a size is provided.
- Scores keyword overlap against title, description, category, brand,
  style tags, and colors.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

Purpose: generate 1-2 outfit ideas for the selected listing.

Inputs:
- `new_item`: the listing selected from search results.
- `wardrobe`: a dict with an `items` list, usually from
  `get_example_wardrobe()` or `get_empty_wardrobe()`.

Output:
- A non-empty outfit suggestion string when the Groq call succeeds.
- If `new_item` is missing, returns a clear error string instead of raising.

Implementation notes:
- If the wardrobe has items, the prompt includes named wardrobe pieces.
- If the wardrobe is empty, the prompt asks for general styling advice.

### `create_fit_card(outfit: str, new_item: dict) -> str`

Purpose: generate a short social-media-style outfit caption.

Inputs:
- `outfit`: the outfit suggestion returned by `suggest_outfit()`.
- `new_item`: the selected listing.

Output:
- A 2-4 sentence caption string when the Groq call succeeds.
- If `outfit` is empty, returns a descriptive error string.
- If `new_item` is missing, returns a descriptive error string.

## Planning Loop

The planning loop lives in `run_agent(query: str, wardrobe: dict) -> dict` in
`agent.py`.

Actual conditional logic:

1. Initialize a session dictionary with `_new_session(query, wardrobe)`.
2. Parse the query with `_parse_query()`:
   - extracts `max_price` from text like `under $30` or `$30`,
   - extracts `size` from text like `size M`,
   - removes those fragments from the search description.
3. Store parsed values in `session["parsed"]`.
4. Call `search_listings(description, size, max_price)`.
5. Store the returned list in `session["search_results"]`.
6. If the list is empty:
   - set `session["error"]`,
   - leave `selected_item`, `outfit_suggestion`, and `fit_card` as `None`,
   - return the session immediately.
7. If results exist:
   - store `results[0]` in `session["selected_item"]`,
   - call `suggest_outfit(session["selected_item"], wardrobe)`,
   - store the response in `session["outfit_suggestion"]`.
8. If the outfit suggestion is empty:
   - set `session["error"]`,
   - return early.
9. Otherwise call `create_fit_card(session["outfit_suggestion"], session["selected_item"])`.
10. Store the caption in `session["fit_card"]`.
11. Return the completed session.

The Gradio app also supports labeled multiline input by normalizing it in
`app.py` before calling `run_agent()`. For example:

```text
description: designer ballgown
size: XXS
max price: 5
```

is converted to:

```text
designer ballgown size XXS under $5
```

## State Management

The session dictionary is the single state object passed through the workflow.
It contains:

- `query`: the original query sent to `run_agent()`.
- `parsed`: a dict with `description`, `size`, and `max_price`.
- `search_results`: all matching listings from `search_listings()`.
- `selected_item`: the first listing in `search_results`, or `None`.
- `wardrobe`: the wardrobe dict passed into the agent.
- `outfit_suggestion`: the string returned by `suggest_outfit()`, or `None`.
- `fit_card`: the string returned by `create_fit_card()`, or `None`.
- `error`: a user-facing error message, or `None`.

Data passes between tools through this session:

1. `search_results` is stored after search.
2. `selected_item` is copied from the top result.
3. `selected_item` and `wardrobe` are passed into `suggest_outfit()`.
4. `outfit_suggestion` and `selected_item` are passed into `create_fit_card()`.

## Error Handling

`search_listings()`:
- Failure mode: no listings match.
- Strategy: return `[]`.
- Example: `"designer ballgown size XXS under $5"` produces no results, so
  `run_agent()` sets `session["error"]` to:
  `"No listings found. Try a broader description, a higher budget, or removing the size filter."`

`suggest_outfit()`:
- Failure mode: no selected item is provided.
- Strategy: return `"I can't suggest an outfit because no item was selected."`
- Empty wardrobes are not treated as failure; the LLM is prompted for general
  styling advice.

`create_fit_card()`:
- Failure mode: empty outfit string.
- Strategy: return `"Cannot create a fit card because the outfit suggestion is empty."`
- Failure mode: no selected item.
- Strategy: return `"Cannot create a fit card because no selected item was provided."`

`run_agent()`:
- Does not call `suggest_outfit()` or `create_fit_card()` when search returns
  `[]`.
- Returns early with `session["error"]` populated.

`handle_query()`:
- If the user submits an empty query, returns `"Please enter what you're looking for."`
- If `session["error"]` exists, displays the error in the listing panel and
  leaves outfit and fit card empty.

## Spec Reflection

One way `planning.md` helped: it defined the required tool order and early-return
behavior. The implementation follows that plan by searching first, storing
results in session state, and stopping before outfit/card generation when no
listing is found.

One divergence from the spec: `planning.md` describes top-level session fields
like `session["size"]` and `session["max_price"]`, but the implemented starter
session already had `session["parsed"]`. The final code stores
`description`, `size`, and `max_price` inside `session["parsed"]` instead of
adding separate top-level fields.

Another practical divergence: labeled multiline input is handled in `app.py` by
normalizing it into the natural-language format expected by `agent.py`, rather
than changing the agent parser to accept every UI input format directly.

## AI Usage

AI was used to draft and revise the tool implementations against the
`planning.md` tool specs. For example, `search_listings()` was implemented as a
local keyword search, then verified with manual tests for a normal query, an
impossible query, and a price-filtered query.

AI was also used to implement and verify the planning loop. The early-return
behavior was checked by monkeypatching `search_listings()` to return `[]` and
confirming that `suggest_outfit()` and `create_fit_card()` were not called.

AI-assisted test creation added `tests/test_tools.py` with pytest coverage for
the search behavior, empty wardrobe outfit generation, and the empty-outfit fit
card error path. The LLM-backed test uses a fake Groq client so tests do not
depend on exact LLM wording or network access.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_key_here
```

## Run The Project

Run the command-line agent smoke test:

```bash
python agent.py
```

Run the Gradio app:

```bash
python app.py
```

If Gradio's default port is unavailable, set a port:

```bash
GRADIO_SERVER_NAME=127.0.0.1 GRADIO_SERVER_PORT=18060 python app.py
```

Then open the local URL shown in the terminal.

Example happy-path browser input:

```text
vintage graphic tee under $30
```

Example no-results browser input:

```text
description: designer ballgown
size: XXS
max price: 5
```

## Run Tests

Run the pytest suite:

```bash
pytest tests/
```

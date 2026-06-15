# FitFindr — planning.md

FitFindr is a multi-tool shopping assistant that helps users find secondhand clothing and figure out how to style it. The agent first searches the mock listings dataset using the user's item description, size, and budget. If it finds a match, it stores the selected item in session state, uses the user's wardrobe to suggest an outfit, then generates a short shareable fit card. If a tool fails or returns no useful result, the agent gives a clear message and either stops or uses fallback behavior instead of crashing.
---

## Tools


### Tool 1: search_listings

**What it does:**
Search the mock secondhand listings dataset for items matching the user's requested description, size, and maximum price.

**Input parameters:**
- description (str): The clothing item or style the user is looking for, such as "vintage graphic tee".
- size (str or None): The user's desired size, such as "M". If None, size is not used as a strict filter.
- max_price (float or None): The maximum price the user wants to pay. If None, price is not used as a strict filter.


**What it returns:**
- list[dict]: A list of matching listing dictionaries.
- If no listings match, returns an empty list [].

**What happens if it fails or returns nothing:**
If no results are found, the tool returns [] instead of raising an exception. The agent tells the user that no matching listings were found and suggests trying a broader description, larger budget, or no size filter.

---

### Tool 2: suggest_outfit

**What it does:**
Suggests one or more outfit ideas using the selected secondhand listing and the user's current wardrobe. It explains how the user can wear the new item with pieces they already own.

**Input parameters:**
- `new_item` (dict): The selected listing returned from `search_listings`. This is the item the agent will style.
- `wardrobe` (dict): The user's wardrobe data, usually loaded from `get_example_wardrobe()` or `get_empty_wardrobe()`.

**What it returns:**
- str: A natural-language outfit suggestion that explains how to style the selected item.
- The suggestion should include specific styling details such as clothing pairings, shoes, accessories, colors, proportions, or overall vibe.

**What happens if it fails or returns nothing:**
If the wardrobe is empty or minimal, the tool still returns useful general styling advice based on the selected item. It should not crash or return an empty string. If no `new_item` is provided, the tool returns a clear error message saying that an outfit cannot be suggested because no item was selected.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable outfit caption based on the outfit suggestion and selected secondhand item. The output should sound like something someone might post on social media, not like a formal product description.

**Input parameters:**
- `outfit` (str): The outfit suggestion created by `suggest_outfit`.
- `new_item` (dict): The selected listing being styled.

**What it returns:**
- str: A short social-media-style fit card or caption.
- The caption should mention the item, the styling idea, and the general vibe of the outfit.

**What happens if it fails or returns nothing:**
If the `outfit` input is empty, missing, or invalid, the tool returns a descriptive error message string instead of crashing. If `new_item` is missing, it returns a clear message saying that the fit card cannot be created because no selected item was provided.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

The agent uses a conditional planning loop based on the current session state and the output of each tool. It does not call all tools blindly. Each tool call depends on whether the previous tool returned useful data.

1. Start with the user's item description, size, max price, and wardrobe.
2. Create a session dictionary with default fields:
   - `session["query"]`
   - `session["size"]`
   - `session["max_price"]`
   - `session["search_results"]`
   - `session["selected_item"]`
   - `session["outfit_suggestion"]`
   - `session["fit_card"]`
   - `session["error"]`
3. Call `search_listings(description, size, max_price)`.
4. Store the returned list in `session["search_results"]`.
5. Check whether the search returned results:
   - If `results == []`:
     - Set `session["error"]` to a helpful message, such as: `"No listings found. Try a broader description, a higher budget, or removing the size filter."`
     - Leave `session["selected_item"]`, `session["outfit_suggestion"]`, and `session["fit_card"]` as `None`.
     - Return the session early.
   - If results exist:
     - Select the top result using `results[0]`.
     - Store it in `session["selected_item"]`.
6. Call `suggest_outfit(session["selected_item"], wardrobe)`.
7. Store the returned string in `session["outfit_suggestion"]`.
8. Check whether the outfit suggestion is valid:
   - If the outfit suggestion is empty or invalid:
     - Set `session["error"]` to a helpful message.
     - Return the session early.
   - If the outfit suggestion is valid:
     - Continue to the fit card step.
9. Call `create_fit_card(session["outfit_suggestion"], session["selected_item"])`.
10. Store the returned caption in `session["fit_card"]`.
11. Return the completed session.

The planning loop is finished when either:
- the agent hits an error path and returns early, or
- all three required tools run successfully and `session["fit_card"]` is created.
---

## State Management

**How does information from one tool get passed to the next?**

The agent stores intermediate outputs in a session dictionary. This allows information from one tool call to be reused by later tools without asking the user to re-enter it.

Session fields:
- `session["query"]`: The original item description from the user.
- `session["size"]`: The requested size.
- `session["max_price"]`: The user's maximum budget.
- `session["search_results"]`: The full list of listings returned by `search_listings`.
- `session["selected_item"]`: The top listing selected from `search_results`.
- `session["outfit_suggestion"]`: The styling suggestion returned by `suggest_outfit`.
- `session["fit_card"]`: The final shareable caption returned by `create_fit_card`.
- `session["error"]`: A user-facing error message if something fails.

Data flow:
1. `search_listings` returns a list of matching listings.
2. The agent stores the list in `session["search_results"]`.
3. The agent selects `results[0]` and stores it in `session["selected_item"]`.
4. `session["selected_item"]` is passed directly into `suggest_outfit`.
5. The returned outfit suggestion is stored in `session["outfit_suggestion"]`.
6. `session["outfit_suggestion"]` and `session["selected_item"]` are passed into `create_fit_card`.
7. The final caption is stored in `session["fit_card"]`.

This state management makes the workflow continuous. The user does not need to copy the found item into the outfit tool or copy the outfit suggestion into the fit card tool.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | The tool returns `[]`. The agent sets `session["error"]` to a message telling the user no listings were found and suggests broadening the description, raising the budget, or removing the size filter. The agent returns early and does not call the next tools. |
| suggest_outfit | Wardrobe is empty | The tool returns general styling advice based on the selected item instead of crashing. The agent stores the suggestion in `session["outfit_suggestion"]` and continues to `create_fit_card` if the suggestion is valid. |
| suggest_outfit | No selected item is provided | The tool returns a clear error message saying it cannot suggest an outfit because no item was selected. The agent stores the error and returns early. |
| create_fit_card | Outfit input is missing or incomplete | The tool returns a descriptive error message instead of raising an exception. The agent stores the message and avoids crashing the app. |
| create_fit_card | Selected item is missing | The tool returns a clear message saying it cannot create a fit card because no item was selected. |

---

## Architecture

```text
User input
(description, size, max_price, wardrobe)
        |
        v
Planning Loop / run_agent()
        |
        v
Initialize session dictionary
        |
        v
search_listings(description, size, max_price)
        |
        |-- results == []
        |       |
        |       v
        |   session["search_results"] = []
        |   session["error"] = "No listings found..."
        |       |
        |       v
        |   Return session early
        |
        |-- results found
                |
                v
        session["search_results"] = results
        session["selected_item"] = results[0]
                |
                v
suggest_outfit(session["selected_item"], wardrobe)
                |
                |-- outfit invalid or empty
                |       |
                |       v
                |   session["error"] = "Could not generate outfit suggestion..."
                |       |
                |       v
                |   Return session early
                |
                |-- outfit valid
                        |
                        v
        session["outfit_suggestion"] = outfit_suggestion
                        |
                        v
create_fit_card(session["outfit_suggestion"], session["selected_item"])
                        |
                        v
        session["fit_card"] = fit_card
                        |
                        v
Return completed session
```
---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

I will use ChatGPT to help implement each tool one at a time. For each tool, I will give ChatGPT the matching tool spec from this `planning.md`, including the input parameters, return value, and failure behavior.

For `search_listings`, I will give ChatGPT the Tool 1 spec and ask it to implement the function in `tools.py` using `load_listings()` from `utils/data_loader.py`. I will verify that the generated code filters by description, size, and max price, and that it returns an empty list instead of crashing when there are no matches. I will test it with at least three queries: one normal query, one impossible query, and one price-filter query.

For `suggest_outfit`, I will give ChatGPT the Tool 2 spec and ask it to implement the function using the selected item and wardrobe data. I will verify that it works with both `get_example_wardrobe()` and `get_empty_wardrobe()`. I will check that the empty wardrobe case still returns useful styling advice.

For `create_fit_card`, I will give ChatGPT the Tool 3 spec and ask it to implement a caption generator that takes `outfit` and `new_item` as inputs. I will verify that it returns a short caption and that it returns an error message instead of crashing when the outfit string is empty.

**Milestone 4 — Planning loop and state management:**

I will use ChatGPT to help implement the planning loop in `agent.py`. I will give it the Planning Loop section, State Management section, and Architecture diagram from this `planning.md`.

I expect it to produce code for `run_agent()` that:
- initializes a session dictionary,
- calls `search_listings` first,
- checks whether search results are empty,
- returns early if no listings are found,
- stores the selected item in session state,
- passes the selected item into `suggest_outfit`,
- stores the outfit suggestion,
- passes the outfit suggestion and selected item into `create_fit_card`,
- stores the final fit card,
- returns the completed session.

I will verify the output by checking that the agent does not call `suggest_outfit` or `create_fit_card` when `search_listings` returns an empty list. I will also print the session dictionary during testing to confirm that `selected_item`, `outfit_suggestion`, and `fit_card` are being stored and passed correctly.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent reads the user's request and identifies the key search inputs:
- description: `"vintage graphic tee"`
- size: `None` because the user did not give a specific size
- max_price: `30.0`
- wardrobe: the user's wardrobe details from the request, including baggy jeans and chunky sneakers

The first tool called is:

```python
search_listings("vintage graphic tee", size=None, max_price=30.0)

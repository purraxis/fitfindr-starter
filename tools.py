"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


_MODEL = "llama-3.1-8b-instant"


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    query_terms = set(re.findall(r"[a-z0-9]+", description.lower()))

    matches = []
    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue

        if size is not None:
            requested_size = size.strip().lower()
            listing_size = listing["size"].lower()
            if requested_size and requested_size not in listing_size:
                continue

        searchable_text = " ".join(
            [
                listing["title"],
                listing["description"],
                listing["category"],
                listing["brand"] or "",
                " ".join(listing["style_tags"]),
                " ".join(listing["colors"]),
            ]
        ).lower()
        listing_terms = set(re.findall(r"[a-z0-9]+", searchable_text))
        score = len(query_terms & listing_terms)

        if score > 0:
            matches.append((score, listing["price"], listing))

    matches.sort(key=lambda item: (-item[0], item[1]))
    return [listing for _, _, listing in matches]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    if not new_item:
        return "I can't suggest an outfit because no item was selected."

    client = _get_groq_client()
    wardrobe_items = wardrobe.get("items", []) if wardrobe else []

    item_summary = (
        f"{new_item.get('title', 'Selected item')} "
        f"({new_item.get('category', 'item')}, size {new_item.get('size', 'unknown')}, "
        f"colors: {', '.join(new_item.get('colors', [])) or 'unknown'}, "
        f"style tags: {', '.join(new_item.get('style_tags', [])) or 'none'})"
    )

    if wardrobe_items:
        wardrobe_summary = "\n".join(
            "- {name} ({category}; colors: {colors}; style: {tags}; notes: {notes})".format(
                name=item.get("name", "Unnamed item"),
                category=item.get("category", "unknown"),
                colors=", ".join(item.get("colors", [])) or "unknown",
                tags=", ".join(item.get("style_tags", [])) or "none",
                notes=item.get("notes") or "none",
            )
            for item in wardrobe_items
        )
        prompt = (
            "Suggest 1-2 complete outfits using this secondhand find and named "
            "pieces from the user's wardrobe. Include specific pairings, shoes, "
            "accessories, colors, proportions, and the overall vibe.\n\n"
            f"New item: {item_summary}\n\n"
            f"Wardrobe:\n{wardrobe_summary}"
        )
    else:
        prompt = (
            "Suggest 1-2 useful outfit ideas for this secondhand find. The user "
            "has not entered wardrobe items yet, so give general styling advice "
            "with specific clothing pairings, shoes, accessories, colors, "
            "proportions, and the overall vibe.\n\n"
            f"New item: {item_summary}"
        )

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a concise personal stylist for secondhand clothing.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Cannot create a fit card because the outfit suggestion is empty."
    if not new_item:
        return "Cannot create a fit card because no selected item was provided."

    client = _get_groq_client()
    prompt = (
        "Write a casual 2-4 sentence social media outfit caption. Make it sound "
        "like a real OOTD post, not a product description. Mention the item "
        "name, price, and platform naturally once each, and capture the outfit "
        "vibe in specific terms.\n\n"
        f"Item: {new_item.get('title', 'Selected item')}\n"
        f"Price: ${new_item.get('price', 'unknown')}\n"
        f"Platform: {new_item.get('platform', 'unknown')}\n"
        f"Outfit idea: {outfit.strip()}"
    )

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You write short, authentic outfit captions.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,
        max_tokens=180,
    )
    return response.choices[0].message.content.strip()

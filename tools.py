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
    try:
        listings = load_listings()
    except Exception:
        return []

    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]

    if size is not None:
        size_lower = size.lower()
        listings = [l for l in listings if size_lower in l["size"].lower()]

    tokens = set(re.sub(r"[^\w\s]", "", description.lower()).split())
    if not tokens:
        return []

    scored = []
    for listing in listings:
        blob = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            listing["brand"] or "",
        ]).lower()
        score = sum(1 for t in tokens if t in blob)
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [listing for _, listing in scored]


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
    items = wardrobe.get("items", [])

    system_prompt = (
        "You are a concise personal stylist who gives actionable, specific fashion advice. "
        "Respond in 2–4 sentences."
    )

    item_line = (
        f"- Name: {new_item.get('title', 'Unknown item')}\n"
        f"- Category: {new_item.get('category', '')}\n"
        f"- Colors: {', '.join(new_item.get('colors', []))}\n"
        f"- Style: {', '.join(new_item.get('style_tags', []))}"
    )

    if not items:
        user_prompt = (
            f"I just found this thrifted item:\n{item_line}\n\n"
            "I don't have a wardrobe on file yet. Give me 1–2 versatile outfit ideas — "
            "suggest the types of silhouettes, textures, and complementary colors that "
            "would pair beautifully with this piece."
        )
    else:
        wardrobe_lines = []
        for piece in items:
            line = (
                f"- {piece.get('name', '')} ({piece.get('category', '')}) "
                f"| Colors: {', '.join(piece.get('colors', []))} "
                f"| Style: {', '.join(piece.get('style_tags', []))}"
            )
            if piece.get("notes"):
                line += f" | Notes: {piece['notes']}"
            wardrobe_lines.append(line)

        user_prompt = (
            f"I just found this thrifted item:\n{item_line}\n\n"
            f"Here is my current wardrobe:\n{chr(10).join(wardrobe_lines)}\n\n"
            "Suggest 1–2 specific outfit combinations using the new item and pieces from "
            "my wardrobe. Name the exact wardrobe pieces you're pairing it with."
        )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=400,
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
    if not outfit.strip():
        return (
            "Unable to generate your Fit Card because outfit data was missing. "
            "Please double-check your search and try again!"
        )

    title = new_item.get("title", "this thrifted piece")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "a thrift platform")

    system_prompt = (
        "You are a fashion-forward Gen-Z thrifter writing casual, authentic OOTD captions "
        "for Instagram and TikTok. Write in first person. Sound real, not like an ad. "
        "Use specific, vivid language about the vibe — not generic phrases."
    )

    user_prompt = (
        f"Write a 2–4 sentence Instagram/TikTok caption for this outfit:\n\n"
        f"Outfit: {outfit}\n"
        f"Item: {title}\n"
        f"Price: ${price}\n"
        f"Found on: {platform}\n\n"
        f"Rules:\n"
        f'- Mention "{title}" naturally once.\n'
        f"- Mention the price (${price}) naturally once.\n"
        f"- Mention the platform ({platform}) naturally once.\n"
        f"- Do NOT use hashtags.\n"
        f"- Sound like a real person posting their OOTD, not a product description."
    )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()

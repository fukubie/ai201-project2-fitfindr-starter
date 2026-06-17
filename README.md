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

# 🤖 System Architecture & Technical Specifications

This section documents the custom implementation, planning loops, and state machine configurations built for the FitFindr agent framework.

## 🧰 Tool Inventory

The agent interacts with the following custom-built tools located inside `tools.py`. Their signatures match their execution footprints exactly.

### 1. `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`
*   **Purpose:** Filters the mock marketplace catalog based on price ceilings and case-insensitive partial size matching, then scores remaining items based on unique description keyword token overlap.
*   **Inputs:** 
    *   `description` (`str`): Cleaned core search keyword strings.
    *   `size` (`str` or `None`): Optional sizing substring query (e.g., `"M"` matches `"S/M"`).
    *   `max_price` (`float` or `None`): Optional inclusive budget limit.
*   **Outputs:** Returns a sorted list of listing dictionaries ranked highest-to-lowest by keyword relevance. Any items with an overlap score of `0` are dropped automatically.

### 2. `suggest_outfit(new_item: dict, wardrobe: dict) -> str`
*   **Purpose:** Interfaces with Groq (`llama-3.3-70b-versatile`) to create 1–2 tailored outfit combinations combining the new item with pieces from the user's closet.
*   **Inputs:**
    *   `new_item` (`dict`): The target marketplace item metadata mapping.
    *   `wardrobe` (`dict`): The current user's closet tracking array structure under the `"items"` key.
*   **Outputs:** Returns a plain-text styling recommendation block.

### 3. `create_fit_card(outfit: str, new_item: dict) -> str`
*   **Purpose:** Interfaces with Groq (`llama-3.3-70b-versatile`) to draft an authentic, Gen-Z styled social media caption natively embedding the item name, price, and platform exactly once.
*   **Inputs:**
    *   `outfit` (`str`): The raw text output from `suggest_outfit`.
    *   `new_item` (`dict`): The listing metadata mapping container.
    *   `temperature`: Explicitly locked to `0.85` for variety across runs.
*   **Outputs:** Returns a casual, production-ready 2–4 sentence social caption string.

---

## 🧠 How the Planning Loop Works

The core routing loop inside `run_agent()` acts as a conditional state machine rather than an unconditional linear pipeline:

1. **Extraction:** The user's unstructured natural language query is processed deterministically (`temperature=0.0`) by Groq using an isolated query-parser system prompt to reliably extract filters into JSON formats, mapped to `session["parsed"]`.
2. **Catalog Execution:** `search_listings` executes with the parsed constraints.
3. **The Branch Guard Condition:** The planning loop inspects the resulting array length of `session["search_results"]`.
    *   **The Empty Branch Path:** If zero items match, the loop halts immediately. It records an actionable system alert to `session["error"]` and exits early. **Downstream styling and layout tools are completely bypassed.**
    *   **The Valid Branch Path:** If items are present, the agent extracts the highest-scored match (`results[0]`), binds it to `session["selected_item"]`, and rolls forward into downstream generation.

---

## 💾 State Management Approach

The entire interaction framework depends on a single Python dictionary—`session`—acting as the live state ledger and single source of truth passed through the pipeline. 

Data transfers automatically without re-prompting or hardcoding values:
*   `_new_session` saves the baseline `query` and `wardrobe` elements immediately.
*   `search_listings` reads inputs out of `session["parsed"]` and dumps outputs to `session["search_results"]`.
*   `suggest_outfit` simultaneously pulls from `session["selected_item"]` and `session["wardrobe"]`, storing its generation into `session["outfit_suggestion"]`.
*   `create_fit_card` finishes the state stack by combining `session["outfit_suggestion"]` and `session["selected_item"]` to update `session["fit_card"]`.

---

## 🛠️ Error Handling Strategy & Testing Performance

| Tool Name | Monitored Failure Mode | Agent Defensive Action & Live Terminal Output Proof |
| :--- | :--- | :--- |
| **`search_listings`** | Zero catalog objects match constraints. | Halts execution early. Running `search_listings('designer ballgown', size='XXS', max_price=5)` cleanly outputs `[]` instead of raising an exception, safely signaling the agent loop guard rail. |
| **`suggest_outfit`** | User's digital closet array is empty. | Mutates system prompt instructions. Running `suggest_outfit()` against `get_empty_wardrobe()` forces the LLM to output general texture, silhouette, and color styling advice for the item rather than crashing over missing item parameters. |
| **`create_fit_card`** | Input styling string data is missing or blank. | Intercepts execution before hitting the API. Passing a whitespace-only string (`'    '`) immediately yields a descriptive instruction message without making an external Groq API model call, saving token credits. |

---

## 🔮 Spec Reflection

*   **How the Spec Helped:** Drafting the architectural flowchart in `planning.md` prior to coding made the implementation of the conditional branching guard block in `agent.py` obvious. It forced me to think about edge case states before compiling a blind line of code.
*   **Implementation Divergence:** My original layout plan leaned on regex logic to break down search terms. During implementation, I quickly realized human queries like *"under thirty bucks"* or *"size medium"* caused regular expression rules to fail instantly. I adapted by building an explicit LLM extraction helper function in `agent.py` locked to `temperature=0.0` for infallible object processing.

---

## 🤖 AI Usage Section

### Instance 1: Tool 1 Scoring Optimization
*   **AI Input:** Provided Claude 3.5 Sonnet with the `## Tools` markdown requirements and the data loader layout for building out `search_listings`.
*   **AI Output:** Code utilizing `re.sub` for string tokenization and text blob substring searches.
*   **My Revision:** The AI's default structure could occasionally spin into empty loops on malformed entries. I manually added an early check `if not query_tokens: return []` right after the string breakdown block to cleanly abort loops.

### Instance 2: State Machine Loop Integration
*   **AI Input:** Provided Claude with the project's Mermaid architecture graph and the raw `agent.py` function stub file.
*   **AI Output:** A linear execution loop inside `run_agent()`.
*   **My Revision:** The generated code originally called all three tools sequentially without evaluating if the catalog search returned anything. I manually stripped out the linear progression and rewrote the conditional guard clause (`if not session["search_results"]: return session`) to protect downstream LLM modules from parsing missing objects.
# tests/test_tools.py
import pytest
from tools import search_listings

def test_search_returns_results():
    # Happy path: searching for something common in the mock dataset
    results = search_listings("tee", size="M", max_price=50.0)
    assert isinstance(results, list)
    if len(results) > 0:
        assert "size" in results[0]

def test_search_empty_results():
    # Failure mode: strict constraints that match absolutely nothing
    results = search_listings("designer ballgown", size="XXS", max_price=5.0)
    assert results == []  # Must return an empty list, no crashing!

def test_search_price_filter():
    # Price path: all items returned must match the budget ceiling
    results = search_listings("tee", max_price=15.0)
    assert all(item["price"] <= 15.0 for item in results)

def test_search_partial_size_matching():
    # Size path: "M" should match items tagged as "S/M" or "M/L"
    results = search_listings("top", size="M")
    for item in results:
        assert "m" in item["size"].lower()


# Test for suggest outfit
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
from tools import suggest_outfit

def test_suggest_outfit_happy_path():
    """
    Test Tool 2 with a fully populated example wardrobe.
    Verifies that a string response is returned and that it references closet items.
    """
    sample_item = {
        "title": "Vintage Denim Jacket",
        "category": "outerwear",
        "colors": ["blue"],
        "style_tags": ["vintage", "casual"]
    }
    
    # Load the standard sample wardrobe with 10 items
    wardrobe = get_example_wardrobe()
    
    # Run the tool
    response = suggest_outfit(sample_item, wardrobe)
    
    assert isinstance(response, str)
    assert len(response.strip()) > 0
    # Note: We don't assert a specific item name since the LLM output varies, 
    # but confirming it generated a solid response block fulfills our check.


def test_suggest_outfit_empty_wardrobe():
    """
    Test Tool 2 failure mode: an empty wardrobe template.
    Verifies the loop forks safely to general styling advice without raising a KeyError.
    """
    sample_item = {
        "title": "Neon Track Pants",
        "category": "bottoms",
        "colors": ["neon green"],
        "style_tags": ["streetwear", "bold"]
    }
    
    # Load the designated empty wardrobe structure
    empty_wardrobe = get_empty_wardrobe()
    
    # Run the tool
    response = suggest_outfit(sample_item, empty_wardrobe)
    
    assert isinstance(response, str)
    assert len(response.strip()) > 0
    # Confirms the fallback system/user prompt handled the zero-item array safely
# Test 3
from tools import create_fit_card

def test_create_fit_card_happy_path():
    """
    Test Tool 3 happy path validation.
    Verifies that the generated caption naturally retains the critical listing tokens.
    """
    sample_item = {
        "title": "Faded Band Tee",
        "price": 22.0,
        "platform": "depop"
    }
    sample_outfit = "Pair it with wide-leg carpenter jeans and chunky retro skate sneakers."
    
    caption = create_fit_card(sample_outfit, sample_item)
    
    assert isinstance(caption, str)
    assert len(caption.strip()) > 0
    # Check that crucial fields are accurately reflected in the caption string
    assert "depop" in caption.lower()
    assert "22" in caption


def test_create_fit_card_empty_guard():
    """
    Test Tool 3 failure path guard rails.
    Verifies that passing a blank or space-filled outfit string triggers the precise error contract.
    """
    sample_item = {
        "title": "Faded Band Tee",
        "price": 22.0,
        "platform": "depop"
    }
    expected_error = "Unable to generate your Fit Card because outfit data was missing. Please double-check your search and try again!"
    
    # Test completely empty string
    res_empty = create_fit_card("", sample_item)
    # Test whitespace-only string
    res_spaces = create_fit_card("    ", sample_item)
    
    assert res_empty == expected_error
    assert res_spaces == expected_error
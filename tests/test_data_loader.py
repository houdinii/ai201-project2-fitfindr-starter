"""Smoke tests: the data layer the tools are built on loads correctly."""
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe, load_listings


def test_listings_load():
    listings = load_listings()
    assert len(listings) == 40
    expected = {"id", "title", "description", "category", "style_tags",
                "size", "condition", "price", "colors", "brand", "platform"}
    assert expected <= set(listings[0].keys())


def test_example_wardrobe_loads():
    wardrobe = get_example_wardrobe()
    assert len(wardrobe["items"]) == 10


def test_empty_wardrobe_is_empty():
    assert get_empty_wardrobe()["items"] == []

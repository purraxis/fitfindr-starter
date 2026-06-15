import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe


class _FakeCompletions:
    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="Style it with relaxed denim and simple sneakers."
                    )
                )
            ]
        )


class _FakeClient:
    chat = SimpleNamespace(completions=_FakeCompletions())


def test_search_listings_returns_results_for_normal_query():
    results = search_listings("vintage graphic tee", None, None)

    assert isinstance(results, list)
    assert results
    assert all(isinstance(listing, dict) for listing in results)


def test_search_listings_returns_empty_list_for_impossible_query():
    results = search_listings("designer ballgown", "XXS", 5)

    assert results == []


def test_search_listings_respects_max_price():
    results = search_listings("vintage graphic tee", None, 20)

    assert results
    assert all(listing["price"] <= 20 for listing in results)


def test_suggest_outfit_returns_non_empty_string_with_empty_wardrobe(monkeypatch):
    monkeypatch.setattr("tools._get_groq_client", lambda: _FakeClient())
    new_item = search_listings("vintage graphic tee", None, 30)[0]

    result = suggest_outfit(new_item, get_empty_wardrobe())

    assert isinstance(result, str)
    assert result.strip()


def test_create_fit_card_returns_error_string_when_outfit_is_empty():
    new_item = search_listings("vintage graphic tee", None, 30)[0]

    result = create_fit_card("", new_item)

    assert isinstance(result, str)
    assert "cannot create a fit card" in result.lower()
    assert "outfit suggestion is empty" in result.lower()

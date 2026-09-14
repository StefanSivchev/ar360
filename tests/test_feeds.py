# The purpose of the file is to write the test that hold the registry to its requirments, then running pytest.

import pytest

# The file import
from src.common.feeds import FEEDS, feeds_by_pattern, get_feed


# The first  two tests.
def test_registry_has_six_feeds():
    """Ensure that the registry has the expected number of feeds."""
    assert len(FEEDS) == 6


def test_feed_names_are_unique():
    """Ensure that all feed names are unique."""
    names = [f.name for f in FEEDS]
    assert len(names) == len(set(names)), "Feed names must be unique"


# The requirments tests.
def test_names_are_safe_identifiers():
    """Ensure that feed names are valid Python identifiers."""
    for feed in FEEDS:
        assert feed.name.islower(), f"{feed.name} is not lowercase"
        assert " " not in feed.name, f"{feed.name} contains spaces"
        assert feed.name.replace("_", "").isalnum(), f"{feed.name} contains invalid characters"


def test_every_feed_has_a_business_key():
    for feed in FEEDS:
        assert isinstance(feed.business_key, tuple)
        assert len(feed.business_key) >= 1
        assert all(isinstance(k, str) for k in feed.business_key)


# Patterns and lookups
def test_patterns_are_valid_and_all_used():
    valid = {"delta", "snapshot", "append"}
    assert {f.load_pattern for f in FEEDS} == valid
    assert len(feeds_by_pattern("delta")) == 2


def test_get_feed_raises_helpfully_on_unknown_name():
    assert get_feed("fx_rates").load_pattern == "append"

    with pytest.raises(KeyError) as exc:
        get_feed("nope")
    assert "fx_rates" in str(exc.value)

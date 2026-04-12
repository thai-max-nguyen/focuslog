import pytest
from tracker.classifier import Classifier


@pytest.fixture
def classifier():
    rules = [
        {"id": 1, "app_name": "Code", "url_contains": None, "category": "Work"},
        {"id": 2, "app_name": "YouTube", "url_contains": None, "category": "Entertainment"},
        {"id": 3, "app_name": "Safari", "url_contains": "github.com", "category": "Work"},
        {"id": 4, "app_name": "Safari", "url_contains": "youtube.com", "category": "Entertainment"},
    ]
    return Classifier(rules)


def test_classify_exact_app_match(classifier):
    assert classifier.classify("Code", "") == "Work"


def test_classify_url_contains(classifier):
    assert classifier.classify("Safari", "GitHub - focuslog") == "Work"
    assert classifier.classify("Safari", "YouTube - Lo-fi music") == "Entertainment"


def test_classify_unknown(classifier):
    assert classifier.classify("Finder", "") == "Unknown"


def test_classify_url_takes_priority_over_app(classifier):
    assert classifier.classify("Safari", "youtube.com - music") == "Entertainment"


def test_partial_app_name_match(classifier):
    assert classifier.classify("Visual Studio Code", "main.py") == "Work"

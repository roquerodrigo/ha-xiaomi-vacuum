from __future__ import annotations

import json

import pytest

from custom_components.xiaomi_vacuum.api import CustomCleaning

SAMPLE_CONFIG = json.dumps(
    {
        "user_labels": [
            {"id": 836314484, "name": "Afternoon", "room_ids": [5, 8]},
            {"id": 131206493, "name": "Litter box", "room_ids": []},
        ]
    }
)


def test_list_from_config_parses_user_labels():
    assert CustomCleaning.list_from_config(SAMPLE_CONFIG) == [
        CustomCleaning(identifier=836314484, name="Afternoon"),
        CustomCleaning(identifier=131206493, name="Litter box"),
    ]


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        0,
        "not json",
        "[]",
        '{"user_labels": {}}',
        '{"other": []}',
    ],
)
def test_list_from_config_returns_empty_for_unusable_payloads(raw):
    assert CustomCleaning.list_from_config(raw) == []


def test_list_from_config_skips_malformed_labels():
    raw = json.dumps(
        {
            "user_labels": [
                "label",
                {"id": "1", "name": "String id"},
                {"id": 2},
                {"id": 3, "name": "Valid"},
            ]
        }
    )
    assert CustomCleaning.list_from_config(raw) == [
        CustomCleaning(identifier=3, name="Valid")
    ]


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Litter box", True), ("  litter BOX ", True), ("Litter", False)],
)
def test_matches_ignores_case_and_padding(name, expected):
    cleaning = CustomCleaning(identifier=1, name="Litter box")
    assert cleaning.matches(name) is expected

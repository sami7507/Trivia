"""Quick-start examples: every one must be valid, unique, and behave the way its label says."""
import random

import pytest

from backend.schemas.patient import PatientInput
from frontend.presets import CUSTOM_LABEL, NORMAL_ADULT, PRESET_LIST, PRESETS, label, random_patient

IDS = [p["title"] for p in PRESET_LIST]


def test_there_are_many_examples_covering_every_level():
    assert len(PRESET_LIST) >= 25
    assert {p["level"] for p in PRESET_LIST} == {0, 1, 2, 3}
    for level in (0, 1, 2, 3):
        assert sum(p["level"] == level for p in PRESET_LIST) >= 5


def test_labels_are_unique_and_custom_is_first():
    labels = [label(p) for p in PRESET_LIST]
    assert len(set(labels)) == len(labels)
    assert next(iter(PRESETS)) == CUSTOM_LABEL


@pytest.mark.parametrize("preset", PRESET_LIST, ids=IDS)
def test_example_is_valid_input(preset):
    PatientInput(**preset["data"])


def test_normal_adult_and_random_patients_are_valid():
    PatientInput(**NORMAL_ADULT)
    rng = random.Random(0)
    for _ in range(300):
        PatientInput(**random_patient(rng))


@pytest.mark.parametrize("preset", PRESET_LIST, ids=IDS)
def test_example_matches_its_label(client, auth, preset):
    """Within one level of the intended triage level (the CI model is a small quick-trained one)."""
    r = client.post("/api/v1/predict", json=preset["data"], headers=auth).json()
    assert abs(r["triage_level"] - preset["level"]) <= 1, (preset["title"], r["triage_label"])


def test_temperature_is_rounded_and_displayed_cleanly(client, auth, payload):
    r = client.post("/api/v1/predict", json={**payload, "temperature": 38.29999999999999}, headers=auth).json()
    temp = [e for e in r["explanation"] if e["feature"] == "Temperature"]
    assert all(e["value"] == "38.3 °C" for e in temp)

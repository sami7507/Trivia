"""Pydantic schema + safety-rule tests (no model required)."""
import pytest
from pydantic import ValidationError

from backend.schemas.auth import PhoneRequest
from backend.schemas.patient import PatientInput
from backend.services.predictor_service import safety_floor


def _p(**over):
    base = dict(age=45, heart_rate=90, systolic_bp=120, diastolic_bp=78, temperature=37.2,
                respiratory_rate=16, oxygen_saturation=98, pain_scale=3,
                chief_complaint="chest_pain", arrival_mode="walk_in", consciousness="alert")
    return PatientInput(**{**base, **over})


class TestPatientSchema:
    def test_valid_patient(self):
        assert _p().age == 45

    def test_age_out_of_range(self):
        with pytest.raises(ValidationError):
            _p(age=200)

    def test_invalid_chief_complaint(self):
        with pytest.raises(ValidationError):
            _p(chief_complaint="broken_arm_invalid")

    def test_spo2_upper_bound(self):
        with pytest.raises(ValidationError):
            _p(oxygen_saturation=110)

    def test_rejects_diastolic_above_systolic(self):
        with pytest.raises(ValidationError):
            _p(diastolic_bp=130, systolic_bp=100)

    def test_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            PatientInput(**{**_p().model_dump(), "name": "John"})


class TestSafetyNet:
    base = dict(consciousness="alert", oxygen_saturation=98, systolic_bp=120,
                heart_rate=80, respiratory_rate=16)

    def test_normal_has_no_floor(self):
        assert safety_floor(self.base)[0] == 0

    def test_unresponsive_forces_resuscitation(self):
        assert safety_floor({**self.base, "consciousness": "unresponsive"})[0] == 3

    def test_severe_hypoxia_forces_urgent(self):
        assert safety_floor({**self.base, "oxygen_saturation": 88})[0] == 2


class TestPhone:
    @pytest.mark.parametrize("raw,ok", [("+919876543210", True), ("+1 (415) 555-2671", True),
                                        ("9876543210", False), ("+0123456789", False), ("abc", False)])
    def test_phone_validation(self, raw, ok):
        if ok:
            assert PhoneRequest(phone=raw).phone.startswith("+")
        else:
            with pytest.raises(ValidationError):
                PhoneRequest(phone=raw)

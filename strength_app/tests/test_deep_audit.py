"""Deep audit 2026-06 regression tests.

One test class per Phase-1 C-item (named test_da_c<N>_* so they are
greppable against DEEP_AUDIT_REPORT.md).
"""
from datetime import date, timedelta

from django.test import TestCase

from strength_app.models import PatientProfile, PeriodisationState
from strength_app.v1_gamification import (
    MAX_SESSION_XP,
    XP_PER_SESSION,
    compute_session_xp,
)
from strength_app.v1_safety_logic import check_deload_needed


def _make_patient(pid='DA001', phone='9000009001'):
    return PatientProfile.objects.create(
        patient_id=pid,
        name='Deep Audit Patient',
        phone=phone,
        age=30,
        goals='Strength',
    )


class TestDAC1XpFormGate(TestCase):
    """C1 — XP form-safety gate must not be defeated by a base-XP floor."""

    def test_da_c1_all_unsafe_exercises_earn_zero_xp(self):
        results = [{'form_score': 40}, {'form_score': 30}, {'form_score': 54}]
        self.assertEqual(compute_session_xp(results), 0)

    def test_da_c1_mixed_results_earn_only_passing_xp_no_floor(self):
        # One passing exercise at 60 → base 10 XP, no quality bonus,
        # and no XP_PER_SESSION floor pulling it up to 40.
        results = [{'form_score': 40}, {'form_score': 60}]
        self.assertEqual(compute_session_xp(results), 10)

    def test_da_c1_quality_bonus_above_80(self):
        results = [{'form_score': 85}]
        self.assertEqual(compute_session_xp(results), 15)

    def test_da_c1_empty_results_keep_legacy_fallback(self):
        self.assertEqual(compute_session_xp([]), XP_PER_SESSION)

    def test_da_c1_xp_ceiling(self):
        results = [{'form_score': 90}] * 50
        self.assertEqual(compute_session_xp(results), MAX_SESSION_XP)


class TestDAC2DeloadFallback(TestCase):
    """C2/C11 — mandatory deload gate fires via the correct related_name
    and via calendar time in BOTH branches (state passed or resolved)."""

    def test_da_c2_fallback_resolves_periodisation_related_name(self):
        patient = _make_patient()
        PeriodisationState.objects.create(patient=patient, weeks_since_deload=4)
        needed, reason = check_deload_needed(patient)  # state NOT passed
        self.assertTrue(needed)
        self.assertIn('Mandatory deload', reason)

    def test_da_c2_passed_state_calendar_check(self):
        patient = _make_patient(pid='DA002', phone='9000009002')
        state = PeriodisationState.objects.create(
            patient=patient,
            weeks_since_deload=2,
            last_deload_date=date.today() - timedelta(weeks=5),
        )
        needed, reason = check_deload_needed(patient, periodisation_state=state)
        self.assertTrue(needed)
        self.assertIn('elapsed', reason)

    def test_da_c2_new_patient_no_state_no_crash(self):
        patient = _make_patient(pid='DA003', phone='9000009003')
        needed, reason = check_deload_needed(patient)
        self.assertFalse(needed)

    def test_da_c11_counter_wins_when_ahead_of_calendar(self):
        # Counter 5 but deload 1 week ago: counter is stale-high, but the
        # documented rule is max(counter, calendar) → deload True is the
        # accepted (conservative) outcome.
        patient = _make_patient(pid='DA004', phone='9000009004')
        state = PeriodisationState.objects.create(
            patient=patient,
            weeks_since_deload=5,
            last_deload_date=date.today() - timedelta(weeks=1),
        )
        needed, _ = check_deload_needed(patient, periodisation_state=state)
        self.assertTrue(needed)

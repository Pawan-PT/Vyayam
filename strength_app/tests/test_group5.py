from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from strength_app.equipment_routing import EXERCISE_EQUIPMENT_REQUIRED
from strength_app.exercise_content import EXERCISE_CONTENT
from strength_app.exercise_content_gap_fill import EXERCISE_CONTENT_GAP_FILL
from strength_app.exercise_tags import get_exercise_dosage
from strength_app.models import (
    DailyFoodLog,
    FoodItem,
    NutritionProfile,
    PatientProfile,
    PeriodisationState,
    StretchSession,
    StrengthProfile,
    WorkoutSession,
)
from strength_app.red_flag_map import get_excluded_exercises
from strength_app.stretch_pdf import generate_stretch_pdf
from strength_app.stretching_protocol import (
    PRE_MATCH_STRETCHES,
    TOTAL_PROTOCOL_DURATION,
    TOTAL_STRETCHES,
)
from strength_app.v1_football_constants import FOOTBALL_ASSESSMENT_TESTS
from strength_app.v1_gamification import (
    compute_asymmetry,
    compute_streak_days,
    compute_xp_and_level,
)
from strength_app.v1_nutrition_engine import (
    calculate_macro_targets,
    generate_mess_guidance,
    get_daily_nutrition_summary,
)
from strength_app.v1_prescription_engine import generate_v1_session
from strength_app.v1_safety_logic import (
    calculate_hormonal_phase,
    check_deload_needed,
    get_return_session_adjustments,
    limit_new_exercises,
)
from strength_app.warmup_library import COOLDOWN_BREATHING, ELEVATE_EXERCISES


def make_patient(patient_id="P5000", phone="9000000500", age=25, **kwargs):
    data = {
        "patient_id": patient_id,
        "name": "Test Patient",
        "phone": phone,
        "age": age,
        "goals": "Build strength",
    }
    data.update(kwargs)
    return PatientProfile.objects.create(**data)


class NutritionEngineTests(TestCase):
    def test_calculate_macro_targets_caps_protein_for_kidney_condition(self):
        targets = calculate_macro_targets(
            weight_kg=80,
            height_cm=180,
            age=30,
            sex="male",
            activity_level="moderately_active",
            goal="maintenance",
            medical_conditions=["Kidney disease"],
        )
        self.assertLessEqual(targets["protein_g"], 64)
        self.assertTrue(any("Protein capped" in note for note in targets["notes"]))

    def test_get_daily_nutrition_summary_uses_targets(self):
        patient = make_patient("P5001", "9000000501")
        profile = NutritionProfile.objects.create(
            patient=patient,
            nutrition_goal="maintenance",
            activity_level="moderately_active",
            target_calories=2000,
            target_protein_g=150,
            target_carbs_g=200,
            target_fat_g=60,
        )
        food = FoodItem.objects.create(
            name="Rice",
            category="grain",
            calories_per_100g=200,
            protein_per_100g=4,
            carbs_per_100g=45,
            fat_per_100g=1,
            serving_size_g=100,
        )
        DailyFoodLog.objects.create(
            patient=patient,
            food_item=food,
            log_date=date.today(),
            quantity_g=250,
            meal_type="lunch",
        )

        summary = get_daily_nutrition_summary(patient, date.today())
        self.assertEqual(summary["target_calories"], profile.target_calories)
        self.assertEqual(summary["traffic_light"], "red")
        self.assertEqual(summary["log_count"], 1)

    def test_generate_mess_guidance_includes_mode(self):
        patient = make_patient("P5002", "9000000502")
        profile = NutritionProfile.objects.create(
            patient=patient,
            nutrition_goal="muscle_gain",
            activity_level="moderately_active",
            target_calories=2400,
            target_protein_g=160,
            target_carbs_g=300,
            target_fat_g=70,
        )
        foods = [
            FoodItem.objects.create(
                name="Paneer",
                category="dairy",
                calories_per_100g=265,
                protein_per_100g=18,
                carbs_per_100g=6,
                fat_per_100g=20,
                serving_size_g=100,
            ),
            FoodItem.objects.create(
                name="Rice",
                category="grain",
                calories_per_100g=200,
                protein_per_100g=4,
                carbs_per_100g=45,
                fat_per_100g=1,
                serving_size_g=100,
            ),
            FoodItem.objects.create(
                name="Spinach",
                category="vegetable",
                calories_per_100g=25,
                protein_per_100g=3,
                carbs_per_100g=4,
                fat_per_100g=0,
                serving_size_g=100,
            ),
        ]
        guidance = generate_mess_guidance(foods, profile)
        self.assertIn("Muscle/Performance Mode", guidance)


class GamificationTests(TestCase):
    def test_compute_xp_and_level_counts_legacy_sessions(self):
        patient = make_patient("P5003", "9000000503")
        WorkoutSession.objects.create(patient=patient, xp_earned=0)
        WorkoutSession.objects.create(patient=patient, xp_earned=0)
        WorkoutSession.objects.create(patient=patient, xp_earned=80)
        result = compute_xp_and_level(patient)
        self.assertEqual(result["total_xp"], 160)
        self.assertEqual(result["user_level"], 1)
        self.assertEqual(result["xp_current"], 160)
        self.assertEqual(result["xp_percentage"], 80)

    def test_compute_streak_days_counts_today_and_yesterday(self):
        patient = make_patient("P5004", "9000000504")
        today = timezone.now()
        yesterday = today - timedelta(days=1)
        session_today = WorkoutSession.objects.create(patient=patient)
        session_yesterday = WorkoutSession.objects.create(patient=patient)
        WorkoutSession.objects.filter(pk=session_today.pk).update(session_date=today)
        WorkoutSession.objects.filter(pk=session_yesterday.pk).update(session_date=yesterday)
        self.assertEqual(compute_streak_days(patient), 2)

    def test_compute_asymmetry_reports_gap(self):
        patient = make_patient("P5005", "9000000505")
        profile = StrengthProfile.objects.create(
            patient=patient,
            hinge_asymmetry="moderate",
            hinge_left=40,
            hinge_right=60,
        )
        asym = compute_asymmetry(profile)
        self.assertIsNotNone(asym)
        self.assertIn("Hinge pattern", asym["description"])


class SafetyLogicTests(TestCase):
    def test_calculate_hormonal_phase_unknown_for_stale_period(self):
        patient = make_patient(
            "P5006",
            "9000000506",
            biological_sex="female",
            cycle_tracking_enabled=True,
            last_period_start=date.today() - timedelta(days=120),
        )
        phase = calculate_hormonal_phase(patient)
        self.assertEqual(phase, "unknown")

    def test_get_return_session_adjustments_moderate_return(self):
        patient = make_patient("P5007", "9000000507")
        session = WorkoutSession.objects.create(patient=patient)
        WorkoutSession.objects.filter(pk=session.pk).update(
            session_date=timezone.now() - timedelta(days=20)
        )
        adjustment = get_return_session_adjustments(patient)
        self.assertEqual(adjustment["adjustment"], "moderate_return")
        self.assertTrue(adjustment["tempo_slow"])

    def test_check_deload_needed_when_weeks_exceeded(self):
        patient = make_patient("P5008", "9000000508")
        state = PeriodisationState.objects.create(patient=patient, weeks_since_deload=4)
        needs_deload, reason = check_deload_needed(patient, state)
        self.assertTrue(needs_deload)
        self.assertIn("Mandatory deload", reason)

    def test_limit_new_exercises_caps_aa_phase(self):
        patient = make_patient("P5009", "9000000509", training_age_months=1)
        state = PeriodisationState.objects.create(
            patient=patient, current_phase="anatomical_adaptation_iso"
        )
        plan = [
            {"exercise_id": "a", "is_new": True},
            {"exercise_id": "b", "is_new": True},
            {"exercise_id": "c", "is_new": True},
        ]
        limited = limit_new_exercises(patient, plan, state)
        self.assertEqual(len(limited), 2)


class PrescriptionEngineTests(TestCase):
    def test_generate_v1_session_mobility_only_for_severe_menstruation(self):
        patient = make_patient(
            "P5010",
            "9000000510",
            biological_sex="female",
            cycle_tracking_enabled=True,
            last_period_start=date.today() - timedelta(days=2),
            menstrual_pain_level="severe",
        )
        session = generate_v1_session(patient)
        self.assertEqual(session["status"], "mobility_only")
        self.assertEqual(session["working_sets"], [])
        self.assertEqual(session["modifiers_applied"]["volume_modifier"], 0.0)


class StretchingProtocolTests(SimpleTestCase):
    def test_protocol_totals_match_entries(self):
        self.assertEqual(TOTAL_STRETCHES, len(PRE_MATCH_STRETCHES))
        total_duration = sum(item["duration_seconds"] for item in PRE_MATCH_STRETCHES)
        self.assertEqual(TOTAL_PROTOCOL_DURATION, total_duration)


class EquipmentRoutingTests(SimpleTestCase):
    def test_equipment_mapping_contains_known_exercises(self):
        self.assertIn("ring_push_up", EXERCISE_EQUIPMENT_REQUIRED)
        self.assertIn("rings", EXERCISE_EQUIPMENT_REQUIRED["ring_push_up"])
        self.assertEqual(EXERCISE_EQUIPMENT_REQUIRED["sit_to_stand"], [])


class RedFlagMapTests(SimpleTestCase):
    def test_acl_red_flag_excludes_plyometrics(self):
        excluded = get_excluded_exercises(["acl_grade_1_2"])
        self.assertIn("jump_squats", excluded)


class ExerciseContentTests(SimpleTestCase):
    def test_content_dictionaries_include_expected_keys(self):
        self.assertIn("sit_to_stand", EXERCISE_CONTENT)
        self.assertIn("diamond_push_up", EXERCISE_CONTENT_GAP_FILL)


class StretchPdfTests(TestCase):
    def test_generate_stretch_pdf_returns_pdf_bytes(self):
        patient = make_patient("P5011", "9000000511")
        session = StretchSession.objects.create(
            patient=patient,
            total_stretches=2,
            stretches_completed=2,
            total_duration_seconds=120,
            camera_used=True,
            stretch_results_json=[
                {
                    "name": "Hip Flexor Stretch",
                    "side": "left",
                    "prescribed_duration": 30,
                    "actual_duration": 30,
                    "completed": True,
                    "posture_note": "",
                },
                {
                    "name": "Hamstring Stretch",
                    "side": "right",
                    "prescribed_duration": 30,
                    "actual_duration": 28,
                    "completed": False,
                    "posture_note": "Tight on the right",
                },
            ],
        )

        pdf_buffer = generate_stretch_pdf(patient, session)
        data = pdf_buffer.getvalue()
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertGreater(len(data), 1000)


class WarmupLibraryTests(SimpleTestCase):
    def test_elevate_and_breathing_entries_have_duration(self):
        for entry in ELEVATE_EXERCISES:
            self.assertTrue(entry.get("id"))
            self.assertTrue(entry.get("name"))
            self.assertGreater(entry.get("duration_seconds", 0), 0)

        for entry in COOLDOWN_BREATHING:
            self.assertTrue(entry.get("id"))
            self.assertTrue(entry.get("name"))
            self.assertGreater(entry.get("duration_seconds", 0), 0)


class ExerciseTagsTests(SimpleTestCase):
    def test_get_exercise_dosage_returns_strength_defaults(self):
        dosage = get_exercise_dosage(
            "sit_to_stand",
            capability_numeric=3,
            age=30,
            lifestyle="moderately_active",
            goal_type="functional",
        )
        self.assertEqual(dosage["sets"], 2)
        self.assertEqual(dosage["reps"], 10)
        self.assertEqual(dosage["hold_duration"], 0)
        self.assertFalse(dosage["is_hold"])

    def test_get_exercise_dosage_returns_balance_hold(self):
        dosage = get_exercise_dosage(
            "double_leg_balance",
            capability_numeric=3,
            age=30,
            lifestyle="moderately_active",
            goal_type="functional",
        )
        self.assertEqual(dosage["sets"], 2)
        self.assertEqual(dosage["reps"], 1)
        self.assertEqual(dosage["hold_duration"], 25)
        self.assertTrue(dosage["is_hold"])


class FootballConstantsTests(SimpleTestCase):
    def test_assessment_tests_have_scoring_bands(self):
        for test in FOOTBALL_ASSESSMENT_TESTS:
            self.assertTrue(test.get("test_id"))
            self.assertTrue(test.get("name"))
            self.assertEqual(len(test.get("scoring_thresholds", [])), 4)
            scoring = test.get("scoring", {})
            self.assertEqual(set(scoring.keys()), {1, 2, 3, 4, 5})

"""
Creates test patients with full onboarding data for development testing.
Usage: python manage.py create_test_patient
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from strength_app.models import PatientProfile, StrengthProfile, PeriodisationState
from datetime import date


class Command(BaseCommand):
    help = 'Creates test patients with full V1 data (TEST001 and TEST002)'

    def handle(self, *args, **options):
        self._create_test001()
        self._create_test002()

    def _create_test001(self):
        patient, created = PatientProfile.objects.get_or_create(
            patient_id='TEST001',
            defaults={
                'name': 'Test Athlete',
                'age': 28,
                'phone': '9999900001',
                'biological_sex': 'male',
                'height_cm': 175,
                'weight_kg': 75,
                'goals': 'general_strength',
                'training_history': 'beginner',
                'training_age_months': 6,
                'equipment_available_json': ['dumbbells', 'pullup_bar', 'bands'],
                'training_location': 'home_some',
                'session_duration_minutes': 45,
                'sessions_per_week': 4,
                'goal_type': 'general_strength',
                'sleep_quality': 'good',
                'stress_level': 'moderate',
                'red_flags_json': [],
                'lifestyle': 'moderately_active',
                'gate_test_completed': True,
            }
        )

        if created:
            patient.password = make_password('test1234')
            patient.save(update_fields=['password'])

        profile, _ = StrengthProfile.objects.get_or_create(
            patient=patient,
            defaults={
                'squat_score': 3,
                'hinge_score': 2,
                'push_score': 3,
                'pull_score': 1,
                'core_score': 3,
                'rotate_score': 2,
                'lunge_score': 3,
            }
        )

        state, _ = PeriodisationState.objects.get_or_create(
            patient=patient,
            defaults={
                'current_phase': 'anatomical_adaptation_iso',
                'current_week': 1,
                'macrocycle_number': 1,
                'phase_start_date': date.today(),
                'anatomical_adaptation_weeks': 4,
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f'TEST001 {"created" if created else "already exists"}: '
            f'male 28yo, beginner, 4x/week — '
            f'S{profile.squat_score} H{profile.hinge_score} P{profile.push_score} '
            f'Pu{profile.pull_score} C{profile.core_score} R{profile.rotate_score} L{profile.lunge_score}'
        ))

    def _create_test002(self):
        """Female, 42yo, rehabilitation, knee pain, cycle tracking."""
        patient, created = PatientProfile.objects.get_or_create(
            patient_id='TEST002',
            defaults={
                'name': 'Test Patient Female',
                'age': 42,
                'phone': '8888888888',
                'biological_sex': 'female',
                'height_cm': 165,
                'weight_kg': 65,
                'goals': 'rehabilitation',
                'training_history': 'beginner',
                'training_age_months': 3,
                'equipment_available_json': ['bands'],
                'training_location': 'home_none',
                'session_duration_minutes': 40,
                'sessions_per_week': 3,
                'goal_type': 'rehabilitation',
                'sleep_quality': '7_to_8',
                'stress_level': 'moderate',
                'red_flags_json': ['knee_pain_patellofemoral'],
                'lifestyle': 'sedentary',
                'gate_test_completed': True,
                # Hormonal tracking
                'cycle_tracking_enabled': True,
                'cycle_length_days': 28,
                'last_period_start': date.today().replace(day=1),
                'menstrual_pain_level': 'moderate',
            }
        )

        if created:
            patient.password = make_password('test1234')
            patient.save(update_fields=['password'])

        profile, _ = StrengthProfile.objects.get_or_create(
            patient=patient,
            defaults={
                'squat_score': 1,
                'hinge_score': 2,
                'push_score': 2,
                'pull_score': 1,
                'core_score': 2,
                'rotate_score': 2,
                'lunge_score': 1,
            }
        )

        state, _ = PeriodisationState.objects.get_or_create(
            patient=patient,
            defaults={
                'current_phase': 'anatomical_adaptation_iso',
                'current_week': 1,
                'macrocycle_number': 1,
                'phase_start_date': date.today(),
                'anatomical_adaptation_weeks': 4,
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f'TEST002 {"created" if created else "already exists"}: '
            f'female 42yo, rehab, knee_pain, cycle tracking — '
            f'S{profile.squat_score} H{profile.hinge_score} P{profile.push_score} '
            f'Pu{profile.pull_score} C{profile.core_score} R{profile.rotate_score} L{profile.lunge_score}'
        ))

"""
Seeds re-runnable football/athlete-tier test fixtures.

Creates:
    COACH    /coach/login/   user: fbcoach        pass: coachpass123
    ATHLETE  /login/         phone: 91000000NN    pass: athletepass123

Namespace is isolated:
    - Coach username  : 'fbcoach'                  (free; no other seeder uses it)
    - Therapist ID    : 'FBTEST_COACH'             (free)
    - Athlete patient_id : 'FBTEST_001' ... 'FBTEST_NNN' (our key)
    - Athlete phones  : 9100000001 ... 9100000099  (block 91… is unused)

A previous version of this command used phones 90000000XX which collided
with seed_therapist_demo's reserved range 9000000001-9000000004. The 91…
block is confirmed empty in production, and HARD GUARDS below abort any
write that would overwrite a non-FBTEST_* row.

Athletes get athlete_tier_eligible=True + athlete_sport='football' so they
land in the football flow. A minimal StrengthProfile is created and
gate_test_completed=True so /login/ routes them to the dashboard (not
back into onboarding); the football assessment itself (FootballProfile,
GateTestResult) is intentionally left EMPTY so it can be run live.

Usage:
    python manage.py seed_football_test               # default 5 athletes
    python manage.py seed_football_test --count 8
    python manage.py seed_football_test --reset       # remove FBTEST rows
"""

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from strength_app.models import (
    CoachPatientLink,
    PatientProfile,
    StrengthProfile,
    TherapistProfile,
)


COACH_USERNAME = 'fbcoach'
COACH_PASSWORD = 'coachpass123'
COACH_NAME = 'Test FB Coach'
COACH_THERAPIST_ID = 'FBTEST_COACH'

ATHLETE_PASSWORD = 'athletepass123'
ATHLETE_PHONE_PREFIX = '910000'   # plus 4-digit zero-padded index → 10 digits
PATIENT_ID_PREFIX = 'FBTEST_'


class Command(BaseCommand):
    help = (
        'Idempotent seed of football-tier test logins: one coach (fbcoach) '
        'and N athletes (FBTEST_001..). Use --reset to remove only these rows.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=5,
            help='Number of test athletes to create (default 5, max 99).'
        )
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete FBTEST_* athletes + fbcoach user + their links, then exit.'
        )

    # ------------------------------------------------------------------ entry

    def handle(self, *args, **opts):
        if opts['reset']:
            self._reset()
            return

        count = max(1, min(99, opts['count']))

        try:
            with transaction.atomic():
                coach = self._seed_coach()
                athletes = []
                for i in range(1, count + 1):
                    athletes.append(self._seed_athlete(i, coach))
        except CommandAbort as exc:
            self.stderr.write(self.style.ERROR(f'\n  ABORT: {exc}\n'))
            return

        self._print_credentials(athletes)

    # ----------------------------------------------------------------- reset

    def _reset(self):
        link_count = CoachPatientLink.objects.filter(
            patient__patient_id__startswith=PATIENT_ID_PREFIX
        ).delete()[0]

        athlete_count = PatientProfile.objects.filter(
            patient_id__startswith=PATIENT_ID_PREFIX
        ).delete()[0]

        # Deleting the User cascades to TherapistProfile (OneToOne, CASCADE)
        # and any remaining CoachPatientLink rows pointing at that therapist.
        user_count = User.objects.filter(username=COACH_USERNAME).delete()[0]

        self.stdout.write(self.style.SUCCESS(
            f'  Reset complete — removed {athlete_count} athlete(s), '
            f'{link_count} link(s), {user_count} coach user.'
        ))

    # ----------------------------------------------------------------- coach

    def _seed_coach(self):
        # Hard guard: if 'fbcoach' already exists AND it already has a
        # TherapistProfile whose therapist_id is NOT ours, refuse to touch it.
        existing = User.objects.filter(username=COACH_USERNAME).first()
        if existing is not None:
            tp = TherapistProfile.objects.filter(user=existing).first()
            if tp is not None and tp.therapist_id != COACH_THERAPIST_ID:
                raise CommandAbort(
                    f"User '{COACH_USERNAME}' already exists and is bound to a "
                    f"different TherapistProfile (therapist_id={tp.therapist_id!r}, "
                    f"name={tp.name!r}). Refusing to overwrite. Choose a different "
                    f"COACH_USERNAME in seed_football_test.py or remove the conflict."
                )

        user, _ = User.objects.get_or_create(
            username=COACH_USERNAME,
            defaults={
                'email': 'fbcoach@test.local',
                'first_name': 'Test',
                'last_name': 'Coach',
            },
        )
        user.set_password(COACH_PASSWORD)
        user.email = 'fbcoach@test.local'
        user.save()

        therapist, _ = TherapistProfile.objects.update_or_create(
            user=user,
            defaults={
                'therapist_id': COACH_THERAPIST_ID,
                'name': COACH_NAME,
                'license_number': 'FBTEST-LIC-001',
                'specialization': 'Football Performance (Test)',
                'email': 'fbcoach@test.local',
                'phone': '9100000000',
            },
        )
        return therapist

    # --------------------------------------------------------------- athlete

    def _seed_athlete(self, i, coach):
        patient_id = f'{PATIENT_ID_PREFIX}{i:03d}'
        phone = f'{ATHLETE_PHONE_PREFIX}{i:04d}'        # 9100000001, 9100000002, …
        # alternate male/female so the female-ACL path is exercised
        bio_sex = 'male' if i % 2 == 1 else 'female'

        # Hard guard: the target phone is unique; refuse to overwrite a
        # PatientProfile we don't own.
        clash = PatientProfile.objects.filter(phone=phone).exclude(
            patient_id=patient_id
        ).first()
        if clash is not None:
            raise CommandAbort(
                f"Phone {phone} is already held by patient_id={clash.patient_id!r} "
                f"(name={clash.name!r}). Refusing to overwrite a non-FBTEST row. "
                f"Either run --reset on the owning seeder or pick a fresh prefix."
            )

        patient, _ = PatientProfile.objects.update_or_create(
            patient_id=patient_id,
            defaults={
                'name': f'TEST Athlete {i}',
                'phone': phone,
                'email': f'fbtest{i:03d}@test.local',
                'password': make_password(ATHLETE_PASSWORD),
                'age': 22,
                'biological_sex': bio_sex,
                'height_cm': 178.0 if bio_sex == 'male' else 168.0,
                'weight_kg': 72.0 if bio_sex == 'male' else 62.0,
                'goals': 'Football athletic-performance test fixture.',
                'goal_type': 'athletic',
                'sport_type': 'football',
                'training_history': 'intermediate',
                'training_age_months': 24,
                'lifestyle': 'very_active',
                'sessions_per_week': 4,
                'session_duration_minutes': 60,
                'training_location': 'gym',
                # Skip strength_app onboarding so /login/ goes straight to the
                # dashboard, from which the athlete can enter the football flow.
                'gate_test_completed': True,
                'therapist_managed': False,
                # Football/athlete tier flags — confirmed in v1_football_views.py
                'athlete_tier_eligible': True,
                'athlete_tier_active': False,   # the assessment flips this True
                'athlete_sport': 'football',
            },
        )

        # Minimal StrengthProfile so patient_login's has_profile check passes
        # and the user lands on v1_dashboard. Scores left intentionally low —
        # we're not testing the strength radar here.
        StrengthProfile.objects.get_or_create(
            patient=patient,
            assessment_number=1,
            defaults={
                'squat_score': 3, 'hinge_score': 3, 'push_score': 3,
                'pull_score': 3, 'core_score': 3, 'rotate_score': 3,
                'lunge_score': 3,
            },
        )

        # NOTE: deliberately NO FootballProfile, NO GateTestResult — the user
        # will run the football assessment live to watch it propagate to the
        # squad view.

        CoachPatientLink.objects.update_or_create(
            coach=coach,
            patient=patient,
            defaults={'is_active': True},
        )

        return {'i': i, 'phone': phone, 'patient_id': patient_id, 'sex': bio_sex}

    # ----------------------------------------------------------------- print

    def _print_credentials(self, athletes):
        self.stdout.write(self.style.SUCCESS(
            '\n  Football test seed complete.\n'
        ))
        self.stdout.write(
            f'    COACH    → /coach/login/   user: {COACH_USERNAME}'
            f'        pass: {COACH_PASSWORD}'
        )
        for a in athletes:
            self.stdout.write(
                f'    ATHLETE {a["i"]} → /login/         phone: {a["phone"]}   '
                f'pass: {ATHLETE_PASSWORD}   ({a["sex"]})'
            )
        self.stdout.write('')


class CommandAbort(Exception):
    """Raised by hard-guard checks to abort the transaction with a clear message."""

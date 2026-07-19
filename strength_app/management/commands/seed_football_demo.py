"""
Seeds the football coach + athlete DEMO fixtures (lived-in account).

Creates:
    COACH    /coach/login/   user: coach_arjun     pass: simple
             Arjun Mehta — Vadodara United FC (TherapistProfile, which is
             what the coach_required decorator resolves via
             request.user.therapistprofile).
    ATHLETE  /login/         phone: 9000000005     pass: athlete
             Kabir Singh, 21, male — football track, linked to coach_arjun
             via CoachPatientLink (the model coach_squad reads).

Seeded so the account looks lived-in:
    - Completed 6-test football battery ~4 weeks ago (hop, Nordic, sprint,
      pogo, COD, Y-balance) with mid-tier raw values → football_level
      computes to 3 (Consolidation) via FootballProfile.compute_level().
    - 14 completed training sessions across the last 4 weeks with
      ExerciseExecution rows (rep_quality_source='manual' — self-counted,
      NO fabricated form/rep-quality data) and SessionFeedback sRPE 4-7.
    - 3 upcoming matches in the next 3 weeks (MatchDate).
    - PeriodisationState mid-macrocycle; FootballProfile.season_phase
      = 'in_season'.
    - Coach notes on the CoachPatientLink.

Namespace is isolated:
    - Coach username   : 'coach_arjun'   (free — no other seeder uses it)
    - Therapist ID     : 'FBDEMO_COACH'
    - Athlete patient_id: 'FBDEMO_KABIR'
    - Athlete phone    : 9000000005 (seed_therapist_demo reserves ...01-04;
                         hard guard below refuses to overwrite a non-FBDEMO
                         holder of this phone)

Idempotent: rows keyed on patient_id / username / therapist_id are
update_or_create'd; the athlete's own sessions + matches are wiped and
re-created on every run so counts never grow.

Usage:
    python manage.py seed_football_demo
    python manage.py seed_football_demo --reset    # remove demo rows only
"""

from datetime import date, datetime, time, timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from strength_app.models import (
    CoachPatientLink,
    ExerciseExecution,
    FootballProfile,
    MatchDate,
    PatientProfile,
    PeriodisationState,
    SessionFeedback,
    StrengthProfile,
    TherapistProfile,
    WorkoutSession,
)


COACH_USERNAME = 'coach_arjun'
COACH_PASSWORD = 'simple'
COACH_NAME = 'Arjun Mehta'
COACH_THERAPIST_ID = 'FBDEMO_COACH'
COACH_CLUB = 'Vadodara United FC'

ATHLETE_PATIENT_ID = 'FBDEMO_KABIR'
ATHLETE_PHONE = '9000000005'
ATHLETE_PASSWORD = 'athlete'
ATHLETE_NAME = 'Kabir Singh'

# ── Assessment battery (~4 weeks ago) — mid-tier raw values ────────────────
# Hand-picked against FOOTBALL_ASSESSMENT_TESTS scoring_thresholds so the
# per-test scores are 3s and 4s and compute_level() rounds to 3
# (Consolidation): (4+3+3+3+3+4)/6 = 3.33 → 3. All bilateral pairs sit
# above their LSI_THRESHOLDS bands, so lsi_flag stays False.
ASSESSMENT_DAYS_AGO = 29   # > 4 weeks → the athlete "Tests due" card shows
ASSESSMENT = {
    'hop_left_cm': 162.0, 'hop_right_cm': 174.0, 'hop_score': 4,      # best 174 → band 150-179
    'nordic_seconds': 5.0, 'nordic_score': 3,                         # band 4-6 s
    'sprint_seconds': 3.52, 'sprint_score': 3,                        # band 3.41-3.70 s
    'pogo_clean_reps': 17, 'pogo_score': 3,                           # band 15-19
    'cod_left_seconds': 2.55, 'cod_right_seconds': 2.48, 'cod_score': 3,  # best 2.48 → band 2.41-2.70
    'ybalance_left_pct': 92.0, 'ybalance_right_pct': 96.0, 'ybalance_score': 4,  # best 96 → band 95-104
}

# ── 14 completed sessions across the last 4 weeks (3-4/week) ───────────────
# (days_ago, duration_min, srpe, difficulty_rating, perceived_difficulty)
SESSION_PLAN = [
    (27, 62, 5, 3, 'just_right'),
    (25, 55, 4, 3, 'just_right'),
    (23, 68, 6, 4, 'hard'),
    (20, 48, 4, 3, 'just_right'),
    (18, 65, 6, 4, 'hard'),
    (16, 58, 5, 3, 'just_right'),
    (14, 72, 7, 4, 'hard'),
    (12, 50, 4, 3, 'just_right'),
    (10, 60, 5, 3, 'just_right'),
    (8, 66, 6, 4, 'hard'),
    (6, 45, 4, 3, 'just_right'),
    (4, 70, 7, 4, 'hard'),
    (2, 57, 5, 3, 'just_right'),
    (1, 63, 6, 3, 'just_right'),
]

# Per-session exercise menu — HSR-phase-2-flavoured football S&C work.
# rep_quality_source='manual' throughout: these are self-counted gym
# sessions, so NO green/yellow/red rep quality and NO form score is
# fabricated (clinical-integrity rule: rep-level data never invented).
SESSION_EXERCISES = [
    [
        ('barbell_rdl', 'Barbell RDL', 'posterior_chain', 4, 6),
        ('bulgarian_split_squats', 'Bulgarian Split Squats', 'lower_body', 4, 6),
        ('nordic_hamstring_curl', 'Nordic Hamstring Curl', 'posterior_chain', 3, 5),
        ('heavy_calf_raise', 'Heavy Calf Raise', 'lower_body', 4, 8),
        ('copenhagen_plank', 'Copenhagen Plank', 'core', 3, 8),
    ],
    [
        ('barbell_hip_thrust', 'Barbell Hip Thrust', 'posterior_chain', 4, 6),
        ('goblet_squat', 'Goblet Squat', 'lower_body', 4, 8),
        ('single_leg_rdl', 'Single-Leg RDL', 'posterior_chain', 3, 8),
        ('lateral_band_walks', 'Lateral Band Walks', 'lower_body', 3, 12),
        ('bird_dog', 'Bird Dog', 'core', 3, 10),
    ],
    [
        ('trap_bar_deadlift', 'Trap Bar Deadlift', 'posterior_chain', 4, 5),
        ('step_ups', 'Step-Ups', 'lower_body', 3, 8),
        ('sliding_leg_curl', 'Sliding Leg Curl', 'posterior_chain', 3, 8),
        ('single_leg_calf_raise', 'Single-Leg Calf Raise', 'lower_body', 3, 10),
        ('box_jumps', 'Box Jumps', 'power', 3, 5),
    ],
]

COACH_NOTES = (
    "2026-07-02: Solid engine — COD times keep improving in small-sided games. "
    "Keep the Nordic volume up, hamstring endurance is the weak link.\n"
    "2026-07-14: Talked through in-season loading — 3 quality gym sessions on "
    "non-match weeks, 2 when we have a midweek fixture."
)

# Upcoming matches: days from today (all inside the next 3 weeks).
MATCH_PLAN = [
    (5, 'Rajkot Rovers', 'League — home'),
    (12, 'Surat City FC', 'League — away'),
    (19, 'Ahmedabad Kings', 'Cup quarter-final'),
]


class Command(BaseCommand):
    help = (
        'Idempotent demo seed: coach_arjun (Arjun Mehta, Vadodara United FC) '
        '+ Kabir Singh, a lived-in football athlete (9000000005 / athlete). '
        'Use --reset to remove only these rows.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete the FBDEMO athlete + coach_arjun user + links, then exit.'
        )

    # ------------------------------------------------------------------ entry

    def handle(self, *args, **opts):
        if opts['reset']:
            self._reset()
            return

        try:
            with transaction.atomic():
                coach = self._seed_coach()
                patient = self._seed_athlete()
                self._seed_link(coach, patient)
                self._seed_football_profile(patient)
                self._seed_periodisation(patient)
                self._seed_sessions(patient)
                self._seed_matches(patient)
        except CommandAbort as exc:
            self.stderr.write(self.style.ERROR(f'\n  ABORT: {exc}\n'))
            return

        self._print_summary(patient)

    # ----------------------------------------------------------------- reset

    def _reset(self):
        links = CoachPatientLink.objects.filter(
            patient__patient_id=ATHLETE_PATIENT_ID
        ).delete()[0]
        athletes = PatientProfile.objects.filter(
            patient_id=ATHLETE_PATIENT_ID
        ).delete()[0]
        # Deleting the User cascades to TherapistProfile (OneToOne CASCADE).
        users = User.objects.filter(username=COACH_USERNAME).delete()[0]
        self.stdout.write(self.style.SUCCESS(
            f'  Reset complete — removed {athletes} athlete(s), '
            f'{links} link(s), {users} coach user tree.'
        ))

    # ----------------------------------------------------------------- coach

    def _seed_coach(self):
        # Hard guard: refuse to hijack a coach_arjun bound to someone else's
        # TherapistProfile.
        existing = User.objects.filter(username=COACH_USERNAME).first()
        if existing is not None:
            tp = TherapistProfile.objects.filter(user=existing).first()
            if tp is not None and tp.therapist_id != COACH_THERAPIST_ID:
                raise CommandAbort(
                    f"User '{COACH_USERNAME}' exists and is bound to a different "
                    f"TherapistProfile (therapist_id={tp.therapist_id!r}). "
                    f"Refusing to overwrite."
                )

        user, _ = User.objects.get_or_create(
            username=COACH_USERNAME,
            defaults={'email': 'arjun.mehta@vadodaraunited.in', 'first_name': 'Arjun',
                      'last_name': 'Mehta'},
        )
        user.set_password(COACH_PASSWORD)
        user.email = 'arjun.mehta@vadodaraunited.in'
        user.save()

        therapist, _ = TherapistProfile.objects.update_or_create(
            user=user,
            defaults={
                'therapist_id': COACH_THERAPIST_ID,
                'name': COACH_NAME,
                'license_number': 'FBDEMO-LIC-001',
                'specialization': f'S&C Coach · {COACH_CLUB}',
                'email': 'arjun.mehta@vadodaraunited.in',
                'phone': '9000000099',
            },
        )
        return therapist

    # --------------------------------------------------------------- athlete

    def _seed_athlete(self):
        clash = PatientProfile.objects.filter(phone=ATHLETE_PHONE).exclude(
            patient_id=ATHLETE_PATIENT_ID
        ).first()
        if clash is not None:
            raise CommandAbort(
                f'Phone {ATHLETE_PHONE} is already held by '
                f'patient_id={clash.patient_id!r} ({clash.name!r}). '
                f'Refusing to overwrite a non-FBDEMO row.'
            )

        patient, _ = PatientProfile.objects.update_or_create(
            patient_id=ATHLETE_PATIENT_ID,
            defaults={
                'name': ATHLETE_NAME,
                'phone': ATHLETE_PHONE,
                'email': 'kabir.singh@example.com',
                'password': make_password(ATHLETE_PASSWORD),
                'age': 21,
                'biological_sex': 'male',
                'height_cm': 176.0,
                'weight_kg': 70.0,
                'goals': 'Hold a starting spot this season; sharper first 10 m and stronger duels.',
                'goal_type': 'athletic',
                'sport_type': 'football',
                'training_history': 'intermediate',
                'training_age_months': 30,
                'lifestyle': 'very_active',
                'sessions_per_week': 4,
                'session_duration_minutes': 60,
                'training_location': 'gym',
                'gate_test_completed': True,
                'therapist_managed': False,
                'athlete_tier_eligible': True,
                'athlete_tier_active': True,   # battery completed → football flow live
                'athlete_sport': 'football',
                'raw_test_data_json': {
                    'position': 'Central Midfielder',
                    # Manual-entry strength tests (Part 3) — same shape the
                    # live assessment writes. e1RM = Epley w×(1+reps/30);
                    # rel_bw vs 70 kg. Display only, never in football_level.
                    'strength_tests': {
                        'bench_press': {
                            'weight_kg': 60.0, 'reps': 8, 'e1rm': 76.0,
                            'rel_bw': 1.09,
                            'tested_at': str(date.today() - timedelta(days=ASSESSMENT_DAYS_AGO)),
                        },
                        'leg_press': {
                            'weight_kg': 140.0, 'reps': 10, 'e1rm': 186.7,
                            'rel_bw': 2.67,
                            'tested_at': str(date.today() - timedelta(days=ASSESSMENT_DAYS_AGO)),
                        },
                    },
                },
            },
        )

        # Strength base: squat 4 keeps the post-session SLS check from
        # re-locking the plyometric gate (football_update_after_session).
        StrengthProfile.objects.get_or_create(
            patient=patient,
            assessment_number=1,
            defaults={
                'squat_score': 4, 'hinge_score': 4, 'push_score': 3,
                'pull_score': 3, 'core_score': 4, 'rotate_score': 3,
                'lunge_score': 4,
            },
        )
        return patient

    def _seed_link(self, coach, patient):
        CoachPatientLink.objects.update_or_create(
            coach=coach,
            patient=patient,
            defaults={'is_active': True, 'notes': COACH_NOTES},
        )
        # Kabir belongs to coach_arjun only — deactivate any stray links
        # a previous seeder/run may have left.
        CoachPatientLink.objects.filter(patient=patient).exclude(
            coach=coach
        ).update(is_active=False)

    # -------------------------------------------------------------- football

    def _seed_football_profile(self, patient):
        fp, _ = FootballProfile.objects.get_or_create(patient=patient)
        for field, value in ASSESSMENT.items():
            setattr(fp, field, value)
        # Derive level / LSI / F-V / plyo clearance with the model's own
        # logic — never re-implemented here.
        fp.compute_level()
        fp.compute_lsi()
        fp.compute_fv_tendency()
        fp.check_plyometric_gate()
        fp.season_phase = 'in_season'
        fp.hsr_current_phase = 'hsr_phase_2'
        fp.hsr_weeks_completed = 2
        fp.last_reassessment = None
        fp.save()

        # assessed_at is auto_now_add — backdate via queryset update.
        assessed = timezone.now() - timedelta(days=ASSESSMENT_DAYS_AGO)
        FootballProfile.objects.filter(pk=fp.pk).update(assessed_at=assessed)
        return fp

    def _seed_periodisation(self, patient):
        today = date.today()
        PeriodisationState.objects.update_or_create(
            patient=patient,
            defaults={
                'current_phase': 'strength',
                'current_week': 4,
                'macrocycle_number': 1,
                'phase_start_date': today - timedelta(days=27),
                'last_deload_date': today - timedelta(days=14),
                'weeks_since_deload': 2,
                'total_sessions_this_cycle': len(SESSION_PLAN),
            },
        )

    # -------------------------------------------------------------- sessions

    def _seed_sessions(self, patient):
        # Wipe-and-recreate our own rows so reruns never duplicate.
        # WorkoutSession delete cascades to ExerciseExecution + SessionFeedback.
        WorkoutSession.objects.filter(patient=patient).delete()

        now = timezone.now()
        for i, (days_ago, duration, srpe, diff_rating, perceived) in enumerate(SESSION_PLAN):
            when = timezone.make_aware(
                datetime.combine((now - timedelta(days=days_ago)).date(), time(18, 30))
            )
            week_number = max(1, 4 - days_ago // 7)
            exercises = SESSION_EXERCISES[i % len(SESSION_EXERCISES)]

            session = WorkoutSession.objects.create(
                patient=patient,
                week_number=week_number,
                total_duration_minutes=duration,
                total_exercises_completed=len(exercises),
                patient_comfortable=True,
                difficulty_rating=diff_rating,
                prescription_mode='ai_auto',
            )
            for ex_id, ex_name, category, sets, reps in exercises:
                ExerciseExecution.objects.create(
                    session=session,
                    exercise_id=ex_id,
                    exercise_name=ex_name,
                    category=category,
                    prescribed_sets=sets,
                    prescribed_reps=reps,
                    prescribed_rest=90,
                    rep_quality_source='manual',   # self-counted — no fabricated form data
                    overall_form_score=None,
                    completion_percentage=100.0,
                )

            feedback = SessionFeedback.objects.create(
                session=session,
                patient=patient,
                perceived_difficulty=perceived,
                sleep_last_night='7_to_8',
                pain_reported='none',
                energy_level='good',
                session_rpe=srpe,
            )
            # Both timestamps are auto_now_add — backdate via queryset update.
            WorkoutSession.objects.filter(pk=session.pk).update(session_date=when)
            SessionFeedback.objects.filter(pk=feedback.pk).update(
                created_at=when + timedelta(minutes=duration)
            )

    # --------------------------------------------------------------- matches

    def _seed_matches(self, patient):
        MatchDate.objects.filter(patient=patient).delete()
        today = date.today()
        for days_ahead, opponent, note in MATCH_PLAN:
            MatchDate.objects.create(
                patient=patient,
                match_date=today + timedelta(days=days_ahead),
                opponent=opponent,
                notes=note,
            )

    # ----------------------------------------------------------------- print

    def _print_summary(self, patient):
        fp = FootballProfile.objects.get(patient=patient)
        sessions = WorkoutSession.objects.filter(patient=patient).count()
        matches = MatchDate.objects.filter(
            patient=patient, match_date__gte=date.today()
        ).count()
        self.stdout.write(self.style.SUCCESS('\n  Football demo seed complete.\n'))
        self.stdout.write(f'    COACH   → /coach/login/  user: {COACH_USERNAME}   pass: {COACH_PASSWORD}')
        self.stdout.write(f'    ATHLETE → /login/        phone: {ATHLETE_PHONE}  pass: {ATHLETE_PASSWORD}')
        self.stdout.write(
            f'    Kabir Singh: football level L{fp.football_level}, '
            f'{fp.get_season_phase_display()}, plyo {fp.plyometric_cleared}, '
            f'{sessions} sessions seeded, {matches} upcoming matches.\n'
        )


class CommandAbort(Exception):
    """Raised by hard-guard checks to abort the transaction with a clear message."""

"""
R2 — report engine tests: a golden-file assertion over the ENTIRE report
dict for a fully fabricated session, every pattern rule on/off,
PainEvent-as-only-pain-source, idempotency, triggers, and
never-raises-on-empty. All fixture timestamps are fixed (auto_now_add
fields are back-dated with .update()) so the dict is deterministic.
"""

import json
from datetime import datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from strength_app.models import PainEvent, PatientProfile, RestEvent
from strength_app.report_builder import build_report, generate_session_report
from therapist_app.models import (
    ExerciseSetLog,
    Prescription,
    PrescriptionItem,
    SessionLog,
    SessionLogItem,
    SessionReport,
    Therapist,
    TherapistMessage,
    TherapistPatientLink,
)

IST = ZoneInfo('Asia/Kolkata')


def at(hour, minute, second=0):
    return datetime(2026, 7, 1, hour, minute, second, tzinfo=IST)


def make_session(suffix='G1', with_pain=True, with_message=True):
    """A deterministic 2-exercise session: camera glute bridge (2 sets,
    tempo 3-1-2, fatiguing form 90->70, one corrected valgus cue, one +30s
    rest extension, aching 4/10 at rep 6 of set 2) + guided single-leg
    balance (2 self-reported sets, one 200s pause). 18:00 -> 18:31 IST."""
    therapist_user = User.objects.create_user(f'dr_gold_{suffix}', password='x')
    therapist = Therapist.objects.create(
        user=therapist_user, full_name='Dr. Gold')
    patient_user = User.objects.create_user(f'golden_{suffix}', password='x')
    profile = PatientProfile.objects.create(
        patient_id=f'GOLD{suffix}', name='Golden Patient',
        phone=f'90000199{suffix[-2:].zfill(2)}'[:15],
        age=30, goals='Rehab', therapist_managed=True, user=patient_user,
    )
    link = TherapistPatientLink.objects.create(
        therapist=therapist, patient=patient_user,
        full_name='Golden Patient', email=f'g{suffix}@x.com', status='active',
    )
    rx = Prescription.objects.create(
        link=link, week_number=8, published_at=at(9, 0), draft_json={})
    item_gb = PrescriptionItem.objects.create(
        prescription=rx, order=0, exercise_id='ex_glute_bridge',
        exercise_name='Glute Bridge', sets=2, reps=10, load='BW',
        rest_seconds=60, tempo='3-1-2')
    item_bal = PrescriptionItem.objects.create(
        prescription=rx, order=1, exercise_id='ex_sl_balance',
        exercise_name='Single-Leg Balance', sets=2, reps=30, load='BW',
        rest_seconds=30, tempo='')

    log = SessionLog.objects.create(link=link, prescription=rx)
    SessionLog.objects.filter(pk=log.pk).update(
        started_at=at(18, 0), completed_at=at(18, 31))
    log.refresh_from_db()

    li_gb = SessionLogItem.objects.create(
        session_log=log, prescription_item=item_gb, order=0,
        exercise_id='ex_glute_bridge', exercise_name='Glute Bridge',
        sets_completed=2, difficulty='easy',
        started_at=at(18, 0, 30), completed_at=at(18, 12, 30))
    SessionLogItem.objects.create(
        session_log=log, prescription_item=item_bal, order=1,
        exercise_id='ex_sl_balance', exercise_name='Single-Leg Balance',
        sets_completed=2, difficulty='right',
        started_at=at(18, 13), completed_at=at(18, 30))

    def raw(ecc, hold, con):
        return [{'name': 'down', 'ms': ecc}, {'name': 'hold', 'ms': hold},
                {'name': 'up', 'ms': con}]

    ExerciseSetLog.objects.create(
        session_log=log, link=link, exercise_id='ex_glute_bridge',
        exercise_name='Glute Bridge', set_number=1, mode='camera',
        reps_count=10, reps_json=[
            {'rep_n': 1, 'partial': False, 'form_pct': 90.0,
             'bottom_angle': 95.0,
             'phase_ms': {'ecc': 3000, 'hold': 1000, 'con': 2000},
             'phases_raw': raw(3000, 1000, 2000), 'cues': []},
            {'rep_n': 2, 'partial': False, 'form_pct': 88.0,
             'bottom_angle': 93.0,
             'phase_ms': {'ecc': 2900, 'hold': 900, 'con': 2100},
             'phases_raw': raw(2900, 900, 2100),
             'cues': [{'cue_id': 'knee_valgus', 'corrected': True}]},
            {'rep_n': 3, 'partial': False, 'form_pct': 92.0,
             'bottom_angle': 91.0,
             'phase_ms': {'ecc': 3100, 'hold': 1100, 'con': 1900},
             'phases_raw': raw(3100, 1100, 1900), 'cues': []},
        ],
        demo_viewed=True, started_at=at(18, 1), ended_at=at(18, 4))
    ExerciseSetLog.objects.create(
        session_log=log, link=link, exercise_id='ex_glute_bridge',
        exercise_name='Glute Bridge', set_number=2, mode='camera',
        reps_count=9, reps_json=[
            {'rep_n': 1, 'partial': False, 'form_pct': 72.0,
             'bottom_angle': 100.0,
             'phase_ms': {'ecc': 1500, 'hold': 1000, 'con': 2000},
             'phases_raw': raw(1500, 1000, 2000), 'cues': []},
            {'rep_n': 2, 'partial': True, 'form_pct': 68.0,
             'bottom_angle': 102.0,
             'phase_ms': {'ecc': 1400, 'hold': 900, 'con': 2100},
             'phases_raw': raw(1400, 900, 2100), 'cues': []},
        ],
        demo_viewed=True, started_at=at(18, 6), ended_at=at(18, 9))
    for n, (start, end) in enumerate([((18, 14), (18, 16)),
                                      ((18, 20), (18, 22))], start=1):
        ExerciseSetLog.objects.create(
            session_log=log, link=link, exercise_id='ex_sl_balance',
            exercise_name='Single-Leg Balance', set_number=n, mode='guided',
            reps_count=30, reps_json=[],
            started_at=at(*start), ended_at=at(*end))

    ext = RestEvent.objects.create(
        patient=profile, session_log=log, exercise_id='ex_glute_bridge',
        exercise_name='Glute Bridge', set_number=1, context='between_sets',
        extra_seconds=30)
    RestEvent.objects.filter(pk=ext.pk).update(created_at=at(18, 4, 30))
    pause = RestEvent.objects.create(
        patient=profile, session_log=log, exercise_id='ex_sl_balance',
        exercise_name='Single-Leg Balance', set_number=1, context='pause',
        extra_seconds=200)
    RestEvent.objects.filter(pk=pause.pk).update(created_at=at(18, 17))

    if with_pain:
        pe = PainEvent.objects.create(
            patient=profile, exercise_id='ex_glute_bridge',
            exercise_name='Glute Bridge', set_number=2, rep_number=6,
            pain_type='aching', pain_severity=4, threshold_applied=5,
            outcome='continued')
        PainEvent.objects.filter(pk=pe.pk).update(created_at=at(18, 7))

    if with_message:
        msg = TherapistMessage.objects.create(
            link=link, sender=patient_user, is_system=False,
            body='Knee felt tight today')
        TherapistMessage.objects.filter(pk=msg.pk).update(sent_at=at(18, 10))

    return log, profile, link


class TestR2GoldenReport(TestCase):
    maxDiff = None

    def test_golden_full_report_dict(self):
        log, _, _ = make_session()
        report = build_report(log)
        self.assertEqual(report, GOLDEN)

    def test_builder_is_deterministic(self):
        log, _, _ = make_session()
        self.assertEqual(build_report(log), build_report(log))


GOLDEN = {'version': 1, 'header': {'patient_name': 'Golden Patient', 'date': '01 Jul 2026', 'week_number': 8, 'session_number': 1, 'status': 'complete', 'duration_mmss': '31:00', 'completion_pct': 100, 'exercises_done': 2, 'exercises_total': 2, 'form_avg': 82.0}, 'safety': [], 'narrative': 'Golden completed all 2 exercises in 31 minutes. Form was strongest on Glute Bridge (82%). Form on Glute Bridge fell from 90% (set 1) to 70% (set 2). Golden reported aching 4/10 at rep 6 of set 2 of Glute Bridge — inside their usual range — the session continued.', 'exercises': [{'exercise_id': 'ex_glute_bridge', 'name': 'Glute Bridge', 'mode': 'camera-tracked', 'prescribed': {'sets': 2, 'reps': 10, 'tempo': '3-1-2', 'load': 'BW', 'rest_seconds': 60}, 'achieved': {'sets': 2, 'reps_per_set': [10, 9]}, 'time': {'elapsed_mmss': '12:00', 'working_mmss': '6:00', 'label': 'elapsed includes rest and pauses; working is time in the sets'}, 'sets': [{'set_number': 1, 'reps': 10, 'hold_seconds': 0, 'self_reported': False, 'form_avg': 90.0, 'depth_best': 91.0, 'depth_avg': 93.0, 'tempo_pct': 100, 'avg_rep_ms': 6000, 'rest_extended_seconds': 30, 'rest_extension_count': 1, 'rest_cut_short': False, 'pause_seconds': 0}, {'set_number': 2, 'reps': 9, 'hold_seconds': 0, 'self_reported': False, 'form_avg': 70.0, 'depth_best': 100.0, 'depth_avg': 101.0, 'tempo_pct': 67, 'avg_rep_ms': 4450, 'rest_extended_seconds': 0, 'rest_extension_count': 0, 'rest_cut_short': False, 'pause_seconds': 0}], 'cues': [{'cue_id': 'knee_valgus', 'text': 'Knees toward the camera', 'fired': 1, 'corrected': 1, 'note': 'corrected within a rep each time'}], 'tempo': {'pct': 87, 'dominant_miss': {'phase': 'lowering', 'direction': 'fast', 'avg_actual': 1.4, 'prescribed': 3, 'share': 0.4}}, 'pain': [{'severity': 4, 'type': 'aching', 'set_number': 2, 'rep_number': 6, 'outcome': 'continued', 'text': 'aching 4/10 at rep 6 of set 2'}], 'feedback': 'easy', 'skipped': None, 'demo_viewed': True, 'form_avg': 82.0}, {'exercise_id': 'ex_sl_balance', 'name': 'Single-Leg Balance', 'mode': 'guided (self-reported)', 'prescribed': {'sets': 2, 'reps': 30, 'tempo': '', 'load': 'BW', 'rest_seconds': 30}, 'achieved': {'sets': 2, 'reps_per_set': [30, 30]}, 'time': {'elapsed_mmss': '17:00', 'working_mmss': '4:00', 'label': 'elapsed includes rest and pauses; working is time in the sets'}, 'sets': [{'set_number': 1, 'reps': 30, 'hold_seconds': 0, 'self_reported': True, 'form_avg': None, 'depth_best': None, 'depth_avg': None, 'tempo_pct': None, 'avg_rep_ms': None, 'rest_extended_seconds': 0, 'rest_extension_count': 0, 'rest_cut_short': False, 'pause_seconds': 200}, {'set_number': 2, 'reps': 30, 'hold_seconds': 0, 'self_reported': True, 'form_avg': None, 'depth_best': None, 'depth_avg': None, 'tempo_pct': None, 'avg_rep_ms': None, 'rest_extended_seconds': 0, 'rest_extension_count': 0, 'rest_cut_short': False, 'pause_seconds': 0}], 'cues': [], 'tempo': None, 'pain': [], 'feedback': 'just right', 'skipped': None, 'demo_viewed': False, 'form_avg': None}], 'patterns': [{'finding': 'fatigue', 'evidence': 'Form on Glute Bridge fell from 90% (set 1) to 70% (set 2).'}, {'finding': 'perception_vs_performance', 'evidence': 'Glute Bridge was rated easy while form fell from 90% to 70%.'}], 'trends': [], 'messages': [{'time': '6:10 PM', 'body': 'Knee felt tight today'}], 'review_points': ['Form on Glute Bridge fell from 90% (set 1) to 70% (set 2).'], 'footer': "This report is generated automatically from camera-based estimates and the patient's own reports. Single-camera tracking has accuracy limits, and guided exercises rely on self-reported counts. It is not a clinical assessment — the treating physiotherapist retains clinical judgment."}


class TestR2PainSourceOfTruth(TestCase):
    """Locked decision 4: PainEvent is the ONLY pain source — never
    SessionLogItem.pain; silent below-threshold reports must appear."""

    def test_item_pain_is_ignored_painevent_is_used(self):
        log, profile, _ = make_session(suffix='P1', with_pain=False)
        # Poison SessionLogItem.pain — the report must NOT read it.
        SessionLogItem.objects.filter(session_log=log).update(pain=9)
        report = build_report(log)
        self.assertEqual(report['exercises'][0]['pain'], [])
        self.assertNotIn('9/10', json.dumps(report))

        # A silent below-threshold PainEvent DOES appear.
        pe = PainEvent.objects.create(
            patient=profile, exercise_id='ex_glute_bridge',
            exercise_name='Glute Bridge', set_number=1, rep_number=2,
            pain_type='dull', pain_severity=2, threshold_applied=5,
            outcome='continued')
        PainEvent.objects.filter(pk=pe.pk).update(created_at=at(18, 3))
        report = build_report(log)
        self.assertEqual(
            report['exercises'][0]['pain'][0]['text'],
            'dull 2/10 at rep 1 of set 1'.replace('rep 1', 'rep 2'))


class TestR2PatternToggles(TestCase):

    def test_warm_in_fires_on_improving_form(self):
        log, _, _ = make_session(suffix='W1', with_pain=False)
        # Invert the two glute-bridge sets: 70 first, 90 last.
        first = ExerciseSetLog.objects.get(session_log=log, set_number=1,
                                           exercise_id='ex_glute_bridge')
        second = ExerciseSetLog.objects.get(session_log=log, set_number=2,
                                            exercise_id='ex_glute_bridge')
        first.reps_json, second.reps_json = second.reps_json, first.reps_json
        first.save(update_fields=['reps_json'])
        second.save(update_fields=['reps_json'])
        report = build_report(log)
        findings = {p['finding'] for p in report['patterns']}
        self.assertIn('warm_in', findings)
        self.assertNotIn('fatigue', findings)

    def test_no_patterns_on_stable_form(self):
        log, _, _ = make_session(suffix='S1', with_pain=False)
        # Make both sets identical (stable 90%) and rating 'right'.
        first = ExerciseSetLog.objects.get(session_log=log, set_number=1,
                                           exercise_id='ex_glute_bridge')
        ExerciseSetLog.objects.filter(
            session_log=log, set_number=2, exercise_id='ex_glute_bridge',
        ).update(reps_json=first.reps_json)
        SessionLogItem.objects.filter(session_log=log).update(difficulty='right')
        report = build_report(log)
        self.assertEqual(report['patterns'], [])

    def test_late_rest_extensions_fire_fatigue(self):
        log, profile, _ = make_session(suffix='L1', with_pain=False)
        # Stabilize form so the form rule stays silent.
        first = ExerciseSetLog.objects.get(session_log=log, set_number=1,
                                           exercise_id='ex_glute_bridge')
        ExerciseSetLog.objects.filter(
            session_log=log, set_number=2, exercise_id='ex_glute_bridge',
        ).update(reps_json=first.reps_json)
        SessionLogItem.objects.filter(session_log=log).update(difficulty='right')
        # Two extensions on the SECOND-half exercise (single-leg balance).
        for n in (1, 2):
            RestEvent.objects.create(
                patient=profile, session_log=log, exercise_id='ex_sl_balance',
                exercise_name='Single-Leg Balance', set_number=n,
                context='between_sets', extra_seconds=30)
        report = build_report(log)
        fatigue = [p for p in report['patterns'] if p['finding'] == 'fatigue']
        self.assertEqual(len(fatigue), 1)
        self.assertIn('second half', fatigue[0]['evidence'])

    def test_tempo_tendency_fires_when_dominant(self):
        log, _, _ = make_session(suffix='T1', with_pain=False)
        # Make EVERY glute-bridge rep rush the lowering phase.
        rushed = [
            {'rep_n': i, 'partial': False, 'form_pct': 90.0,
             'bottom_angle': 95.0,
             'phase_ms': {'ecc': 1200, 'hold': 1000, 'con': 2000},
             'phases_raw': [{'name': 'down', 'ms': 1200},
                            {'name': 'hold', 'ms': 1000},
                            {'name': 'up', 'ms': 2000}],
             'cues': []}
            for i in (1, 2, 3)
        ]
        ExerciseSetLog.objects.filter(
            session_log=log, exercise_id='ex_glute_bridge',
        ).update(reps_json=rushed)
        SessionLogItem.objects.filter(session_log=log).update(difficulty='right')
        report = build_report(log)
        tendency = [p for p in report['patterns']
                    if p['finding'] == 'tempo_tendency']
        self.assertEqual(len(tendency), 1)
        self.assertIn('Rushes the lowering phase', tendency[0]['evidence'])
        self.assertIn('1.2s', tendency[0]['evidence'])


class TestR2Trends(TestCase):

    def _previous_report(self, link, profile, days_before, report_json):
        rx = link.prescriptions.first()
        prev_log = SessionLog.objects.create(link=link, prescription=rx)
        SessionLog.objects.filter(pk=prev_log.pk).update(
            started_at=at(17, 0) - timedelta(days=days_before),
            completed_at=at(17, 30) - timedelta(days=days_before))
        prev_log.refresh_from_db()
        return SessionReport.objects.create(
            link=link, session_log=prev_log, patient=profile,
            report_date=prev_log.started_at.date(),
            status='complete', report_json=report_json)

    def test_form_delta_recurrence_and_streak(self):
        log, profile, link = make_session(suffix='R1')
        prev_json = {
            'header': {'form_avg': 74.0, 'completion_pct': 100},
            'exercises': [{
                'exercise_id': 'ex_glute_bridge',
                'pain': [{'severity': 3, 'type': 'aching'}],
                'sets': [{'depth_best': 101.0}],
            }],
        }
        self._previous_report(link, profile, 2, prev_json)
        report = build_report(log)
        findings = {t['finding']: t['evidence'] for t in report['trends']}
        # form 82 vs 74 → higher by 8
        self.assertIn('8% higher', findings['form_delta'])
        # depth best today 91 vs 101 → improved ~10°
        self.assertIn('improved', findings['rom_delta'])
        # aching on glute bridge last session too → 2nd consecutive
        self.assertIn('2nd consecutive session', findings['pain_recurrence'])
        # both sessions 100% → streak of 2
        self.assertIn('2 fully-completed sessions in a row',
                      findings['completion_streak'])
        # And the narrative closes with the streak sentence (S6).
        self.assertIn('2 fully-completed sessions in a row',
                      report['narrative'])

    def test_no_trends_without_previous_reports(self):
        log, _, _ = make_session(suffix='R2')
        self.assertEqual(build_report(log)['trends'], [])


class TestR2GenerateIdempotent(TestCase):

    def test_generate_twice_is_one_immutable_row(self):
        log, _, _ = make_session(suffix='I1')
        first = generate_session_report(log)
        snapshot = first.report_json
        # Mutate underlying data — the snapshot must NOT change.
        ExerciseSetLog.objects.filter(session_log=log).delete()
        second = generate_session_report(log)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(SessionReport.objects.count(), 1)
        second.refresh_from_db()
        self.assertEqual(second.report_json, snapshot)
        self.assertEqual(second.status, 'complete')


class TestR2NeverRaises(TestCase):
    """Builder must never raise on missing/partial data."""

    def test_bare_session_with_zero_activity(self):
        log, _, _ = make_session(suffix='B1', with_pain=False,
                                 with_message=False)
        ExerciseSetLog.objects.filter(session_log=log).delete()
        RestEvent.objects.filter(session_log=log).delete()
        SessionLogItem.objects.filter(session_log=log).delete()
        SessionLog.objects.filter(pk=log.pk).update(completed_at=None)
        log.refresh_from_db()
        report = build_report(log)
        self.assertEqual(report['header']['status'], 'partial')
        self.assertEqual(report['header']['completion_pct'], 0)
        self.assertTrue(any(s['kind'] == 'incomplete' for s in report['safety']))
        self.assertTrue(report['narrative'])

    def test_corrupt_reps_json_shapes_do_not_raise(self):
        log, _, _ = make_session(suffix='B2', with_pain=False)
        ExerciseSetLog.objects.filter(
            session_log=log, exercise_id='ex_glute_bridge', set_number=1,
        ).update(reps_json=[{'phase_ms': 'junk'}, {},
                            {'cues': [{'corrected': True}]}])
        report = build_report(log)
        self.assertIn('exercises', report)


class TestR2TriggersHTTP(TestCase):
    """The three trigger points, driven through the real seeded flow."""

    def setUp(self):
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        self.client.post(reverse('patient_login'),
                         {'phone': '9000000001', 'password': 'patient'})
        self.client.post(reverse('therapist_session_start'))

    def test_completion_trigger_creates_complete_report(self):
        resp = self.client.post(reverse('therapist_session_complete'),
                                {'overall_pain': 1})
        self.assertEqual(resp.status_code, 302)
        report = SessionReport.objects.get()
        self.assertEqual(report.status, 'complete')
        self.assertEqual(report.report_json['header']['exercises_total'], 5)

    def test_pain_pause_trigger_creates_early_end_report(self):
        resp = self.client.post(
            reverse('therapist_session_report_pain', args=[0]),
            data=json.dumps({'severity': 8, 'pain_type': 'aching',
                             'set_number': 1, 'rep_number': 4}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['action'], 'pause')
        report = SessionReport.objects.get()
        self.assertEqual(report.status, 'ended_early_pain')
        safety = report.report_json['safety']
        self.assertTrue(safety)
        self.assertIn('aching', safety[0]['text'])
        self.assertIn('rep 4', safety[0]['text'])

    def test_finished_safety_net_is_idempotent(self):
        self.client.post(reverse('therapist_session_complete'),
                         {'overall_pain': 0})
        self.assertEqual(SessionReport.objects.count(), 1)
        self.client.get(reverse('therapist_session_finished'))
        self.assertEqual(SessionReport.objects.count(), 1)

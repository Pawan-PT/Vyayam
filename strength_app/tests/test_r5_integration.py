"""
R5 — the whole-cycle acceptance test, automated.

The handoff's acceptance sentence: a sloppy session with a rest extension,
a pause, a mid-rep pain 4, a cue the patient obeys and one they ignore →
open the report → EVERY one of those events appears, correctly pinned, in
human-readable prose. This drives the real seeded HTTP endpoints (the same
requests the device makes) and then reads the rendered pages, not the dict.
"""

import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from therapist_app.models import SessionReport, TherapistPatientLink


def rep(n, form, cues=(), partial=False):
    return {
        'rep_n': n, 'partial': partial, 'form_pct': form,
        'bottom_angle': 100.0 - n,
        'phase_ms': {'ecc': 2900, 'hold': 900, 'con': 2000},
        'phases_raw': [{'name': 'down', 'ms': 2900}, {'name': 'hold', 'ms': 900},
                       {'name': 'up', 'ms': 2000}],
        'cues': [{'cue_id': c, 'corrected': corr} for c, corr in cues],
    }


class TestR5EndToEndAcceptance(TestCase):
    maxDiff = None

    def setUp(self):
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        self.client.post(reverse('patient_login'),
                         {'phone': '9000000001', 'password': 'patient'})
        self.client.post(reverse('therapist_session_start'))

    def post_json(self, url_name, idx, payload):
        resp = self.client.post(
            reverse(url_name, args=[idx]), data=json.dumps(payload),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200, f'{url_name} idx {idx}')
        return resp

    def run_sloppy_session(self):
        """Glute bridge (camera): set 1 with a corrected knee_valgus cue,
        +30s rest extension; set 2 sloppier, hips_level ignored 3x, aching
        4/10 reported at rep 6. A 220s pause during the guided balance.
        Then walk the rest of the protocol and complete."""
        self.client.get(reverse('therapist_session_exercise', args=[0]))
        # Set 1 — the OBEYED cue: knee_valgus fired rep 2, corrected.
        self.post_json('therapist_session_set_log', 0, {
            'set_number': 1, 'mode': 'camera', 'reps_count': 10,
            'duration_ms': 180000, 'demo_viewed': True,
            'reps': [rep(1, 88), rep(2, 84, [('knee_valgus', True)]),
                     rep(3, 90), rep(4, 89)],
        })
        self.post_json('therapist_session_rest_event', 0,
                       {'kind': 'extension', 'seconds': 30, 'set_number': 1})
        # Mid-rep pain at rep 6 of set 2 (modal opened mid-rep).
        self.post_json('therapist_session_report_pain', 0, {
            'severity': 4, 'pain_type': 'aching',
            'set_number': 2, 'rep_number': 6})
        # Set 2 — the IGNORED cue: hips_level fired 3x, never corrected.
        self.post_json('therapist_session_set_log', 0, {
            'set_number': 2, 'mode': 'camera', 'reps_count': 9,
            'duration_ms': 200000,
            'reps': [rep(1, 72, [('hips_level', False)]),
                     rep(2, 70, [('hips_level', False)]),
                     rep(3, 66, [('hips_level', False)])],
        })
        # Guided balance with a 220s whole-session pause.
        self.client.get(reverse('therapist_session_exercise', args=[2]))
        self.post_json('therapist_session_set_log', 2, {
            'set_number': 1, 'mode': 'guided', 'reps_count': 30,
            'duration_ms': 60000, 'reps': []})
        self.post_json('therapist_session_rest_event', 2,
                       {'kind': 'pause', 'seconds': 220, 'set_number': 1})
        # Per-exercise feedback for the bridge, then complete the session.
        self.client.post(reverse('therapist_session_feedback', args=[0]),
                         {'pain': 0, 'difficulty': 'right', 'sets_completed': 2})
        resp = self.client.post(reverse('therapist_session_complete'),
                                {'overall_pain': 2})
        self.assertEqual(resp.status_code, 302)
        return SessionReport.objects.get()

    def test_every_event_appears_in_human_readable_prose(self):
        report = self.run_sloppy_session()

        # Patient page and therapist page — the identical document.
        patient_page = self.client.get(
            reverse('therapist_session_report', args=[report.id]))
        therapist_client = self.client_class()
        therapist_client.force_login(User.objects.get(username='dr_shah'))
        link = TherapistPatientLink.objects.get(patient__username='anika')
        therapist_page = therapist_client.get(reverse(
            'therapist_session_report_detail', args=[link.id, report.id]))

        for page in (patient_page, therapist_page):
            self.assertEqual(page.status_code, 200)
            content = page.content.decode('utf-8')
            # 1 · the mid-rep pain, correctly pinned:
            self.assertIn('aching 4/10 at rep 6 of set 2', content)
            # 2 · the rest extension on the right set:
            self.assertIn('+30s extended', content)
            # 3 · the pause with its duration:
            self.assertIn('paused 220s', content)
            # 4 · the obeyed cue, in the coach's live phrasing:
            self.assertIn('Knees toward the camera', content)
            self.assertIn('corrected within a rep each time', content)
            # 5 · the ignored cue, flagged for the therapist:
            self.assertIn('Keep your hips level', content)
            self.assertIn('persisted after cueing — flagged for review', content)
            # 6 · the narrative reads like prose about this patient:
            self.assertIn('Anika', content)
            # 7 · both time clocks, labeled:
            self.assertIn('working', content)
            # 8 · demo viewed + the honest guided label:
            self.assertIn('watched demo', content)
            self.assertIn('guided (self-reported)', content)
            # 9 · the fixed integrity footer:
            self.assertIn('not a clinical assessment', content)

        # And the report's review points carry the persisted cue.
        review = ' '.join(report.report_json['review_points'])
        self.assertIn('persisted after coaching', review)

    def test_fatigue_pattern_lands_in_report(self):
        report = self.run_sloppy_session()
        patterns = {p['finding'] for p in report.report_json['patterns']}
        # Set 1 avg 87.75 -> set 2 avg 69.3: the fatigue signature fires.
        self.assertIn('fatigue', patterns)

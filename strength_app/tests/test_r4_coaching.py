"""
R4 — coaching wiring tests (server-renderable half). The arbitration LOGIC
is node-tested in strength_app/tests/js/coach_core.test.mjs (12 tests:
priority/interrupt, rep spacing, final-2-reps blackout, 3-strike fading,
praise rules, calibration, confidence gate, fatigue, tempo channel,
calibratedTarget math, registry quality). These tests pin that the camera
template actually routes through that logic.
"""

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class TestR4CoachWiring(TestCase):

    def setUp(self):
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        self.client.post(reverse('patient_login'),
                         {'phone': '9000000001', 'password': 'patient'})
        self.client.post(reverse('therapist_session_start'))

    def render_camera_page(self):
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertTemplateUsed(resp, 'strength_app/v1_exercise_execute.html')
        return resp.content.decode('utf-8')

    def test_arbiter_is_loaded_and_owns_the_cue_sites(self):
        content = self.render_camera_page()
        self.assertIn('js/coach_core.', content)  # hashed static name
        self.assertIn('VyayamCoach.createArbiter()', content)
        # Every corrective cue site routes through arbitration…
        self.assertGreaterEqual(content.count('coachCue('), 12)
        # …and no live site speaks the old fault-label lines directly.
        self.assertNotIn(
            "VoiceCoach.speak('Push your knees out. Do not let them cave in.'",
            content)
        self.assertNotIn("VoiceCoach.speak('Keep your hips level — do not hike.'",
                         content)

    def test_calibration_confidence_and_coloring_wired(self):
        content = self.render_camera_page()
        self.assertIn('getGhostCurrentTarget = function()', content)  # wrapper
        self.assertIn('CoachCal.adjustTarget', content)
        self.assertIn('Coach.confidence(', content)
        self.assertIn('Coach.colorsFrozen()', content)
        self.assertIn('Coach.redAllowed(', content)
        # Assessment flows are never calibrated (scores stay comparable).
        self.assertIn('ASSESSMENT_MODE) return', content)

    def test_tempo_speech_yields_to_arbitration(self):
        content = self.render_camera_page()
        self.assertIn('Coach.tempoAllowed(', content)
        self.assertIn("word + ' — ' + this._left", content)

    def test_coach_core_module_ships(self):
        js = Path(settings.BASE_DIR, 'strength_app', 'static',
                  'strength_app', 'js', 'coach_core.js')
        self.assertTrue(js.exists())
        source = js.read_text(encoding='utf-8')
        # Locked rule of record: tempo NEVER colors form.
        self.assertIn('Tempo NEVER colors', source)
        self.assertIn('createArbiter', source)
        self.assertIn('calibratedTarget', source)

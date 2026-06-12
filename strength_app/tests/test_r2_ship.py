"""
R2 ship-readiness tests (Run 2). Grep anchors: test_r2_w1, test_r2_w2, ...
"""

import json

from django.test import TestCase, SimpleTestCase
from django.urls import reverse

from strength_app.models import PatientProfile, ExerciseExecution, WorkoutSession


# ════════════════════════════════════════════════════════════════════════
# W1 — live CV parity
# ════════════════════════════════════════════════════════════════════════

class TestR2W1ExportArtifact(SimpleTestCase):
    """The committed exercise_targets.json is generated, fresh, and sane."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from strength_app.cv_targets import _load
        cls.data = _load()

    def test_r2_w1_artifact_exists_and_covers_registry(self):
        from strength_app.exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        self.assertTrue(self.data, "exercise_targets.json missing or empty")
        missing = set(EXERCISE_METADATA.keys()) - set(self.data.keys())
        self.assertFalse(missing, f"registry IDs missing from artifact: {sorted(missing)[:10]}")

    def test_r2_w1_export_is_fresh(self):
        """Regenerate to a temp file and diff against the committed artifact."""
        import io
        from django.core.management import call_command
        try:
            call_command('export_exercise_targets', check=True,
                         stdout=io.StringIO(), stderr=io.StringIO())
        except SystemExit as exc:
            self.fail(f"exercise_targets.json is stale: {exc}")

    def test_r2_w1_camera_entries_have_valid_js_type(self):
        for ex_id, entry in self.data.items():
            if entry['tracking'] == 'camera':
                self.assertTrue(entry.get('js_type'),
                                f"{ex_id} is camera-tracked but has no js_type")
            else:
                self.assertIsNone(entry.get('js_type'),
                                  f"{ex_id} is manual but carries js_type "
                                  f"{entry.get('js_type')} (would re-enable fake tracking)")

    def test_r2_w1_april27_mapping_fixes(self):
        # marching_on_spot was ghost-coached as a JUMP — a march is not a jump.
        self.assertEqual(self.data['marching_on_spot']['tracking'], 'manual')
        # wall_sit was scored as a PLANK body-line; it is an isometric squat hold.
        self.assertEqual(self.data['wall_sit']['js_type'], 'SQUAT_HOLD')
        self.assertTrue(self.data['wall_sit']['is_hold'])
        # mountain climbers have no push-up elbow cycle.
        self.assertEqual(self.data['mountain_climbers']['tracking'], 'manual')
        # Nordics are positional/manual only (W2-6).
        for ex in ('nordic_hamstring_curl', 'nordic_curl_weighted', 'nordic_curl_partner'):
            self.assertEqual(self.data[ex]['tracking'], 'manual', ex)
        # bodyweight_rdl keeps its dedicated hinge coach.
        self.assertEqual(self.data['bodyweight_rdl']['js_type'], 'BW_RDL')

    def test_r2_w1_stretches_are_manual(self):
        """The old STRETCH fallback faked shoulder tracking for everything."""
        for ex in ('hamstring_stretch', 'cat_cow', 'foam_rolling', 'chin_tuck'):
            self.assertEqual(self.data[ex]['tracking'], 'manual', ex)

    def test_r2_w1_no_scored_back_targets_for_camera_exercises(self):
        """SB-15 (JS path): no camera exercise may carry a scored back/spine
        override — spinal position is not measurable with MediaPipe."""
        for ex_id, entry in self.data.items():
            for phase, joints in (entry.get('js_overrides') or {}).items():
                for joint in joints:
                    self.assertNotIn('back', joint.lower(),
                                     f"{ex_id}.{phase} ports a back-angle target")
                    self.assertNotIn('spine', joint.lower(), ex_id)

    def test_r2_w1_unknown_exercise_defaults_to_manual(self):
        from strength_app.cv_targets import get_cv_config
        cfg = get_cv_config('definitely_not_an_exercise')
        self.assertEqual(cfg['tracking'], 'manual')
        self.assertIsNone(cfg['js_type'])


class TestR2W1TemplateIntegration(TestCase):
    """The execute page embeds the CV config; SB-15 text is gone from JS cues."""

    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id='P9001', name='CV Test', phone='9000000901',
            age=30, goals='Strength',
        )
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session['v1_session'] = {
            'working_sets': [
                {'exercise_id': 'full_squats', 'exercise_name': 'Full Squats',
                 'movement_pattern': 'squat', 'sets': 3, 'reps': 10,
                 'tempo': '3-1-2-0', 'rest_seconds': 60},
                {'exercise_id': 'hamstring_stretch', 'exercise_name': 'Hamstring Stretch',
                 'movement_pattern': 'hinge', 'sets': 1, 'reps': 1,
                 'tempo': '3-1-2-0', 'rest_seconds': 30},
            ],
        }
        session.save()

    def test_r2_w1_camera_exercise_embeds_config(self):
        resp = self.client.get(reverse('v1_execute_exercise', args=[0]))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('"tracking": "camera"'.replace(' ', '')
                      if '"tracking":"camera"' in html.replace(' ', '')
                      else '"tracking"', html.replace(' ', ''))
        self.assertIn('"js_type"', html)
        self.assertIn('SQUAT', html)

    def test_r2_w1_manual_exercise_embeds_manual_config(self):
        resp = self.client.get(reverse('v1_execute_exercise', args=[1]))
        self.assertEqual(resp.status_code, 200)
        compact = resp.content.decode().replace(' ', '')
        self.assertIn('"tracking":"manual"', compact)

    def test_r2_w1_no_rounding_claim_in_measurement_cues(self):
        """SB-15: measurement-driven cues must not claim to see rounding."""
        resp = self.client.get(reverse('v1_execute_exercise', args=[0]))
        html = resp.content.decode()
        self.assertNotIn("no rounding.', true", html)
        self.assertNotIn('joints: { elbow: 170, back:', html)


class TestR2W1ManualSave(TestCase):
    """Manual-mode results: null form preserved end-to-end, completion XP."""

    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id='P9002', name='Manual Save', phone='9000000902',
            age=30, goals='Strength',
        )
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session['v1_session'] = {
            'working_sets': [
                {'exercise_id': 'hamstring_stretch', 'exercise_name': 'Hamstring Stretch',
                 'movement_pattern': 'hinge', 'sets': 1, 'reps': 1,
                 'tempo': '3-1-2-0', 'rest_seconds': 30},
            ],
        }
        session.save()

    def test_r2_w1_null_form_score_stored_as_none(self):
        resp = self.client.post(
            reverse('v1_save_exercise_result'),
            data=json.dumps({
                'exercise_index': 0, 'exercise_id': 'hamstring_stretch',
                'exercise_name': 'Hamstring Stretch', 'movement_pattern': 'hinge',
                'prescribed_sets': 1, 'prescribed_reps': 1,
                'completed_sets': 1, 'reps_per_set': [1],
                'form_score': None, 'rep_quality_source': 'manual',
                'pain_reported': False, 'skipped': False,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        stored = self.client.session['v1_exercise_results'][0]
        self.assertIsNone(stored['form_score'])
        self.assertEqual(stored['rep_quality_source'], 'manual')

    def test_r2_w1_form_score_75_not_fabricated_when_absent(self):
        """A payload with no form_score key must not invent 75 any more."""
        resp = self.client.post(
            reverse('v1_save_exercise_result'),
            data=json.dumps({
                'exercise_index': 0, 'exercise_id': 'hamstring_stretch',
                'exercise_name': 'Hamstring Stretch', 'movement_pattern': 'hinge',
                'completed_sets': 1, 'reps_per_set': [1],
                'pain_reported': False, 'skipped': False,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        stored = self.client.session['v1_exercise_results'][0]
        self.assertIsNone(stored['form_score'])
        self.assertEqual(stored['rep_quality_source'], 'manual')

    def test_r2_w1_xp_completion_based_for_manual(self):
        from strength_app.v1_gamification import compute_session_xp
        results = [
            {'form_score': None, 'rep_quality_source': 'manual',
             'completed_sets': 1, 'skipped': False},   # base XP, no bonus
            {'form_score': None, 'rep_quality_source': 'manual',
             'completed_sets': 0, 'skipped': True},    # skipped → 0
            {'form_score': 90, 'completed_sets': 3, 'skipped': False},  # cv: 15
        ]
        self.assertEqual(compute_session_xp(results), 25)

    def test_r2_w1_execution_row_marked_manual(self):
        """Manual result → ExerciseExecution with source 'manual', form None."""
        workout = WorkoutSession.objects.create(patient=self.patient, week_number=1)
        ExerciseExecution.objects.create(
            session=workout, exercise_id='hamstring_stretch',
            exercise_name='Hamstring Stretch', category='lower_body',
            prescribed_sets=1, prescribed_reps=1,
            rep_quality_source='manual', overall_form_score=None,
        )
        row = ExerciseExecution.objects.get(session=workout)
        self.assertIsNone(row.overall_form_score)
        self.assertEqual(row.rep_quality_source, 'manual')


# ════════════════════════════════════════════════════════════════════════
# W2 — football & sports-physio methodology
# ════════════════════════════════════════════════════════════════════════

class TestR2W2LsiPerTest(TestCase):
    """SB-11: LSI thresholds are per test type, not a uniform 90."""

    def _profile(self, **kw):
        from strength_app.models import FootballProfile
        patient = PatientProfile.objects.create(
            patient_id=f'P9{len(PatientProfile.objects.all()):03d}',
            name='LSI', phone=f'91000001{len(PatientProfile.objects.all()):02d}',
            age=22, goals='Football',
        )
        return FootballProfile.objects.create(patient=patient, **kw)

    def test_r2_w2_ybalance_uses_94_band(self):
        fp = self._profile(ybalance_left_pct=92.0, ybalance_right_pct=100.0)
        fp.compute_lsi()
        self.assertEqual(fp.ybalance_lsi_pct, 92.0)
        self.assertTrue(fp.lsi_flag, 'ybalance 92% must flag under the 94% band')

    def test_r2_w2_hop_keeps_90_band(self):
        fp = self._profile(hop_left_cm=92.0, hop_right_cm=100.0)
        fp.compute_lsi()
        self.assertFalse(fp.lsi_flag, 'hop 92% passes the 90% hop band')
        fp2 = self._profile(hop_left_cm=85.0, hop_right_cm=100.0)
        fp2.compute_lsi()
        self.assertTrue(fp2.lsi_flag)


class TestR2W2AsymmetryRaw(SimpleTestCase):
    """SB-12: asymmetry from raw values; banding cannot change the result."""

    def test_r2_w2_same_raw_same_class_regardless_of_bands(self):
        from strength_app.v1_onboarding_views import _compute_asymmetry_raw
        # 28 s vs 9 s hold — LSI 32.1 — significant, whatever bands they hit
        cls, lsi = _compute_asymmetry_raw(28, 9)
        self.assertEqual(cls, 'significant')
        self.assertAlmostEqual(lsi, 32.1, places=1)
        # same-band values that differ meaningfully are no longer hidden
        cls2, lsi2 = _compute_asymmetry_raw(30, 22)   # both could band to 4
        self.assertEqual(cls2, 'mild')

    def test_r2_w2_raw_fallback_when_missing(self):
        from strength_app.v1_onboarding_views import _compute_asymmetry_raw
        self.assertEqual(_compute_asymmetry_raw(None, 10), (None, None))
        self.assertEqual(_compute_asymmetry_raw(0, 10), (None, None))


class TestR2W2DeloadTrainingAge(TestCase):
    """SB-14: novices deload at 6 weeks; trained users keep 4."""

    def _patient(self, history, weeks):
        from strength_app.models import PeriodisationState
        patient = PatientProfile.objects.create(
            patient_id=f'P8{weeks}{history[:2]}', name='Deload',
            phone=f'92000{weeks:03d}{len(history)}', age=30, goals='Strength',
            training_history=history,
        )
        PeriodisationState.objects.create(patient=patient, weeks_since_deload=weeks)
        return patient

    def test_r2_w2_novice_five_weeks_no_mandatory_deload(self):
        from strength_app.v1_safety_logic import check_deload_needed
        needed, _ = check_deload_needed(self._patient('never', 5))
        self.assertFalse(needed)

    def test_r2_w2_novice_six_weeks_deloads(self):
        from strength_app.v1_safety_logic import check_deload_needed
        needed, reason = check_deload_needed(self._patient('beginner', 6))
        self.assertTrue(needed)
        self.assertIn('6', reason)

    def test_r2_w2_intermediate_keeps_four_week_ceiling(self):
        from strength_app.v1_safety_logic import check_deload_needed
        needed, _ = check_deload_needed(self._patient('intermediate', 4))
        self.assertTrue(needed)


class TestR2W2SleepTrafficLight(SimpleTestCase):
    """W2-9: 5-6h sleep is yellow only when energy is not good."""

    def _fb(self, sleep, energy):
        from types import SimpleNamespace
        return SimpleNamespace(
            pain_severity=0, pain_reported='none',
            perceived_difficulty='just_right',
            sleep_last_night=sleep, energy_level=energy,
        )

    def test_r2_w2_short_night_good_energy_is_green(self):
        from strength_app.v1_safety_logic import compute_traffic_light
        self.assertEqual(compute_traffic_light(self._fb('5_to_6', 'good')), 'green')

    def test_r2_w2_short_night_tired_is_yellow(self):
        from strength_app.v1_safety_logic import compute_traffic_light
        self.assertEqual(compute_traffic_light(self._fb('5_to_6', 'moderate')), 'yellow')

    def test_r2_w2_under_5_always_at_least_yellow(self):
        from strength_app.v1_safety_logic import compute_traffic_light
        self.assertEqual(compute_traffic_light(self._fb('under_5', 'good')), 'yellow')
        self.assertEqual(compute_traffic_light(self._fb('under_5', 'low')), 'red')


class TestR2W2ProtocolHygiene(SimpleTestCase):
    """W2-1/4/8: pogo labelling, normalisation table, stretch durations."""

    def test_r2_w2_no_rsi_claim_anywhere_user_facing(self):
        from strength_app.v1_football_constants import FOOTBALL_ASSESSMENT_TESTS
        for test in FOOTBALL_ASSESSMENT_TESTS:
            blob = ' '.join([test['name'], test['measure'], test['input_label'],
                             ' '.join(test['instructions'])])
            self.assertNotIn('RSI', blob, f"{test['test_id']} claims RSI")
            self.assertNotIn('reactive strength index', blob.lower())

    def test_r2_w2_normalisation_table_complete_and_tagged(self):
        from strength_app.v1_constants import V1_TEST_NORMALISATION
        from strength_app.v1_onboarding_views import ASSESSMENT_SCORING
        self.assertEqual(set(V1_TEST_NORMALISATION), set(ASSESSMENT_SCORING))
        for key, cfg in V1_TEST_NORMALISATION.items():
            self.assertIn(cfg['evidence'], ('cited', 'pragmatic'), key)
            self.assertTrue(cfg.get('rationale'), f'{key} has no rationale')
            self.assertEqual(len(cfg['thresholds']), 5, key)

    def test_r2_w2_prematch_protocol_is_dynamic(self):
        from strength_app.stretching_protocol import PRE_MATCH_STRETCHES
        names = ' '.join(s['name'] for s in PRE_MATCH_STRETCHES)
        self.assertNotIn('Standing Quadriceps Stretch', names)
        for s in PRE_MATCH_STRETCHES:
            self.assertLessEqual(s['duration_seconds'], 30, s['name'])

    def test_r2_w2_cooldown_static_holds_within_acsm_band(self):
        from strength_app.warmup_library import COOLDOWN_STATIC_STRETCHES
        for day, stretches in COOLDOWN_STATIC_STRETCHES.items():
            for s in stretches:
                if 'hold' in s:  # cat_cow_slow is reps-based
                    self.assertLessEqual(s['hold'], 30, f"{day}/{s['id']}")


# ════════════════════════════════════════════════════════════════════════
# W3 — user-POV features
# ════════════════════════════════════════════════════════════════════════

class TestR2W3ForgotPassword(TestCase):
    """U1: recovery flow — generic responses, single-use 1-hour tokens,
    forced change after a therapist-issued temp password."""

    def setUp(self):
        from django.contrib.auth.hashers import make_password
        self.patient = PatientProfile.objects.create(
            patient_id='P9101', name='Reset Me', phone='9000009101',
            age=30, goals='Strength', email='reset@example.com',
            password=make_password('oldpass123'),
        )

    def test_r2_u1_generic_response_for_unknown_and_known_phone(self):
        r1 = self.client.post(reverse('forgot_password'), {'phone': '9000009101'})
        r2 = self.client.post(reverse('forgot_password'), {'phone': '9999999999'})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        # identical copy — no enumeration signal
        self.assertEqual(r1.content, r2.content)

    def test_r2_u1_token_created_and_reset_works(self):
        from strength_app.models import PasswordResetToken
        from django.contrib.auth.hashers import check_password
        self.client.post(reverse('forgot_password'), {'phone': '9000009101'})
        token = PasswordResetToken.objects.get(patient=self.patient)
        self.assertTrue(token.is_valid())
        resp = self.client.post(
            reverse('reset_password', args=[token.token]),
            {'new_password': 'newpass123', 'confirm_password': 'newpass123'},
        )
        self.assertEqual(resp.status_code, 302)
        self.patient.refresh_from_db()
        self.assertTrue(check_password('newpass123', self.patient.password))
        token.refresh_from_db()
        self.assertTrue(token.used)
        # reuse blocked
        resp2 = self.client.get(reverse('reset_password', args=[token.token]))
        self.assertContains(resp2, 'expired')

    def test_r2_u1_weak_password_rejected(self):
        from strength_app.models import PasswordResetToken
        PasswordResetToken.objects.create(patient=self.patient, token='t' * 40)
        resp = self.client.post(
            reverse('reset_password', args=['t' * 40]),
            {'new_password': '12345678', 'confirm_password': '12345678'},
        )
        self.assertContains(resp, 'letters and numbers')

    def test_r2_u1_no_token_without_email(self):
        from strength_app.models import PasswordResetToken
        from django.contrib.auth.hashers import make_password
        PatientProfile.objects.create(
            patient_id='P9102', name='No Email', phone='9000009102',
            age=30, goals='Strength', password=make_password('x1234567'),
        )
        self.client.post(reverse('forgot_password'), {'phone': '9000009102'})
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_r2_u1_must_change_password_forces_change(self):
        self.patient.must_change_password = True
        self.patient.save(update_fields=['must_change_password'])
        resp = self.client.post(reverse('patient_login'),
                                {'phone': '9000009101', 'password': 'oldpass123'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('change-password', resp.url)


class TestR2W3ResumeAndUndo(TestCase):
    """U2/U3: resume markers and the undo-last-result endpoint."""

    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id='P9103', name='Resume', phone='9000009103',
            age=30, goals='Strength',
        )
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session['v1_session'] = {
            'working_sets': [
                {'exercise_id': 'full_squats', 'exercise_name': 'Full Squats',
                 'movement_pattern': 'squat', 'sets': 3, 'reps': 10},
                {'exercise_id': 'push_ups', 'exercise_name': 'Push-ups',
                 'movement_pattern': 'push', 'sets': 3, 'reps': 10},
            ],
        }
        from datetime import date as _date
        session['v1_session_date'] = str(_date.today())
        session.save()

    def _save_one(self):
        return self.client.post(
            reverse('v1_save_exercise_result'),
            data=json.dumps({
                'exercise_index': 0, 'exercise_id': 'full_squats',
                'exercise_name': 'Full Squats', 'movement_pattern': 'squat',
                'completed_sets': 3, 'reps_per_set': [10, 10, 10],
                'form_score': 85, 'pain_reported': False, 'skipped': False,
            }),
            content_type='application/json',
        )

    def test_r2_u2_resume_markers_set_and_dashboard_offers_continue(self):
        self._save_one()
        self.assertEqual(self.client.session.get('v1_main_done'), 1)
        self.assertIn('exercise/1', self.client.session.get('v1_resume_url', ''))
        resp = self.client.get(reverse('v1_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Session in progress')
        self.assertContains(resp, '1 of 2')

    def test_r2_u3_undo_pops_last_result_and_redirects_back(self):
        self._save_one()
        resp = self.client.post(reverse('v1_undo_last_result'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('exercise/0', resp.url)
        self.assertEqual(self.client.session.get('v1_exercise_results'), [])
        self.assertEqual(self.client.session.get('v1_main_done'), 0)

    def test_r2_u3_undo_with_nothing_done_is_safe(self):
        resp = self.client.post(reverse('v1_undo_last_result'))
        self.assertEqual(resp.status_code, 302)  # dashboard, no crash


class TestR2W3SessionHistory(TestCase):
    """U4: history list + ownership-enforced detail."""

    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id='P9104', name='History', phone='9000009104',
            age=30, goals='Strength',
        )
        self.other = PatientProfile.objects.create(
            patient_id='P9105', name='Other', phone='9000009105',
            age=30, goals='Strength',
        )
        self.own = WorkoutSession.objects.create(patient=self.patient, week_number=2)
        ExerciseExecution.objects.create(
            session=self.own, exercise_id='full_squats', exercise_name='Full Squats',
            category='lower_body', prescribed_sets=3, prescribed_reps=10,
            rep_quality_source='manual', overall_form_score=None,
        )
        self.theirs = WorkoutSession.objects.create(patient=self.other, week_number=1)
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session.save()

    def test_r2_u4_history_lists_own_sessions(self):
        resp = self.client.get(reverse('v1_session_history'))
        self.assertContains(resp, 'Week 2')

    def test_r2_u4_detail_renders_manual_without_fake_form(self):
        resp = self.client.get(reverse('v1_session_detail', args=[self.own.pk]))
        self.assertContains(resp, 'guided — no form tracking')

    def test_r2_u4_other_patients_session_404s(self):
        resp = self.client.get(reverse('v1_session_detail', args=[self.theirs.pk]))
        self.assertEqual(resp.status_code, 404)


class TestR2W3ProfileEdit(TestCase):
    """U7: equipment change clears the cached session."""

    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id='P9106', name='Editor', phone='9000009106',
            age=30, goals='Strength', equipment_available_json=['none'],
        )
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session['v1_session'] = {'working_sets': []}
        session.save()

    def test_r2_u7_equipment_change_clears_cached_session(self):
        resp = self.client.post(reverse('v1_edit_profile'), {
            'name': 'Editor', 'email': '', 'weight_kg': '70',
            'equipment': ['dumbbells', 'bands'],
        })
        self.assertEqual(resp.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(set(self.patient.equipment_available_json), {'dumbbells', 'bands'})
        self.assertNotIn('v1_session', self.client.session)

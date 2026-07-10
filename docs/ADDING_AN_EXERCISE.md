# Adding an Exercise — the 30-minute playbook

Two paths. **Default is GUIDED** (no camera). Camera tracking is added ONLY
after the exercise passes the filming protocol (`docs/FILMING_PROTOCOL.md`)
— never before. Every step below names the exact file and the command that
proves it worked.

---

## Path 1 — GUIDED exercise (therapist-prescribable, ~10 minutes)

A guided exercise needs no Python module, no CV work, no template change.

1. **Catalog entry** — `therapist_app/exercise_catalog.py`, append to
   `EXERCISES` (copy the `ex_ankle_pumps` entry at ~line 372 as the shape):
   ```python
   {
       "exercise_id": "ex_<snake_name>",       # unique, ex_ prefix
       "name": "<Display Name>",
       "movement_pattern": "<Squat|Hinge|Push|Pull|Core|Mobility|Balance>",
       "equipment": "<None|Light band|…>",
       "video_url": "",                         # YouTube embed URL or ""
       "v2_ghost_supported": False,             # guided = False, always
       "v2_exercise_key": "",
       "description": "<2–4 sentences a patient can follow. Plain words, "
                      "start position → movement → what to feel. This IS "
                      "the patient-facing instruction on the guided screen.>",
       "default_sets": 3,
       "default_reps": 12,
       "default_rest_seconds": 45,
   }
   ```
2. **Verify** (all from repo root):
   ```
   python manage.py check                       # catalog imports clean
   python manage.py test therapist_app strength_app.tests.test_c_therapist_note
   python manage.py export_exercise_targets --check   # must still say "fresh"
   ```
   (`--check` stays fresh because guided catalog entries are not in the CV
   registry — if it says stale you touched the wrong file.)
3. **Smoke in browser**: therapist builder → add the exercise → Publish →
   patient today page shows it → open it: guided screen with description,
   set tracker works, "Set done" posts a guided `ExerciseSetLog` row
   (check `/admin/therapist_app/exercisesetlog/`).

That's it. Do NOT touch `exercise_targets.json`, the export command, or any
JS for a guided exercise.

> Self-serve engine note: only if the exercise should ALSO be prescribable
> by the athlete/self-serve engine does it need entries in
> `strength_app/v1_progression_chains.py`, `strength_app/exercise_content.py`
> (or `exercise_content_gap_fill.py`) and
> `strength_app/equipment_routing.py:EXERCISE_EQUIPMENT_REQUIRED` — the
> `TestDAP3DataIntegrity` tests enforce that trio. Therapist-only guided
> exercises skip all of this.

---

## Path 2 — CAMERA exercise (~30 minutes, AFTER filming protocol passes)

**Decision rule (locked):** camera tracking ships only when the movement
passed `docs/FILMING_PROTOCOL.md` on a real device. Until then it ships as
guided (Path 1) — honest guided beats fake tracking. Adding a NEW ghost
phase template no longer touches the frozen camera template: since 2026-07,
new `js_type` definitions + fault observers go in
`strength_app/static/strength_app/js/coach_dark.js` (UMD, node-tested in
`coach_dark.test.mjs`; `install()` merges them without ever overwriting an
audited live key). Prefer reusing an existing audited `js_type` when one
matches the movement; a coach can also ship DARK behind a `*_rx` key with
the catalog flag False — see "Dark camera coaches" in CLAUDE.md for the
pattern and flip procedure.

1. **Python module** — `strength_app/exercise_system/exercises/<name>_v2.py`.
   Copy the nearest sibling (e.g. `static_glutei_v2.py` for a hold,
   `glute_bridge_v2.py` for a rep cycle) and adjust angles/phases. Keep the
   module import pattern identical (it imports `cv2` at top — desktop-only
   is expected; the web never imports these modules at request time).
2. **Package export** — `strength_app/exercise_system/exercises/__init__.py`:
   add the import line, matching the existing pattern.
3. **Registry** — `strength_app/exercise_system/exercise_registry_v2.py`:
   import the class (~line 32 block) and add the `EXERCISE_METADATA` entry
   (~line 320; copy shape):
   ```python
   '<snake_name>': {
       'class': <ClassName>,
       'category': 'strength',            # strength|mobility|balance|…
       'subcategory': 'foundation',
       'level': 2,
       'display_name': '<Display Name>',
       'unilateral': False,
       'movement_pattern': 'squat',
   },
   ```
4. **Tracking verdict** —
   `strength_app/management/commands/export_exercise_targets.py`:
   - Verified on camera per the filming protocol → add
     `'<snake_name>': '<JS_TYPE>'` to the `CAMERA` dict (line ~62),
     where `<JS_TYPE>` is an EXISTING audited `EXERCISE_PHASES` key
     (`SQUAT`, `SQUAT_SINGLE`, `GLUTE_BRIDGE_SUPINE`, `LUNGE_SPLIT`, …).
   - Not yet verified → add the id to the appropriate `MANUAL` set
     (line ~145 blocks) with a one-line comment saying why.
   Every registry id MUST land in exactly one of the two tables — the
   command errors on unknown ids.
5. **Regenerate the artifact** (the single source of truth for the web):
   ```
   python manage.py export_exercise_targets            # writes the JSON
   python manage.py export_exercise_targets --check    # now says "fresh"
   python manage.py collectstatic --noinput            # manifest storage!
   ```
   Commit `strength_app/static/strength_app/js/exercise_targets.json`
   together with the code change — `--check` is the CI gate.
6. **Patient-facing content** — `strength_app/exercise_content.py` (or
   `exercise_content_gap_fill.py`), keyed by the SNAKE id. The REAL keys are
   `instructions` (list of sentences), `form_cues` (list) and
   `mind_muscle_cue` (dict with a `during` entry) — this doc previously said
   `*_en` keys, which exist in ZERO entries (2026-07 exam finding A8; the
   views that still read `*_en` are a known deferred fix gated on a mentor
   pass — see CODEBASE_HEALTH_2026-07.md).
7. **Therapist catalog** — `therapist_app/exercise_catalog.py` entry as in
   Path 1 but with `"v2_ghost_supported": True,
   "v2_exercise_key": "<snake_name>"`.
8. **Tests that must go green** (in this order — each catches a different
   mistake):
   ```
   python manage.py test strength_app.tests.test_deep_audit.TestDAH3RegistryIntegrity   # registry shape
   python manage.py test strength_app.tests.test_deep_audit.TestDAH2IdealTrajectoryInvariant  # module scores >=85 on its own ideal trajectory
   python manage.py test strength_app.tests.test_deep_audit.TestDAP3DataIntegrity       # content/equipment coverage (if in chains)
   python manage.py test                                                                # full suite
   node --test strength_app/tests/js/cv_core.test.mjs
   ```
   H2 threshold is ≥85 (`test_deep_audit.py:733`) — if your module can't
   score its own ideal trajectory, the phase targets are wrong; fix the
   module, never the harness.
9. **Checklist row** — `docs/EXERCISE_TEST_CHECKLIST.md`: add the row
   (exercise · js_type · synthetic score · JS-verified? · filmed?). The
   H2 per-module score appears in
   `strength_app/tests/clinical_audit/reports/H2_RESULTS.md` after the H2
   test runs.
10. **Device smoke** (append result to `MASTER_TEST_DAY.md` Part F):
    therapist publishes it → patient opens it → Start Camera → framing →
    reps count on real movement, form % responds, no console errors —
    and the **squat re-test** afterwards (any camera-table change warrants
    the showpiece check).

## The commit shape

One exercise = one commit:
`feat(exercise): <snake_name> — <guided|camera:JS_TYPE>` containing the
module+registry+export-table+JSON (camera) or the catalog entry (guided),
plus content and checklist row. `export --check` green in the same commit.

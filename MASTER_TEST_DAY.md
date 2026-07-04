# VYAYAM — MASTER TEST DAY (on-device walk)

The consolidated device test for everything shipped through the pitch-polish
(G0–F), security, and report/coaching (R1–R5) cycles. **The R4 coaching layer
is frozen until this passes.** Run on a real phone/laptop camera, console
open where possible. Tick every box; anything that fails gets a note with
what you saw. Budget ~90 minutes.

Credentials (after seeding): therapist `dr_shah / simple` at
`/therapist/login/` · patient `9000000001 / patient` (Anika) at `/login/`.

---

## Part A — Environment prep (10 min)

- [ ] `git pull` → branch `ship-ready-2026-06`, clean tree
- [ ] `python manage.py migrate` → "No migrations to apply"
- [ ] `python manage.py collectstatic --noinput` → exit 0 (manifest storage
      — camera pages 500 without this)
- [ ] `python manage.py test` → 312+ OK ·
      `node --test strength_app/tests/js/*.test.mjs` → 25+ pass
- [ ] `python manage.py seed_therapist_demo` (demo DB only, never prod)
- [ ] Fresh server start (`python manage.py runserver` or the deploy URL) —
      the G0 dead-buttons incident was a stale server; always restart
- [ ] Phone and laptop both reach the server over HTTPS or localhost
      (camera requires a secure context)

## Part B — PITCH_SMOKE walk (30 min)

- [ ] Run `PITCH_SMOKE.md` steps **1–23** in order, ticking there.
      Sections: therapist edit+publish (1–3) · full patient session, every
      button (4–14) · therapist message+alert (15–16) · squat showpiece
      (17–18) · self-serve stop parity (19) · report+coaching cycle (20–23).
- [ ] Extra G1 tier check while in step 10–11: severity **4** → green
      "within your usual range"; **6** → skip + chat message, NO alert;
      **8** → pause + chat ⚠ + one inbox alert. Repeat 8 on the same
      exercise within 10 min → chat message but NO duplicate alert;
      mark reviewed → next 8 alerts again.
- [ ] Phase D check at step 6: after Start Camera + framing, you land
      STRAIGHT in ("Ready. Step into the outline…"). **Show demo** works
      both before camera start (placeholder button) and mid-exercise
      (status-card button), and hands back to work.
- [ ] Phase E check at step 7: tempo chip colors — blue lowering, amber
      hold, green up; clamshell (`—` tempo) shows NO tempo card, no chip,
      no crash.
- [ ] Phase F check: the coach voice sounds natural on this device
      (Chrome/Android = Google voice; Safari = Samantha/Ava). Toggle the
      speaker icon off → silence; on → resumes.

## Part C — The deliberately-sloppy coaching session (R4, 20 min)

On a camera exercise (squat or glute bridge), one continuous set sequence:

- [ ] **Calibration**: first thing after "now you try" you hear "Let's see
      your natural movement first"; 2 reps with NEUTRAL skeleton (no
      green/amber/red), no cues; colors come alive on rep 3, scored to
      YOUR depth (a shallow mover should be able to reach green)
- [ ] **Safety cue + red**: let knees cave once → ONE "Knees toward the
      camera", skeleton may show red ONLY now
- [ ] **Correction praise**: fix it → next rep "Better — knees are
      tracking now", then silence on that cue
- [ ] **3-strike fade**: deliberately ignore a cue for 3 reps → one
      "Let's slow down — quality over count", then that cue stays silent
      for the set
- [ ] **One praise per set**: 3 clean reps → exactly one praise line;
      different wording next set
- [ ] **Confidence gate**: step half out of frame ~2 s → grey skeleton +
      "I can't see you clearly — step back a little" (once); no cues, no
      reds until you're back
- [ ] **Tempo loop (3-1-1 or similar)**: "Slowly down — 3… 2… 1 · Hold ·
      Up" every rep; counting PAUSES while a cue/praise speaks; resumes
      next rep; tempo deviation NEVER changes any color; at most one
      "a bit quick" adjust line per set
- [ ] **Fatigue tone**: extend rest +30s twice → next set opens "Last set —
      steady and controlled"; only safety cues after that
- [ ] **One voice throughout**: never two lines talking over each other
- [ ] **Assessment unchanged**: run one camera assessment — NO calibration
      line, NO adjusted targets, scores as before

## Part D — Capture rows in /admin (10 min)

As dr_shah at `/admin/` after the Part B/C sessions:

- [ ] `Therapist_app → Exercise set logs`: one row per set; camera rows
      have `reps_json` (per-rep form %, phase ms, bottom angle, cues with
      corrected flags); guided rows have count only, empty reps; the
      exercise you demoed has `demo_viewed=True`
- [ ] `Strength_app → Rest events`: your +30s taps (context between_sets),
      the skipped rest (`cut_short=True`), the pause (context `pause`,
      duration right ±5 s), all tied to the session log
- [ ] `Strength_app → Pain events`: severity/type/threshold/outcome rows;
      the camera-exercise report has BOTH `set_number` and `rep_number`;
      the guided one has rep_number empty
- [ ] `Therapist_app → Session reports`: one per finished session,
      statuses correct (`complete` / `ended early — pain`), no duplicates
      after revisiting the finished page

## Part E — The report, both sides + print (10 min)

- [ ] Patient: finished page → "View today's session report"; Progress →
      Session reports card → same report
- [ ] The pain line reads exactly like "aching 4/10 at rep 6 of set 2 —
      noted, session continued"
- [ ] Exercise header shows BOTH clocks: "N:NN elapsed · N:NN working"
- [ ] Your obeyed cue: "corrected within a rep each time"; the ignored
      one: "persisted after cueing — flagged for review" (+ in For review)
- [ ] Rest column: "+30s extended" on the right set, "paused Ns", "cut
      short" where you skipped
- [ ] Guided exercise block says "guided (self-reported)" with NO form/
      depth/tempo numbers (dashes)
- [ ] Therapist: patient → Reports tab → Session reports list (status
      chips, completion %, safety badge on the pain-stopped one) → Open →
      IDENTICAL document
- [ ] Safety-stopped session's report: red banner ABOVE the narrative
- [ ] Cmd+P print preview: nav/buttons gone, clean clinical document
- [ ] Footer disclaimer present on every report

## Part F — Final squat + console pass (10 min)

- [ ] Full squat set start→finish: framing → straight in → calibration →
      reps count on real movement → form % moves with depth → ghost
      tracks → voice coaches → Set done → rest → finish
- [ ] Browser console: ZERO red errors across the entire session
      (screenshot anything red with the URL visible)
- [ ] `python manage.py test` once more after the device day — still green
- [ ] Sign here: date + device + browser + "PASS" or the failure list

**On full PASS: the camera/coaching freeze lifts.** File any failure as a
bug with console text + the exact step number from this document.

---
*Every future phase appends its manual steps to this file (standing rule 8).*

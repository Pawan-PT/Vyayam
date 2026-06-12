# VYAYAM Football & Sports-Physio Methods — a study document

*Written 2026-06 (Run 2) for Pawan: you have not studied sports physiotherapy
yet — this explains what the app's football tier does, **why**, what the
evidence is, and exactly where we are being pragmatic rather than
evidence-based. Every claim is tagged. Where a citation says "commonly cited
as", I am confident the body of work exists but you should verify the exact
reference before repeating it to a sports physio. There are no invented
references in this document.*

**Citation tags used throughout:**
- **[cited]** — a real, well-known body of literature; the named source is
  the conventional anchor for the claim. Verify the exact paper before
  quoting it formally.
- **[pragmatic]** — our own clinically-reasoned default. Defensible, but a
  sports physio could legitimately choose a different number.
- **[contested]** — the literature genuinely disagrees; we took the
  conservative side.

---

## 1. Why footballers get hurt, and what this app tries to do about it

Most non-contact football injuries cluster in four tissues: **hamstrings**
(sprinting), **ACL** (cutting/landing), **groin/adductors** (kicking and
change of direction), and **tendons** (Achilles, patellar — from repeated
high-velocity loading). The app's football tier is built around the
best-supported *modifiable* risk factors:

1. **Eccentric hamstring strength** — the hamstring is injured while
   lengthening under load at high sprint speed. Programmes built around the
   Nordic hamstring exercise reduce hamstring injury incidence — this is one
   of the most replicated findings in sports medicine **[cited — commonly
   cited as the Nordic-programme trials and meta-analyses, e.g. van der Horst
   et al. 2015; Petersen et al. 2011; pooled analyses around ~50% incidence
   reduction in compliant groups]**.
2. **Tendon load tolerance** — tendons adapt to slow, heavy loading, and
   degrade under sudden spikes of explosive work they're not prepared for.
   Heavy Slow Resistance is the rehabilitation/preparation protocol with the
   strongest tendon evidence **[cited — Kongsgaard et al., HSR for patellar
   tendinopathy, ~2009-2010 trials]**.
3. **Landing mechanics and asymmetry** — large left-right differences in hop
   performance and poor landing control (knee valgus, stiff landings) are
   associated with lower-limb injury risk; neuromuscular warm-up programmes
   reduce injuries **[cited — commonly cited as the FIFA 11+ trials]**.
4. **Load management** — sudden spikes in training load relative to what the
   athlete is prepared for precede injuries. NOTE: the specific ACWR
   (acute:chronic workload ratio) metric is methodologically criticised and
   **deliberately excluded from this app** (standing decision R2 from Run 1)
   **[contested — the original Gabbett-era ACWR work vs. the statistical
   critiques, commonly cited as Impellizzeri et al.]**. We manage load with
   periodisation phases, mandatory deloads, and symptom-led traffic lights
   instead — structures, not a pseudo-precise ratio.

**The framing rule (standing):** V1's athlete tier is *training-readiness*
framing only. It never diagnoses, never claims return-to-sport authority,
and the patient-facing copy says "decision support" things, never clinical
conclusions.

---

## 2. The 6-test assessment battery — what each test measures

All six are field tests an amateur can do with a phone, a tape measure, and
a stopwatch. Each is scored 1–5 by thresholds in `v1_football_constants.py`
(`FOOTBALL_ASSESSMENT_TESTS`); the athlete's **football level (1–5)** is the
*average* of test scores, and gates what training content unlocks.

| Test | What it actually measures | Threshold provenance |
|---|---|---|
| Single-leg hop for distance (L/R) | Unilateral explosive force + landing confidence; feeds LSI | bands [pragmatic]; the test itself is a standard hop battery item [cited] |
| Nordic hold (self-timed seconds) | Eccentric hamstring capacity — how long you can resist the fall | bands [pragmatic] |
| 20 m sprint | Maximal acceleration/speed | bands [pragmatic — typical amateur times] |
| Pogo 10 s count | **App reactivity count** (see §4 — NOT RSI) | bands [pragmatic] |
| 505 change-of-direction (L/R) | Deceleration + re-acceleration each pivot side; feeds LSI | the 505 test is standard [cited]; bands [pragmatic] |
| Y-balance anterior reach (L/R, % limb length) | Dynamic single-leg control; feeds LSI | the test and the ~4 cm anterior asymmetry risk marker are commonly cited as Plisky et al. 2006 [cited]; our % bands [pragmatic] |

**Honesty note:** all raw values are self-measured/self-timed by the athlete
or a coach with a phone. Expect ±10–20 % noise versus laboratory testing.
That is exactly why the app uses these scores to pick *training bands*, not
to make clinical claims.

---

## 3. LSI — Limb Symmetry Index (SB-11/12)

**What it is.** LSI = (weaker side ÷ stronger side) × 100. It is the
standard field expression of left-right asymmetry, historically from ACL
rehabilitation hop testing, where **≥90 % on hop batteries** is the
conventional symmetry benchmark **[cited — commonly cited as Noyes et al.
1991 and the subsequent hop-test literature]**.

**Per-test bands as implemented** (`LSI_THRESHOLDS`):
- hop distance ≥ **90 %** [cited convention]
- 505 COD time ≥ **90 %** [pragmatic — no established band for time-based
  L/R 505 comparison; we mirror the hop convention]
- Y-balance ≥ **94 %** [pragmatic conversion of the cited >4 cm anterior
  reach-difference risk marker into a percentage]

**The known limitation you must be able to say out loud to a physio:** LSI
is a *ratio*. An athlete who is weak on BOTH legs passes LSI perfectly.
That's why the app pairs LSI (asymmetry screen) with the 1–5 capability
scores (absolute capacity screen) and shows the caveat to coaches. LSI in
uninjured athletes is also naturally noisy — dominant-leg differences of
5–10 % are normal, which is why the bands are not tighter.

**Onboarding 7-test screen (non-football, SB-12).** The same logic now
applies to the home user's bilateral tests (hinge/lunge/rotate holds):
asymmetry is computed as (weak/strong)×100 **on raw hold seconds**, with
wider bands than hop tests (≥85 none / 70–84 mild / 55–69 moderate / <55
significant) because self-timed holds are noisier than measured hop
distances [pragmatic]. The old method compared 1–5 *score bands*, which both
hid real gaps (both sides in one band) and exaggerated trivial ones
(adjacent bands across a boundary). Band-gap comparison survives only as a
fallback when raw values are missing, and every result is labelled with the
method that produced it.

---

## 4. The pogo test and why we refuse to call it RSI (SB-9)

**What RSI is.** Reactive Strength Index = jump height (or flight time) ÷
ground-contact time, measured on a contact mat or force plate during drop
jumps. It quantifies the stretch-shortening cycle — the spring-like tendon
behaviour elite jumpers/sprinters have. Typical measurement needs contact
times resolved to ~milliseconds.

**Why we can't measure it.** A phone camera at 30 fps has ~33 ms per frame;
ground contacts in reactive hopping are 130–250 ms. Frame-counting gives
±25 % error on contact time before pose-estimation noise. A self-counting
athlete can't judge 200 ms at all.

**What we do instead.** The pogo test is an **app-specific reactivity
count**: springy reps in 10 seconds, where "springy" is defined behaviourally
(bounce, don't squat; knees nearly straight; heels barely touch). It
correlates with the quality RSI measures — ankle-dominant elasticity — but it
is not RSI, and no label, instruction, or coach view uses that term
(test-enforced). If VYAYAM ever wants true RSI, the path is a contact mat or
validated high-fps video analysis, with an error analysis — not a rename.

---

## 5. Nordic hamstring work (SB-4) — what V1 ships

**Why Nordics matter.** See §1: Nordic-based programmes roughly halve
hamstring injury incidence in compliant teams **[cited — Nordic programme
literature]**. The exercise trains the hamstring to produce force while
lengthening — exactly the sprint-swing-phase mechanism of injury.

**The break-point concept.** In a clinic, Nordic capacity is assessed by the
*break-point angle* — how far forward the athlete can lower before the
hamstrings give out — or by force output on a NordBord-style device. Both
need instrumentation or a trained eye.

**What V1 does (and doesn't).** The app records a **self-timed eccentric
hold** ("seconds until your hands touch the floor") and bands it 1–5. The
exercise's live page runs in **guided (manual) mode** — there is NO camera
score for Nordics, because the kneeling fall doesn't match any verified
tracking template, and a wrong score on a maximal eccentric is exactly where
false confidence hurts. The input is labelled self-timed. A camera
break-point estimate is possible future work but requires a validation plan
(film vs. goniometer comparison) before it may show a number.

---

## 6. Heavy Slow Resistance (HSR) and the 6-0-6-0 tempo (SB-7)

**What HSR is.** Heavy loads moved deliberately slowly — in the canonical
patellar-tendinopathy trials, ~6 seconds per rep phase, 3–4 sets, 2–3×/week
**[cited — Kongsgaard et al.]**. The slow tempo keeps peak tendon strain
high but rate-of-loading low, which drives tendon adaptation without the
spike that aggravates it.

**As implemented** (`HSR_PHASES`):
- Phase 1 (4 wk): 3 × 6-8 @ **6-0-6-0** tempo — load introduction
- Phase 2 (4 wk): 4 × 4-6 @ **6-0-6-0** — progressive loading
- Phase 3 (4 wk): 4 × 3-5 @ **3-0-3-0**, frequency drops to 2×/wk — peak
  stiffness + reactive work introduced [pragmatic phase structure; the
  tempo and slow-heavy principle are the cited part]

Tempo notation is E-P-C-T: eccentric-pause-concentric-top, in seconds. So
6-0-6-0 = 6 s down, no pause, 6 s up. Run 1 fixed cue strings that
described this wrong (SB-7).

**The HSR anchor bug you should understand (SB-5, fixed in Run 1):** phase
advancement requires ≥4 weeks *in the phase*. The "weeks in phase" anchor
was stored as 0-means-unset, and a falsy check re-anchored every athlete to
week 0 on every session — so nobody could EVER advance. It is now a nullable
field with an explicit `is None` check. Lesson: sentinel values that are
also valid values corrupt gates silently.

---

## 7. Plyometric progression and the gate tree (SB-1)

Plyometrics (jump/landing work) are the highest-tissue-stress content in the
app, so they sit behind a **fail-closed** gate (`check_plyometric_gate`):
missing data ⇒ NOT cleared. Tiers must be cleared in order:

```
none ──► low_load          (level ≥2, hop LSI ≥80, hop score ≥2, pain ≤2/10)
         pogo, skipping, lateral shuffle
     ──► moderate_load     (level ≥3, hop LSI ≥85, hop ≥3, nordic ≥3, pain ≤1)
         box jumps, hurdle hops, broad jump, single-leg hop
     ──► high_load         (level ≥4, hop LSI ≥90, hop ≥4, nordic ≥4,
         depth jumps,       sprint ≥3, pain 0)
         reactive SL hops
```

The *structure* (graded exposure, eccentric/strength prerequisites before
reactive load, pain as a hard gate) is standard plyometric-progression
practice **[cited as convention in strength & conditioning texts]**; the
specific numbers are ours **[pragmatic]**. Note the Nordic prerequisite:
hamstring eccentric capacity before high-velocity bounding — that ordering
is the defensible core.

Additionally, the *camera* coaches for the six dedicated plyo exercises
check two landing faults in real time: knee valgus (knees collapsing
inward — the classic ACL mechanism) and stiff-knee landings (>160° at
contact — poor force absorption). These produce voice warnings, never
scores.

---

## 8. Periodisation, the in-season microcycle, and deloads (SB-14)

**Phases.** Off/pre/in/post-season phases wave volume and intensity
(accumulation → intensification → realisation → deload). This is block-
periodisation convention **[cited — commonly cited as Issurin's block
periodisation reviews and Bompa's periodisation texts; convention more than
RCT evidence — say this honestly]**. All modifiers are within ±30 % and the
big ones REDUCE load approaching competition.

**Match microcycle (MD-x).** With a match calendar, sessions adapt by
days-to-match. As implemented: MD+1 recovery, MD+2 return-to-training,
**MD-4 strength (the big day), MD-3 power/speed, MD-2 light activation,
MD-1 neural prime (minimal)**, match day = rest/no prescription. This
matches the commonly described elite one-match-week structure (hardest
physical work 3–4 days out, taper in) **[cited as common practice in
football S&C literature; exact mapping pragmatic]**. Double gameweeks
collapse everything to light/prime days.

**Deloads.** Planned reduced-load weeks. The app forces one:
- every **4 weeks** for intermediate/advanced users,
- every **6 weeks** for novices (training_history never/tried/beginner) —
  novices train at loads that accumulate less systemic fatigue, so a hard
  4-week stop was a blunt instrument **[pragmatic; periodisation convention,
  not trial evidence — both intervals]**;
- **immediately** regardless of calendar if feedback triggers fire
  (≥2 red traffic lights or ≥2 moderate/severe pain reports in the last 5
  sessions). Feedback always wins over calendar.

---

## 9. Recovery inputs: sleep, stress, hormonal phase (W2-9)

- **Sleep**: <5 h ⇒ session yellow on its own; <5 h + low energy ⇒ red;
  5–6 h ⇒ yellow only when energy is also not good. Sleep restriction
  degrading performance/recovery is well replicated **[cited — sleep &
  athletic performance reviews]**; our exact volume reductions (0.6–0.85)
  are **[pragmatic]**.
- **Stress**: high/very-high reported stress trims volume 15–30 %
  **[pragmatic; direction commonly cited as Stults-Kolehmainen & Sinha
  2014]**.
- **Menstrual cycle**: the performance literature is **[contested]** —
  meta-analyses (commonly cited as McNulty et al. 2020) find trivial,
  inconsistent phase effects. V1 therefore makes NO performance claims:
  menstruation-phase reductions are *symptom-led* (the athlete's own
  reported severity drives 0–100 % volume), which is autoregulation, not
  cycle pseudoscience; the ovulation plyometric block reflects the
  laxity/ACL-risk hypothesis and we accept it may be over-cautious.
  Nothing in this family ever INCREASES load.

---

## 10. Stretching (W2-8)

- **Pre-match: dynamic only.** Sustained static stretching immediately
  before explosive work acutely reduces power/sprint performance, with the
  effect growing for holds ≥60 s **[cited — commonly cited as the Simic et
  al. 2013 meta-analysis and successors]**; a dynamic warm-up is standard
  pre-match practice. The previous protocol opened with 4×30 s static
  holds — replaced with movement-matched dynamic equivalents (lunge-with-
  reach, walking quad pulls, hamstring sweeps, rocking calf stretch).
- **General flexibility statics** (cooldowns, mobility work): 15–30 s holds
  × multiple sets, consistent with ACSM-style flexibility guidance
  **[cited as guidance]**. All cooldown holds are now capped at 30 s with
  set counts raised to preserve total stretch time.

---

## 11. The constants tables — every cutoff in one place

- 7-test onboarding cutoffs: `V1_TEST_NORMALISATION` in `v1_constants.py` —
  per test: measure, thresholds, rationale, **evidence tag** (currently all
  `pragmatic` — that's the honest state; the push test additionally applies
  female-adjusted bands, matching published sex-split push-up norms in
  direction).
- Football test cutoffs: `FOOTBALL_ASSESSMENT_TESTS` (scoring_thresholds).
- LSI bands: `LSI_THRESHOLDS` (§3). Plyo gates: `PLYOMETRIC_GATES` (§7).
- Deloads: `DELOAD_CONFIG` (§8). Sleep/stress/hormonal/age/sex multipliers:
  `v1_constants.py` — every family now carries a citation-or-pragmatic
  annotation inline. There is **no uncited load increase >20 % anywhere**;
  the aggressive multipliers all reduce load.

You should be able to defend every number in those tables with either the
tagged rationale or "pragmatic default, conservative direction, flagged for
review" — and nothing else is claimed.

---

## 12. What VYAYAM measures vs. what a sports-physio clinic measures

| Quantity | Clinic / lab | VYAYAM | Honest gap |
|---|---|---|---|
| Hop distance / LSI | Tape + supervised trials | Same, self-measured | ±5-10 % self-measurement noise |
| Eccentric hamstring | NordBord force (N), break-point angle | Self-timed Nordic hold (s) | No force data; time is a coarse proxy |
| Reactive strength | RSI via contact mat / force plate | App reactivity count (10 s pogo) | NOT RSI; behavioural proxy only |
| Sprint | Timing gates | Phone stopwatch / video | ±0.2-0.3 s human timing error |
| Landing mechanics | 3D motion capture, force plates | MediaPipe valgus/stiff-landing voice warnings | 2D, frontal plane only, no kinetics; warnings not scores |
| Movement quality | Clinician's eye | Joint-angle trajectory match (camera exercises only; 112 of 288) | One plane, no load, no spinal position (not measurable — never claimed) |
| Strength | 1RM / dynamometry | Capability bands from reps/holds | Bands, not newtons |
| Internal load | RPE×duration, GPS, HR | Session RPE + traffic light | No GPS/HR; ACWR deliberately excluded |
| Diagnosis / RTS clearance | Clinician | **Never** | Out of scope by design (V1 uninjured-only) |

The product's integrity rests on this table: everything to the left of a
gap is either measured honestly, proxied with a label that says so, or not
claimed at all.

---

## 13. Open questions for a real sports physio (take these to the meeting)

1. Are the 6-test scoring bands sane for amateur Indian footballers
   (sprint/COD absolute times especially)? All are [pragmatic].
2. Is a 94 % Y-balance band a fair translation of the 4 cm anterior-reach
   marker for our population?
3. Should the ovulation plyometric block stay, given the contested evidence?
   (We kept it as the cautious option.)
4. Nordic dosage in HSR phases: is 3×/week Nordic exposure too dense for
   in-season amateurs? (Literature programmes often run 1–2×/week after
   ramp-up.)
5. Is the 6-week novice deload ceiling reasonable, or should novices simply
   have no mandatory ceiling with feedback triggers only?

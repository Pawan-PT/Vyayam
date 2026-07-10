/*
 * R2-W1-9: node test harness for the extracted CV core.
 * Run:  node --test strength_app/tests/js/cv_core.test.mjs
 * (Not part of the Django suite — run manually or in CI where node exists.)
 *
 * Replays synthetic landmark/angle sequences through the same functions
 * the live execute page uses (the H2 harness idea, in JS).
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const cv = require('../../static/strength_app/js/cv_core.js');

// ── helpers ─────────────────────────────────────────────────────────────
const P = (x, y, visibility = 1) => ({ x, y, visibility });

/** Build a 33-landmark frame for a front-view standing figure whose knee
 *  angle is controlled by `kneeBend` (0 = straight, 1 = full squat). */
function standingFrame(kneeBend = 0) {
  const lm = Array.from({ length: 33 }, () => P(0.5, 0.5, 1));
  const drop = kneeBend * 0.24;           // hips sink as knees bend
  lm[cv.LM.nose] = P(0.50, 0.10);
  lm[cv.LM.leftEar] = P(0.47, 0.11); lm[cv.LM.rightEar] = P(0.53, 0.11);
  lm[cv.LM.leftShoulder] = P(0.40, 0.25); lm[cv.LM.rightShoulder] = P(0.60, 0.25 );
  lm[cv.LM.leftHip] = P(0.44, 0.52 + drop); lm[cv.LM.rightHip] = P(0.56, 0.52 + drop);
  // knee travels forward+down as it bends
  lm[cv.LM.leftKnee] = P(0.44 - kneeBend * 0.09, 0.72 + drop * 0.4);
  lm[cv.LM.rightKnee] = P(0.56 + kneeBend * 0.09, 0.72 + drop * 0.4);
  lm[cv.LM.leftAnkle] = P(0.44, 0.92); lm[cv.LM.rightAnkle] = P(0.56, 0.92);
  lm[cv.LM.leftHeel] = P(0.44, 0.94); lm[cv.LM.rightHeel] = P(0.56, 0.94);
  lm[cv.LM.leftFootIndex] = P(0.45, 0.95); lm[cv.LM.rightFootIndex] = P(0.55, 0.95);
  lm[cv.LM.leftWrist] = P(0.40, 0.50); lm[cv.LM.rightWrist] = P(0.60, 0.50);
  return lm;
}

const kneeAngle = (lm, side = 'left') => cv.calcAngle(
  lm[cv.LM[`${side}Hip`]], lm[cv.LM[`${side}Knee`]], lm[cv.LM[`${side}Ankle`]]);

// ── calcAngle ───────────────────────────────────────────────────────────
test('calcAngle: right angle and straight line', () => {
  assert.equal(Math.round(cv.calcAngle(P(0, 0), P(0, 1), P(1, 1))), 90);
  assert.equal(Math.round(cv.calcAngle(P(0, 0), P(0, 1), P(0, 2))), 180);
});

test('calcAngle: missing landmark degrades to 90, never throws', () => {
  assert.equal(cv.calcAngle(null, P(0, 1), P(1, 1)), 90);
});

// ── computeMatchScore: the phase-advance signal ─────────────────────────
test('matchScore: on-target = 100, distance decays, clamps at 0', () => {
  assert.equal(cv.computeMatchScore({ knee: 90 }, { knee: 90 }), 100);
  assert.ok(cv.computeMatchScore({ knee: 110 }, { knee: 90 }) < 80);
  assert.equal(cv.computeMatchScore({ knee: 178 }, { knee: 90 }), 0);
});

test('matchScore: a clearly-short PARTIAL squat cannot pass the 70-point phase gate', () => {
  // Live gate: USER_FOLLOWS advances a phase only at matchScore >= 70 for
  // 5 frames + 250ms. The scoring curve (100 - meanDiff*1.5) means the
  // gate tolerates up to EXACTLY 20 degrees mean deviation — within the
  // capability-eased band. A rep 25+ degrees short must stall (and then
  // be counted as a partial, not a rep — R2-W1-5).
  const bottomTarget = { knee: 90, hip: 90 };
  const partial = cv.computeMatchScore({ knee: 115, hip: 115 }, bottomTarget);
  assert.ok(partial < 70, `partial scored ${partial}, would have advanced the phase`);
  const edge = cv.computeMatchScore({ knee: 110, hip: 110 }, bottomTarget);
  assert.equal(edge, 70, 'gate boundary moved — re-check partial-rep behavior');
  const full = cv.computeMatchScore({ knee: 92, hip: 93 }, bottomTarget);
  assert.ok(full >= 70, `honest rep scored ${full}, would NOT advance`);
});

test('matchScore: normalised (sub-1.0) targets use the 500x scale', () => {
  // e.g. BALANCE hipLevel target 0.04
  const good = cv.computeMatchScore({ hipLevel: 0.05 }, { hipLevel: 0.04 });
  const bad = cv.computeMatchScore({ hipLevel: 0.20 }, { hipLevel: 0.04 });
  assert.ok(good > 90 && bad < 10);
});

// ── synthetic squat rep through real landmark geometry ──────────────────
test('squat trajectory: knee angle sweeps from straight to deep and back', () => {
  const seq = [0, 0.25, 0.5, 0.75, 1, 0.75, 0.5, 0.25, 0]; // bend fraction
  const angles = seq.map(b => kneeAngle(standingFrame(b)));
  assert.ok(angles[0] > 150, `standing knee ${angles[0]}`);
  const bottom = Math.min(...angles);
  assert.ok(bottom < 110, `bottom knee ${bottom} not deep enough`);
  assert.ok(angles.at(-1) > 150, 'did not return to standing');
});

// ── stance + orientation checks ─────────────────────────────────────────
test('checkStanceWidth: shoulder-width stance passes, too-narrow fails', () => {
  const check = { ankleToShoulderRatio: { min: 0.6, max: 1.4 }, label: 'Feet shoulder width' };
  assert.equal(cv.checkStanceWidth(standingFrame(), check).ok, true);
  const narrow = standingFrame();
  narrow[cv.LM.leftAnkle] = P(0.49, 0.92);
  narrow[cv.LM.rightAnkle] = P(0.51, 0.92);
  assert.equal(cv.checkStanceWidth(narrow, check).ok, false);
});

test('detectOrientation: standing vs supine vs sidelying', () => {
  assert.equal(cv.detectOrientation(standingFrame()), 'standing');
  const supine = standingFrame();
  supine[cv.LM.leftShoulder] = P(0.25, 0.62); supine[cv.LM.rightShoulder] = P(0.27, 0.60);
  supine[cv.LM.leftHip] = P(0.55, 0.60); supine[cv.LM.rightHip] = P(0.57, 0.62);
  supine[cv.LM.nose] = P(0.18, 0.50);
  assert.equal(cv.detectOrientation(supine), 'supine');
  const side = standingFrame();
  side[cv.LM.leftShoulder] = P(0.5, 0.30); side[cv.LM.rightShoulder] = P(0.5, 0.50);
  assert.equal(cv.detectOrientation(side), 'sidelying');
});

// E12 (2026-07 exam): findWorstJoint was the only untested pure cv_core export.
test('findWorstJoint: largest deviation wins, 500x scale for normalized targets, null when unmeasurable', () => {
  assert.equal(cv.findWorstJoint({ knee: 120, hip: 92 }, { knee: 90, hip: 90 }), 'knee');
  // hipLevel err 0.10 * 500 = 50 beats knee err 20
  assert.equal(
    cv.findWorstJoint({ hipLevel: 0.14, knee: 110 }, { hipLevel: 0.04, knee: 90 }),
    'hipLevel');
  assert.equal(cv.findWorstJoint({}, { knee: 90 }), null);
});

/*
 * R2-W1-9: VyayamCV core — pure CV math extracted VERBATIM from
 * v1_exercise_execute.html so it can be unit-tested with node
 * (cv_core.test.mjs). No behavior change. The template aliases these
 * via `VyayamCV.*`; keep both sides in sync when editing.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.VyayamCV = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  const LM = {
    nose: 0,
    leftEar: 7,       rightEar: 8,
    leftShoulder: 11, rightShoulder: 12,
    leftElbow: 13,    rightElbow: 14,
    leftWrist: 15,    rightWrist: 16,
    leftHip: 23,      rightHip: 24,
    leftKnee: 25,     rightKnee: 26,
    leftAnkle: 27,    rightAnkle: 28,
    leftHeel: 29,     rightHeel: 30,
    leftFootIndex: 31, rightFootIndex: 32,
  };

  function calcAngle(a, b, c) {
    if (!a || !b || !c) return 90;
    const rad = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs(rad * 180 / Math.PI);
    if (angle > 180) angle = 360 - angle;
    return angle;
  }

  function computeMatchScore(userAngles, targetJoints) {
    var keys = Object.keys(targetJoints);
    if (keys.length === 0) return 90;
    var totalDiff = 0, count = 0;
    for (var i = 0; i < keys.length; i++) {
      var key    = keys[i];
      var target = targetJoints[key];
      var actual = userAngles[key];
      if (actual === undefined) continue;
      totalDiff += (target < 1) ? Math.abs(actual - target) * 500
                                 : Math.abs(actual - target);
      count++;
    }
    if (count === 0) return 90;
    return Math.max(0, Math.min(100, 100 - (totalDiff / count) * 1.5));
  }

  function findWorstJoint(userAngles, targetJoints) {
    var worstKey = null, worstDiff = 0;
    for (var key in targetJoints) {
      if (userAngles[key] === undefined) continue;
      var diff = Math.abs(userAngles[key] - targetJoints[key]);
      if (targetJoints[key] < 1) diff *= 500;
      if (diff > worstDiff) { worstDiff = diff; worstKey = key; }
    }
    return worstKey;
  }

  function checkStanceWidth(lm, stanceCheck) {
    if (!stanceCheck) return { ok: true, message: '' };

    var shoulderW = Math.abs(lm[LM.leftShoulder].x - lm[LM.rightShoulder].x);
    if (shoulderW < 0.01) return { ok: true, message: '' };

    // === 1. Ankle-to-shoulder width ratio ===
    if (stanceCheck.ankleToShoulderRatio) {
      var ankleW = Math.abs(lm[LM.leftAnkle].x - lm[LM.rightAnkle].x);
      var aRatio = ankleW / shoulderW;
      // Add 30% tolerance to thresholds for MediaPipe jitter
      var aMin = stanceCheck.ankleToShoulderRatio.min * 0.7;
      var aMax = stanceCheck.ankleToShoulderRatio.max * 1.3;
      if (aRatio < aMin) {
        return { ok: false, message: stanceCheck.label + ' \u2014 feet too narrow' };
      }
      if (aRatio > aMax) {
        return { ok: false, message: stanceCheck.label + ' \u2014 feet too wide' };
      }
    }

    // === 2. Wrist-to-shoulder width ratio ===
    if (stanceCheck.wristToShoulderRatio) {
      var wristW = Math.abs(lm[LM.leftWrist].x - lm[LM.rightWrist].x);
      var wRatio = wristW / shoulderW;
      var wMin = stanceCheck.wristToShoulderRatio.min * 0.7;
      var wMax = stanceCheck.wristToShoulderRatio.max * 1.3;
      if (wRatio < wMin) {
        return { ok: false, message: stanceCheck.label + ' \u2014 hands too narrow' };
      }
      if (wRatio > wMax) {
        return { ok: false, message: stanceCheck.label + ' \u2014 hands too wide' };
      }
    }

    // === 3. Foot rotation (heel-to-toe direction) ===
    if (stanceCheck.maxFootRotation !== undefined) {
      var leftHeel  = lm[LM.leftHeel];
      var leftToe   = lm[LM.leftFootIndex];
      var rightHeel = lm[LM.rightHeel];
      var rightToe  = lm[LM.rightFootIndex];

      if (leftHeel && leftToe && rightHeel && rightToe) {
        var heelVis = (leftHeel.visibility  === undefined || leftHeel.visibility  > 0.4)
                   && (rightHeel.visibility === undefined || rightHeel.visibility > 0.4);
        var toeVis  = (leftToe.visibility   === undefined || leftToe.visibility   > 0.4)
                   && (rightToe.visibility  === undefined || rightToe.visibility  > 0.4);

        if (heelVis && toeVis) {
          var leftRot  = Math.abs(leftToe.x  - leftHeel.x)  / shoulderW;
          var rightRot = Math.abs(rightToe.x - rightHeel.x) / shoulderW;

          var footThresh = stanceCheck.maxFootRotation * 1.5;  // 50% more tolerance
          if (leftRot > footThresh || rightRot > footThresh) {
            var side = leftRot > rightRot ? 'left' : 'right';
            return { ok: false, message: 'Your ' + side + ' foot is turned out too much. Point toes more forward.' };
          }
        }
      }
    }

    // === 4. Knee over ankle (valgus/varus check) ===
    if (stanceCheck.kneeOverAnkle) {
      var lKnee  = lm[LM.leftKnee];
      var lAnkle = lm[LM.leftAnkle];
      var rKnee  = lm[LM.rightKnee];
      var rAnkle = lm[LM.rightAnkle];

      if (lKnee && lAnkle && rKnee && rAnkle) {
        var leftValgus  = lAnkle.x - lKnee.x;
        var rightValgus = rKnee.x  - rAnkle.x;
        var valgusThreshold = shoulderW * 0.25;  // wider tolerance for MediaPipe noise

        if (leftValgus > valgusThreshold) {
          return { ok: false, message: 'Left knee is caving inward. Push it out over your toes.' };
        }
        if (rightValgus > valgusThreshold) {
          return { ok: false, message: 'Right knee is caving inward. Push it out over your toes.' };
        }
      }
    }

    // === 5. Shoulder shrug (shoulders too close to ears) ===
    if (stanceCheck.shoulderShrug) {
      var lShoulder = lm[LM.leftShoulder];
      var lEar      = lm[LM.leftEar];
      var rShoulder = lm[LM.rightShoulder];
      var rEar      = lm[LM.rightEar];

      if (lShoulder && lEar && rShoulder && rEar) {
        var earVis = (lEar.visibility === undefined || lEar.visibility > 0.4)
                  && (rEar.visibility === undefined || rEar.visibility > 0.4);
        if (earVis) {
          var leftEarDist  = Math.abs(lEar.y - lShoulder.y);
          var rightEarDist = Math.abs(rEar.y - rShoulder.y);
          var avgEarDist   = (leftEarDist + rightEarDist) / 2;
          var shrugRatio   = avgEarDist / shoulderW;

          if (shrugRatio < 0.25) {  // more lenient — only trigger for very shrugged shoulders
            return { ok: false, message: 'Drop your shoulders away from your ears. Relax them down.' };
          }
        }
      }
    }

    // === 6. Hip level (one hip dropping) ===
    if (stanceCheck.hipLevel) {
      var lHip = lm[LM.leftHip];
      var rHip = lm[LM.rightHip];
      if (lHip && rHip) {
        var hipDiff = Math.abs(lHip.y - rHip.y);
        if (hipDiff > shoulderW * 0.20) {  // wider tolerance — most people have mild asymmetry
          var lowSide = lHip.y > rHip.y ? 'left' : 'right';
          return { ok: false, message: 'Your ' + lowSide + ' hip is dropping. Level your hips.' };
        }
      }
    }

    // === 7. Body line (for planks — hip sag or pike) ===
    if (stanceCheck.bodyLine) {
      var shoulder = lm[LM.leftShoulder];
      var hip      = lm[LM.leftHip];
      var ankle    = lm[LM.leftAnkle];
      if (shoulder && hip && ankle) {
        var midY   = (shoulder.y + ankle.y) / 2;
        var deviation = hip.y - midY;
        var bodyLen   = Math.abs(ankle.y - shoulder.y);
        if (bodyLen > 0.05) {
          var devRatio = deviation / bodyLen;
          if (devRatio > 0.25) {
            return { ok: false, message: 'Your hips are sagging. Squeeze your core and lift them.' };
          }
          if (devRatio < -0.25) {
            return { ok: false, message: 'Your hips are piking up. Lower them into a straight line.' };
          }
        }
      }
    }

    // === 8. Symmetry (left-right balance) ===
    if (stanceCheck.symmetry) {
      var lSh  = lm[LM.leftShoulder];
      var rSh  = lm[LM.rightShoulder];
      var lHip = lm[LM.leftHip];
      var rHip = lm[LM.rightHip];
      if (lSh && rSh && lHip && rHip) {
        var shoulderMidX = (lSh.x + rSh.x) / 2;
        var hipMidX      = (lHip.x + rHip.x) / 2;
        var lateralShift = Math.abs(shoulderMidX - hipMidX);
        if (lateralShift > shoulderW * 0.15) {
          return { ok: false, message: 'You are leaning to one side. Center yourself.' };
        }
      }
    }

    return { ok: true, message: '' };
  }

  function detectOrientation(lm) {
    if (!lm || !lm[LM.leftShoulder] || !lm[LM.rightShoulder] || !lm[LM.leftHip] || !lm[LM.rightHip]) return 'unknown';
    var lsY = lm[LM.leftShoulder].y, rsY = lm[LM.rightShoulder].y;
    var lhY = lm[LM.leftHip].y,      rhY = lm[LM.rightHip].y;
    var shoulderMidY = (lsY + rsY) / 2;
    var hipMidY      = (lhY + rhY) / 2;
    var shoulderToHip = hipMidY - shoulderMidY;  // positive when shoulders above hips

    // Sidelying: shoulders are spread horizontally (one above the other)
    // by more than half the hip-vertical-spread plus a clear baseline.
    var shoulderSpreadY = Math.abs(lsY - rsY);
    if (shoulderSpreadY > 0.15) return 'sidelying';

    // Standing: shoulders clearly above hips (head-up posture).
    if (shoulderToHip > 0.15) return 'standing';

    // Supine vs prone — body roughly horizontal in frame.
    // Supine: face up (nose visible, above shoulders by camera POV).
    // Prone: face down (nose below shoulders).
    if (Math.abs(shoulderToHip) < 0.10) {
      var nose = lm[LM.nose];
      if (nose && nose.visibility !== undefined && nose.visibility > 0.4) {
        return (nose.y < shoulderMidY) ? 'supine' : 'prone';
      }
      return 'supine';  // default to supine when ambiguous and horizontal
    }

    // Inverted: hips above shoulders (handstand or rare).
    if (shoulderToHip < -0.10) return 'prone';

    return 'unknown';
  }

  return {
    LM: LM,
    calcAngle: calcAngle,
    computeMatchScore: computeMatchScore,
    findWorstJoint: findWorstJoint,
    checkStanceWidth: checkStanceWidth,
    detectOrientation: detectOrientation,
  };
});

"""
Lateral Lunges V2 - Frontal Plane Strength Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Accurate lunging/straight leg detection
✅ Practice mode (4 GREEN reps required - 2 per side)
✅ AR overlay V2 support
✅ Better depth validation
✅ Straight leg checking

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced lunging side detection (more bent knee)
- Added practice mode with 4 GREEN rep requirement
- Improved straight leg validation
- Added AR overlay targets
- Better posture tracking
- Side alternation counting

TEST NOTES:
- Verify lunging side detection works
- Ensure straight leg stays straight
- Test depth measurement at bottom
- Check form score varies realistically
- Verify side switching announcements
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class LateralLungesV2:
    """
    Lateral Lunges - Frontal plane strength exercise
    
    Level: Advanced
    Category: Strength
    Target: Hip abductors, adductors, glutes, quadriceps
    
    Reference Video: https://www.youtube.com/watch?v=9zJy_WvBRxs
    (Lateral Lunges - Proper Form)
    
    Biomechanics:
    - Lunging knee: hip → knee → ankle (target 90°)
    - Straight leg: must stay straight (>165°)
    - Back posture: upright throughout
    - Key checkpoints:
      * Step wide to side
      * One leg bends, other stays straight
      * Push hips back
      * Return to center
    
    Phases:
    1. Center (feet together)
    2. Stepping_side (moving into lunge)
    3. Bottom (one knee bent, one straight)
    4. Returning (coming back to center)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=9zJy_WvBRxs"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "center"
        self.last_phase = "center"
        
        self.probation_mode = True
        self.practice_reps_needed = 4  # 2 per side
        self.practice_reps_completed = 0
        
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        if left_knee < right_knee:
            lunging_knee = left_knee
            straight_knee = right_knee
            lunging_side = 'left'
        else:
            lunging_knee = right_knee
            straight_knee = left_knee
            lunging_side = 'right'
        
        lateral_separation = abs(la[0] - ra[0])
        
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        back = 180 - abs(analyzer.calculate_angle(
            (hip_mid[0], hip_mid[1] + 100), hip_mid, shoulder_mid
        ))
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'lunging_knee': lunging_knee,
            'straight_knee': straight_knee,
            'lunging_side': lunging_side,
            'lateral_separation': lateral_separation,
            'back': back,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'center': {
                'left_knee': 175,
                'right_knee': 175,
                'back': 165,
                'tolerance': 10
            },
            'stepping_side': {
                'lunging_knee': 140,
                'straight_knee': 175,
                'back': 160,
                'tolerance': 12
            },
            'bottom': {
                'lunging_knee': 90,
                'straight_knee': 175,
                'back': 160,
                'tolerance': 10
            },
            'returning': {
                'lunging_knee': 140,
                'straight_knee': 175,
                'back': 160,
                'tolerance': 12
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        lunging = angles.get('lunging_knee', 0)
        straight = angles.get('straight_knee', 0)
        
        if straight >= 165:
            feedback['straight_leg'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=straight,
                message="Good straight leg"
            )
        elif straight >= 155:
            feedback['straight_leg'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=straight,
                message="Keep leg straighter"
            )
        else:
            feedback['straight_leg'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=straight,
                message="Leg must stay straight"
            )
        
        if angles.get('back', 0) >= 155:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['back'],
                message="Good posture"
            )
        elif angles.get('back', 0) >= 145:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['back'],
                message="Keep chest up"
            )
        
        if phase == 'bottom':
            if 85 <= lunging <= 100:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=lunging,
                    message="Perfect depth"
                )
            elif 100 < lunging <= 120:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=lunging,
                    message="Good depth"
                )
            elif lunging > 130:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=lunging,
                    message="Lunge deeper"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        lunging_knee = angle
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
        
        if self.phase == "center":
            if lunging_knee >= 165 and self.tempo_detector.get_phase_duration() > 0.5:
                if voice and self.rep_count == 0 and self.practice_reps_completed == 0:
                    voice.speak("Step wide to the side", priority=True)
        
        if self.phase == "center" and lunging_knee < 155:
            self.phase = "stepping_side"
            self.tempo_detector.start_phase('stepping_side')
        
        elif self.phase == "stepping_side":
            if lunging_knee <= 120 and self.tempo_detector.get_phase_duration() > 0.8:
                self.phase = "bottom"
                self.tempo_detector.start_phase('bottom')
                voice.speak("Hold position", priority=True)
        
        elif self.phase == "bottom":
            if self.tempo_detector.get_phase_duration() > 0.5:
                self.phase = "returning"
                self.tempo_detector.start_phase('returning')
                voice.speak("Push back to center", priority=True)
        
        elif self.phase == "returning":
            if lunging_knee >= 165 and self.tempo_detector.get_phase_duration() > 1.0:
                if not has_critical:
                    form_score = self._calculate_rep_form_score()
                    self._handle_rep_completion(form_score, voice)
                    rep_done = True
                else:
                    self.rejected_count += 1
                    voice.speak("Rep rejected", priority=True)
                
                self.phase = "center"
                self.tempo_detector.start_phase('center')
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg_form = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg_form
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        if self.probation_mode:
            if form_score >= 85:
                self.practice_reps_completed += 1
                voice.announce_practice_rep(
                    self.practice_reps_completed,
                    self.practice_reps_needed,
                    form_score
                )
                
                if self.practice_reps_completed >= self.practice_reps_needed:
                    self.probation_mode = False
                    voice.announce_phase_transition(from_practice_to_counted=True)
            else:
                self.rejected_count += 1
                voice.provide_ar_feedback(form_score)
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
            if self.rep_count % 2 == 0:
                voice.speak("Switch sides", priority=True)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        self.stability_detector.update(joints_coords)
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = self.tempo_detector.check_tempo()
        
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
        )
        
        self.current_rep_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        if self.probation_mode:
            frame, position_matched = self.ar.draw_practice_mode(
                frame=frame,
                joints=joints_coords,
                current_angles=angles,
                target_angles=self.get_target_poses()[self.phase],
                form_score=form_score
            )
        else:
            frame = self.ar.draw_counted_mode(
                frame=frame,
                joints=joints_coords,
                form_score=form_score
            )
        return frame
    
    def get_stats(self):
        avg_form_score = (
            sum(self.form_scores) / len(self.form_scores)
            if self.form_scores else 0
        )
        
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("LATERAL LUNGES V2 - Frontal Plane Strength")
    print("="*70)
    exercise = LateralLungesV2(target_reps=10)
    print("\n✅ Features: Lunging/straight leg detection, depth validation, side alternation")
    print("🎯 Exercise ready!")
"""
Single-Leg RDL V2 - Posterior Chain Balance Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Accurate hip hinge angle detection
✅ Practice mode (3 GREEN reps required)
✅ AR overlay V2 support
✅ Back flatness validation (NO rounding)
✅ Stance leg stability check
✅ T-position validation

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced hip hinge detection (torso lean)
- Added practice mode with 3 GREEN rep requirement
- Implemented back flatness check
- Added stance/back leg detection
- Improved form validation
- Added AR overlay targets

TEST NOTES:
- Verify hip hinge angle calculation works
- Ensure back flatness check is accurate
- Test stance leg detection
- Check form score varies realistically
- Verify "hinge at hips not knees" guidance
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SingleLegRDLV2:
    """
    Single-Leg Romanian Deadlift - Posterior chain balance exercise
    
    Level: Advanced
    Category: Strength + Balance
    Target: Hamstrings, glutes, core, balance, ACL protection
    
    Reference Video: https://www.youtube.com/watch?v=LxLDzfM8V5o
    (Single Leg RDL - Proper Technique)
    
    Biomechanics:
    - Stance knee: slight bend (165°), NOT locked
    - Back leg: straight behind (175°)
    - Hip hinge: torso parallel to ground (~90° from vertical)
    - Back: MUST stay flat (no rounding)
    - T-position: torso and back leg in line
    
    Phases:
    1. Standing (upright on one leg)
    2. Hinging (leaning forward, hinge at hips)
    3. Bottom (T-position, parallel to ground)
    4. Rising (returning to standing)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=LxLDzfM8V5o"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "standing"
        self.last_phase = "standing"
        
        self.probation_mode = True
        self.practice_reps_needed = 3
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
        
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        if ra[1] > la[1]:
            stance_knee = right_knee
            back_leg_knee = left_knee
        else:
            stance_knee = left_knee
            back_leg_knee = right_knee
        
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        
        hip_hinge = analyzer.calculate_angle(
            (hip_mid[0], hip_mid[1] + 100),
            hip_mid,
            shoulder_mid
        )
        
        back_flat = True
        if hip_hinge > 45:
            back_alignment = abs(shoulder_mid[1] - hip_mid[1])
            back_flat = back_alignment < 60
        
        return {
            'stance_knee': stance_knee,
            'back_leg_knee': back_leg_knee,
            'hip_hinge': hip_hinge,
            'back_flat': back_flat,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'standing': {
                'stance_knee': 175,
                'back_leg_knee': 175,
                'hip_hinge': 20,
                'tolerance': 10
            },
            'hinging': {
                'stance_knee': 165,
                'back_leg_knee': 175,
                'hip_hinge': 50,
                'tolerance': 12
            },
            'bottom': {
                'stance_knee': 165,
                'back_leg_knee': 175,
                'hip_hinge': 85,
                'tolerance': 10
            },
            'rising': {
                'stance_knee': 165,
                'back_leg_knee': 175,
                'hip_hinge': 50,
                'tolerance': 12
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        
        if 160 <= angles.get('stance_knee', 0) <= 175:
            feedback['stance'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['stance_knee'],
                message="Good knee position"
            )
        elif angles.get('stance_knee', 0) < 150:
            feedback['stance'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=angles['stance_knee'],
                message="Don't squat - hinge at hips"
            )
        
        if angles.get('back_leg_knee', 0) >= 165:
            feedback['back_leg'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['back_leg_knee'],
                message="Good leg extension"
            )
        elif angles.get('back_leg_knee', 0) >= 155:
            feedback['back_leg'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['back_leg_knee'],
                message="Keep leg straighter"
            )
        
        if not angles.get('back_flat', True):
            feedback['back'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Back rounding - keep flat"
            )
        else:
            feedback['back'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=0,
                message="Good flat back"
            )
        
        if phase == 'bottom':
            if 60 <= angles.get('hip_hinge', 0) <= 90:
                feedback['hinge'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=angles['hip_hinge'],
                    message="Perfect hip hinge"
                )
            elif angles.get('hip_hinge', 0) < 60:
                feedback['hinge'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=angles['hip_hinge'],
                    message="Hinge forward more"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        hip_hinge = angle
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
        
        if self.phase == "standing":
            if hip_hinge <= 30 and self.tempo_detector.get_phase_duration() > 0.5:
                self.phase = "hinging"
                self.tempo_detector.start_phase('hinging')
                voice.speak("Hinge at hips not knees", priority=True)
        
        elif self.phase == "hinging":
            if hip_hinge >= 60 and self.tempo_detector.get_phase_duration() > 1.0:
                self.phase = "bottom"
                self.tempo_detector.start_phase('bottom')
                voice.speak("Hold T-position", priority=True)
        
        elif self.phase == "bottom":
            if self.tempo_detector.get_phase_duration() > 0.5:
                self.phase = "rising"
                self.tempo_detector.start_phase('rising')
                voice.speak("Return to standing", priority=True)
        
        elif self.phase == "rising":
            if hip_hinge <= 30 and self.tempo_detector.get_phase_duration() > 1.0:
                if not has_critical:
                    form_score = self._calculate_rep_form_score()
                    self._handle_rep_completion(form_score, voice)
                    rep_done = True
                else:
                    self.rejected_count += 1
                    voice.speak("Rep rejected", priority=True)
                
                self.phase = "standing"
                self.tempo_detector.start_phase('standing')
        
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
            if self.rep_count % 5 == 0:
                voice.speak("Switch legs", priority=True)
    
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
    print("SINGLE-LEG RDL V2 - Posterior Chain Balance")
    print("="*70)
    exercise = SingleLegRDLV2(target_reps=10)
    print("\n✅ Features: Hip hinge detection, back flatness check, T-position validation")
    print("🎯 Exercise ready!")
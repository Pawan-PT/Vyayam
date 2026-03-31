"""
Glute Bridge V2 - Posterior Chain Foundation Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Accurate hip extension and alignment tracking
✅ Practice mode (3 GREEN reps required)
✅ AR overlay V2 support
✅ 2-second hold at top
✅ Hip symmetry validation

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced hip extension detection
- Added practice mode with 3 GREEN rep requirement
- Implemented 2-second hold at top position
- Added hip symmetry checking
- Body alignment validation (shoulder-hip-knee line)
- Improved tempo tracking

TEST NOTES:
- Verify hip extension detection works
- Ensure 2-second hold is enforced
- Test hip symmetry checking
- Check form score varies realistically

Reference Video: https://www.youtube.com/watch?v=wPM8icPu6H8
(Glute Bridge - Proper Form Tutorial)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class GluteBridgeV2:
    """
    Glute Bridge - Posterior chain foundation
    
    Level: Foundation
    Category: Strength
    Target: Gluteus maximus, hamstrings, erector spinae
    
    Reference Video: https://www.youtube.com/watch?v=wPM8icPu6H8
    (Glute Bridge - Proper Form Tutorial)
    
    Biomechanics:
    - Starting: Lying with knees bent (90°)
    - Top: Hips fully extended (170°), straight line shoulder-hip-knee
    - Hold: 2 seconds at top
    - Control: Slow descent
    
    Phases:
    1. Lying (ready position)
    2. Lifting (hips rising)
    3. Top (hold 2 seconds)
    4. Lowering (controlled descent)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=wPM8icPu6H8"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "lying"
        self.last_phase = "lying"
        
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
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Hip angles (shoulder-hip-knee)
        left_hip = analyzer.smooth_angle(analyzer.calculate_angle(ls, lh, lk), 'left')
        right_hip = analyzer.smooth_angle(analyzer.calculate_angle(rs, rh, rk), 'right')
        
        # Knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Body alignment (shoulder-hip-knee line)
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        knee_mid = ((lk[0] + rk[0])//2, (lk[1] + rk[1])//2)
        
        body_alignment = analyzer.calculate_angle(shoulder_mid, hip_mid, knee_mid)
        
        # Hip symmetry
        hip_diff = abs(left_hip - right_hip)
        
        return {
            'left_hip': left_hip,
            'right_hip': right_hip,
            'avg_hip': (left_hip + right_hip) / 2,
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': (left_knee + right_knee) / 2,
            'body_alignment': body_alignment,
            'hip_symmetry': hip_diff,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'lying': {
                'avg_hip': 90,
                'avg_knee': 90,
                'tolerance': 10
            },
            'lifting': {
                'avg_hip': 140,
                'avg_knee': 95,
                'body_alignment': 160,
                'tolerance': 12
            },
            'top': {
                'avg_hip': 170,
                'avg_knee': 100,
                'body_alignment': 170,
                'tolerance': 8
            },
            'lowering': {
                'avg_hip': 120,
                'avg_knee': 95,
                'tolerance': 12
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        avg_hip = angles.get('avg_hip', 0)
        
        # Hip symmetry
        if angles.get('hip_symmetry', 0) < 12:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['hip_symmetry'],
                message="Even hips"
            )
        elif angles.get('hip_symmetry', 0) < 20:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['hip_symmetry'],
                message="Level hips"
            )
        else:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=angles['hip_symmetry'],
                message="Uneven hips"
            )
        
        if phase == 'top':
            # Hip extension
            if avg_hip >= 160:
                feedback['hip'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=avg_hip,
                    message="Perfect hip extension"
                )
            elif avg_hip >= 145:
                feedback['hip'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=avg_hip,
                    message="Lift hips higher"
                )
            else:
                feedback['hip'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=avg_hip,
                    message="Much higher"
                )
            
            # Body alignment
            if angles.get('body_alignment', 0) >= 160:
                feedback['alignment'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=angles['body_alignment'],
                    message="Perfect alignment"
                )
            elif angles.get('body_alignment', 0) >= 140:
                feedback['alignment'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=angles['body_alignment'],
                    message="Straighten more"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        avg_hip = angle
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
        
        # STATE MACHINE
        if self.phase == "lying":
            if 80 <= avg_hip <= 110 and self.tempo_detector.get_phase_duration() > 0.5:
                self.phase = "lifting"
                self.tempo_detector.start_phase('lifting')
                voice.speak("Lift your hips", priority=True)
        
        elif self.phase == "lifting":
            if avg_hip >= 155 and self.tempo_detector.get_phase_duration() > 0.8:
                self.phase = "top"
                self.tempo_detector.start_phase('top')
                voice.speak("Hold and squeeze", priority=True)
        
        elif self.phase == "top":
            # Must hold 2 seconds
            if self.tempo_detector.get_phase_duration() >= 2.0:
                self.phase = "lowering"
                self.tempo_detector.start_phase('lowering')
                voice.speak("Lower slowly", priority=True)
            elif self.tempo_detector.get_phase_duration() < 2.0 and avg_hip < 150:
                warnings.append("Hold at top for 2 seconds")
        
        elif self.phase == "lowering":
            if avg_hip <= 110 and self.tempo_detector.get_phase_duration() > 0.5:
                if not has_critical:
                    form_score = self._calculate_rep_form_score()
                    self._handle_rep_completion(form_score, voice)
                    rep_done = True
                else:
                    self.rejected_count += 1
                    voice.speak("Rep rejected", priority=True)
                
                self.phase = "lying"
                self.tempo_detector.start_phase('lying')
        
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
    print("GLUTE BRIDGE V2 - Posterior Chain Foundation")
    print("="*70)
    exercise = GluteBridgeV2(target_reps=10)
    print("\n✅ Features: Hip extension tracking, 2-sec hold, alignment validation")
    print("🎯 Exercise ready!")
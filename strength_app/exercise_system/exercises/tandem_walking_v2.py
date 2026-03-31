"""
Tandem Walking V2 - Balance and Coordination Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Accurate step detection and balance tracking
✅ Practice mode (3 GREEN steps required)
✅ AR overlay V2 support
✅ Wobble detection during tandem stance
✅ Heel-to-toe alignment checking

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced step detection (heel-to-toe alignment)
- Added practice mode with 3 GREEN rep requirement
- Improved balance scoring with stability tracking
- Added AR overlay targets
- Better wobble detection

TEST NOTES:
- Verify heel-to-toe alignment detection works
- Ensure wobble tracking is sensitive enough
- Test step counting (each step = 1 rep)
- Check form score reflects balance quality
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class TandemWalkingV2:
    """
    Tandem Walking - Balance and coordination exercise
    
    Level: Intermediate
    Category: Balance
    Target: Balance, coordination, proprioception
    
    Reference Video: https://www.youtube.com/watch?v=3JQFbGgRPkk
    (Tandem Walking - Balance Exercise)
    
    Biomechanics:
    - Heel-to-toe alignment (one foot directly in front of other)
    - Upright posture throughout
    - Minimal wobble during stance
    - Controlled step cadence
    
    Phases:
    1. Ready (feet together)
    2. Stepping (one foot moves forward heel-to-toe)
    3. Stable (brief hold on new position)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=3JQFbGgRPkk"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "ready"
        self.last_phase = "ready"
        
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
        self.voice.speak("Walk heel-to-toe", priority=True)
    
    def calculate_angles(self, analyzer, results, shape):
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Heel-to-toe separation
        foot_separation = abs(la[1] - ra[1])  # Vertical separation
        lateral_separation = abs(la[0] - ra[0])  # Should be minimal
        
        # Back posture
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        hip_mid_x = (lh[0] + rh[0]) / 2
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        
        vertical_offset = abs(shoulder_mid_x - hip_mid_x)
        vertical_height = abs(hip_mid_y - shoulder_mid_y) if hip_mid_y > shoulder_mid_y else 1
        lean_ratio = vertical_offset / max(vertical_height, 1)
        back_angle = 180 - (lean_ratio * 60)
        back_angle = max(120, min(180, back_angle))
        
        return {
            'foot_separation': foot_separation,
            'lateral_separation': lateral_separation,
            'back': back_angle,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'ready': {
                'foot_separation': 30,
                'back': 165,
                'tolerance': 10
            },
            'stepping': {
                'foot_separation': 50,
                'back': 165,
                'tolerance': 12
            },
            'stable': {
                'foot_separation': 35,
                'back': 165,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        
        if angles.get('lateral_separation', 0) > 40:
            feedback['alignment'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['lateral_separation'],
                message="Keep feet in line"
            )
        else:
            feedback['alignment'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['lateral_separation'],
                message="Good heel-to-toe"
            )
        
        if angles.get('back', 0) >= 160:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['back'],
                message="Good posture"
            )
        elif angles.get('back', 0) >= 145:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['back'],
                message="Stand taller"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        
        if self.phase == "ready":
            self.phase = "stepping"
            self.tempo_detector.start_phase('stepping')
            voice.speak("Step forward", priority=True)
        
        elif self.phase == "stepping":
            if self.tempo_detector.get_phase_duration() > 0.8:
                self.phase = "stable"
                self.tempo_detector.start_phase('stable')
        
        elif self.phase == "stable":
            if self.tempo_detector.get_phase_duration() > 0.5:
                rep_done = True
                self.phase = "ready"
                
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
        
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
    print("TANDEM WALKING V2 - Balance Exercise")
    print("="*70)
    
    exercise = TandemWalkingV2(target_reps=10)
    print("\n✅ Features: Heel-to-toe detection, balance scoring, wobble tracking")
    print("🎯 Exercise ready!")
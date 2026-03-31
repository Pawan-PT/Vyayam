"""
Double Leg Balance V2 - Proprioception Baseline Assessment

Reference Video: https://www.youtube.com/watch?v=jZ4gKdmYT3Q
(Double Leg Balance - Standing Balance Training)

CHANGES FROM V1:
- Added form calculator with stability tracking (wobble detection)
- Integrated voice coach V2 for second-by-second counting
- Added AR overlay V2
- Real-time wobble visualization
- Fixed practice mode (2 successful 10-second holds)
"""

import cv2
import time
import numpy as np
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class DoubleLegBalanceV2:
    """
    Double Leg Balance - Proprioception baseline
    
    Level: Foundation
    Category: Balance
    Target: Proprioception, core stability, ankle stabilizers
    
    Reference Video: https://www.youtube.com/watch?v=jZ4gKdmYT3Q
    (Double Leg Balance Technique)
    
    Biomechanics:
    - Stance: Feet hip-width apart
    - Knee angle: 170-180° (slight flex for stability)
    - Goal: Minimize body sway
    - Hold duration: 10 seconds
    - Success metric: Wobble score < 5
    
    Phases:
    1. Standing (getting into position)
    2. Holding (10-second static hold)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=jZ4gKdmYT3Q"
    
    def __init__(self, target_reps=5):
        # Exercise parameters (reps = number of 10-second holds)
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "standing"
        
        # Practice mode (2 successful holds required)
        self.probation_mode = True
        self.practice_reps_needed = 2
        self.practice_reps_completed = 0
        
        # Hold tracking
        self.hold_start_time = None
        self.hold_duration_required = 10.0  # 10 seconds
        self.hold_announced_seconds = set()
        
        # Form tracking
        self.form_scores = []
        self.current_hold_form_scores = []
        
        # Stability tracker (critical for balance)
        self.stability_detector = StabilityDetector(history_size=30)  # Longer history for balance
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """Calculate stability metrics"""
        # Extract joints
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Knee angles (should be slightly bent for stability)
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        avg_knee = (left_knee + right_knee) / 2
        
        # Weight distribution (based on ankle heights)
        weight_diff = abs(la[1] - ra[1])
        uneven_weight = weight_diff > 20
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'weight_diff': weight_diff,
            'uneven_weight': uneven_weight,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        """Target angles"""
        return {
            'standing': {
                'avg_knee': 175,
                'tolerance': 10
            },
            'holding': {
                'avg_knee': 175,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate balance form"""
        feedback = {}
        
        # Knee position
        knee_angle = angles.get('avg_knee', 0)
        if 170 <= knee_angle <= 180:
            feedback['stance'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_angle,
                message="Good stance"
            )
        elif knee_angle < 160:
            feedback['stance'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_angle,
                message="Stand more upright"
            )
        
        # Weight distribution
        if angles.get('uneven_weight', False):
            feedback['weight'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['weight_diff'],
                message="Balance weight evenly"
            )
        else:
            feedback['weight'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['weight_diff'],
                message="Even weight distribution"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update hold counter"""
        rep_done = False
        warnings = []
        
        # For balance, we don't use traditional phase transitions
        # Just track the hold duration
        
        if self.hold_start_time is None:
            # Start the hold
            self.hold_start_time = time.time()
            self.hold_announced_seconds = set()
            self.phase = "holding"
            voice.speak("Hold steady", priority=True)
        
        # Calculate hold duration
        hold_elapsed = time.time() - self.hold_start_time
        current_second = int(hold_elapsed)
        
        # Count each second
        if current_second > 0 and current_second not in self.hold_announced_seconds:
            self.hold_announced_seconds.add(current_second)
            voice.count_hold_seconds(current_second, int(self.hold_duration_required))
        
        # Get stability score (wobble)
        stability_data = self.stability_detector.get_stability_data()
        wobble = stability_data.get('wobble_amount', 0)
        
        # Check if hold failed due to excessive wobble
        if wobble > 8:  # High wobble threshold
            warnings.append(f"Too much movement - wobble: {wobble:.1f}")
            if hold_elapsed > 2.0:  # Give 2 seconds grace period
                # Reset hold
                self.hold_start_time = None
                self.rejected_count += 1
                voice.speak("Too unstable", priority=True)
                return False, "standing", warnings
        
        # Check if hold complete
        if hold_elapsed >= self.hold_duration_required:
            # Hold successful
            rep_done = True
            
            form_score = self._calculate_hold_form_score(wobble)
            self._handle_hold_completion(form_score, voice)
            
            # Reset for next hold
            self.hold_start_time = None
            self.phase = "standing"
        
        # Display hold progress
        warnings.append(f"Hold: {int(hold_elapsed)}s / {int(self.hold_duration_required)}s | Wobble: {wobble:.1f}")
        
        return rep_done, self.phase, warnings
    
    def _calculate_hold_form_score(self, wobble):
        """Calculate form score based on wobble"""
        # For balance, wobble is the primary metric
        # Low wobble = high score
        if wobble < 2:
            return 95.0  # Excellent
        elif wobble < 4:
            return 88.0  # Good
        elif wobble < 6:
            return 75.0  # Acceptable
        else:
            return 60.0  # Needs improvement
    
    def _handle_hold_completion(self, form_score, voice):
        """Handle hold completion"""
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
                voice.speak("Practice again", priority=True)
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        stability_data = self.stability_detector.get_stability_data()
        wobble = stability_data.get('wobble_amount', 0)
        
        # For balance, stability is the primary factor (weighted 80%)
        stability_score = max(0, 100 - (wobble * 10))
        
        # Angle accuracy (weighted 20%)
        target_angles = self.get_target_poses()[self.phase]
        angle_score = FormCalculator.calculate_angle_accuracy(angles, target_angles)
        
        form_score = (stability_score * 0.8) + (angle_score * 0.2)
        
        self.current_hold_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay"""
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(
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
        """Get statistics"""
        avg_form_score = (
            sum(self.form_scores) / len(self.form_scores)
            if self.form_scores else 0
        )
        
        return {
            'holds_completed': self.rep_count,
            'practice_holds': self.practice_reps_completed,
            'rejected_holds': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'avg_wobble': round(100 - avg_form_score, 1) if avg_form_score > 0 else 0,
            'form_scores': self.form_scores,
            'target_holds': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("DOUBLE LEG BALANCE V2")
    print("="*70)
    print("\n✅ 10-second hold with wobble tracking")
    print("✅ Real-time stability measurement")
    print("✅ Second-by-second counting")
    print("✅ Form based on wobble score")
    print("="*70)
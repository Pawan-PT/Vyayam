"""
Butt Kicks V2 - Cardio Running Drill

Reference Video: https://www.youtube.com/watch?v=9Qxo0BQKCJE
(Butt Kicks - Proper Form and Technique)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class ButtKicksV2:
    """
    Butt Kicks - Running drill for hamstrings and cardio
    
    Level: Foundation
    Category: Cardio
    Target: Hamstrings, cardiovascular endurance, running form
    
    Reference Video: https://www.youtube.com/watch?v=9Qxo0BQKCJE
    (Butt Kicks Proper Technique)
    
    Biomechanics:
    - Alternating heel kicks toward glutes
    - Knee flexion >90° (ideally heel touches glute)
    - Fast repetitive movement
    - Upper body upright
    
    Movement Detection:
    - Heel-to-glute distance (closer = better form)
    - Knee flexion angle (should be <90° at peak)
    - Alternating legs
    - Fast cadence
    
    Phases (per leg):
    1. Extended (leg straight down)
    2. Kicking (heel moving toward glute)
    3. Peak (heel at/near glute)
    4. Lowering (returning to ground)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=9Qxo0BQKCJE"
    
    def __init__(self, target_reps=30):  # 30 kicks total (15 per leg)
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Track which leg is working
        self.left_kicks = 0
        self.right_kicks = 0
        
        # Phase tracking (for current working leg)
        self.phase = "extended"
        self.last_phase = "extended"
        self.current_working_leg = None  # 'left' or 'right'
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 6  # 3 per leg
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        # Detectors
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate angles for butt kicks
        
        Key measurements:
        - Knee flexion (hip-knee-ankle)
        - Heel-to-glute distance
        """
        # Extract joints
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        lheel = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HEEL, shape)
        rheel = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HEEL, shape)
        
        # Knee flexion angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Heel-to-glute distances (approximate)
        left_heel_to_glute = abs(lheel[1] - lh[1])  # Vertical distance
        right_heel_to_glute = abs(rheel[1] - rh[1])
        
        # Determine which leg is kicking (more flexed knee)
        if left_knee < 120 and left_knee < right_knee - 20:
            working_leg = 'left'
            working_knee_angle = left_knee
            heel_to_glute = left_heel_to_glute
        elif right_knee < 120 and right_knee < left_knee - 20:
            working_leg = 'right'
            working_knee_angle = right_knee
            heel_to_glute = right_heel_to_glute
        else:
            working_leg = None
            working_knee_angle = max(left_knee, right_knee)
            heel_to_glute = min(left_heel_to_glute, right_heel_to_glute)
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'working_leg': working_leg,
            'working_knee_angle': working_knee_angle,
            'heel_to_glute': heel_to_glute,
            'left_heel_to_glute': left_heel_to_glute,
            'right_heel_to_glute': right_heel_to_glute,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'lheel': lheel, 'rheel': rheel
            }
        }
    
    def get_target_poses(self):
        """Target positions for butt kicks"""
        return {
            'extended': {
                'working_knee_angle': 170,  # Straight leg
                'tolerance': 10
            },
            'kicking': {
                'working_knee_angle': 120,  # Mid-kick
                'tolerance': 15
            },
            'peak': {
                'working_knee_angle': 60,   # Heel near glute
                'tolerance': 15
            },
            'lowering': {
                'working_knee_angle': 120,  # Returning
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate butt kick form"""
        feedback = {}
        
        working_knee = angles.get('working_knee_angle', 180)
        heel_dist = angles.get('heel_to_glute', 200)
        
        # Peak position - heel should be close to glute
        if phase == 'peak':
            if working_knee < 70 and heel_dist < 80:
                feedback['kick'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good kick!"
                )
            elif working_knee > 90:
                feedback['kick'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Kick higher"
                )
            elif heel_dist > 100:
                feedback['kick'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Bring heel to glute"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for butt kicks
        
        Each kick = 1 rep (alternating legs)
        """
        rep_done = False
        warnings = []
        
        working_knee = angle.get('working_knee_angle', 180)
        working_leg = angle.get('working_leg')
        
        # State machine for one kick
        if self.phase == "extended":
            # Detect start of kick
            if working_leg is not None and working_knee < 140:
                self.phase = "kicking"
                self.current_working_leg = working_leg
                self.tempo_detector.start_phase('kicking')
        
        elif self.phase == "kicking":
            # Reached peak flexion
            if working_knee < 90:
                self.phase = "peak"
        
        elif self.phase == "peak":
            # Starting to extend
            if working_knee > 100:
                self.phase = "lowering"
        
        elif self.phase == "lowering":
            # Completed one kick
            if working_knee > 150:
                rep_done = True
                self.phase = "extended"
                
                # Track which leg completed
                if self.current_working_leg == 'left':
                    self.left_kicks += 1
                elif self.current_working_leg == 'right':
                    self.right_kicks += 1
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
                
                self.current_working_leg = None
        
        # Track phase changes
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed kick"""
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        """Handle rep completion"""
        if self.probation_mode:
            if form_score >= 85:
                self.practice_reps_completed += 1
                # Only announce every other practice rep (too fast)
                if self.practice_reps_completed % 2 == 0:
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
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            
            # Announce every 10 reps for fast cardio
            if self.rep_count % 10 == 0:
                voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        working_knee = angles.get('working_knee_angle', 180)
        heel_dist = angles.get('heel_to_glute', 200)
        
        # Score based on kick quality
        if self.phase == 'peak':
            # At peak - check how close heel gets to glute
            if working_knee < 70 and heel_dist < 80:
                form_score = 95.0
            elif working_knee < 90 and heel_dist < 100:
                form_score = 85.0
            else:
                form_score = 70.0
        else:
            # Transition phases
            form_score = 80.0
        
        self.current_rep_form_scores.append(form_score)
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
            'reps_completed': self.rep_count,
            'left_kicks': self.left_kicks,
            'right_kicks': self.right_kicks,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("BUTT KICKS V2 - Cardio Running Drill")
    print("="*70)
    print("\n✅ Heel-to-glute tracking")
    print("✅ Alternating leg detection")
    print("✅ Fast cadence support")
    print("✅ Running form validation")
    print("="*70)

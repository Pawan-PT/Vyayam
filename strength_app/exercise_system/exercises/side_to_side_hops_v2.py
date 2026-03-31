"""
Side-to-Side Hops V2 - Lateral Agility Drill

Reference Video: https://www.youtube.com/watch?v=RRBSs8yzYJk
(Side to Side Hops - Agility Training)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SideToSideHopsV2:
    """
    Side-to-Side Hops - Lateral agility and cardio
    
    Level: Foundation
    Category: Cardio
    Target: Lateral movement, agility, cardiovascular endurance, ankle/knee stability
    
    Reference Video: https://www.youtube.com/watch?v=RRBSs8yzYJk
    (Side to Side Hops Agility)
    
    Biomechanics:
    - Lateral hopping from side to side
    - Both feet together
    - Soft landing on balls of feet
    - Knees slightly bent for shock absorption
    
    Movement Detection:
    - Lateral displacement (left vs center vs right)
    - Hip horizontal position tracking
    - Landing detection (knee flexion)
    
    Phases:
    1. Left (landed left)
    2. Hopping right (in air/transitioning)
    3. Right (landed right)
    4. Hopping left (returning)
    
    Rep = one complete cycle (left → right → left)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=RRBSs8yzYJk"
    
    def __init__(self, target_reps=20):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "center"
        self.last_phase = "center"
        
        # Position tracking
        self.center_x = None  # Calibrate center position
        self.left_hops = 0
        self.right_hops = 0
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 3
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
        Calculate position for side-to-side hops
        
        Key measurements:
        - Hip horizontal position (lateral displacement)
        - Knee flexion (landing detection)
        """
        # Extract joints
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Hip center position (horizontal)
        hip_center_x = (lh[0] + rh[0]) / 2
        
        # Calibrate center on first frame
        if self.center_x is None:
            self.center_x = hip_center_x
        
        # Calculate lateral displacement from center
        displacement = hip_center_x - self.center_x
        
        # Classify position (left, center, right)
        if displacement < -40:  # Moved left
            position = "left"
        elif displacement > 40:  # Moved right
            position = "right"
        else:
            position = "center"
        
        # Knee angles for landing detection
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        avg_knee = (left_knee + right_knee) / 2
        
        # Landed (knees bent)
        landed = avg_knee < 160
        
        return {
            'hip_center_x': hip_center_x,
            'displacement': displacement,
            'position': position,
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'landed': landed,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target positions for side hops"""
        return {
            'left': {
                'displacement': -60,    # Left of center
                'avg_knee': 155,        # Slightly bent
                'tolerance': 20
            },
            'hopping_right': {
                'displacement': 0,      # Mid-hop
                'tolerance': 30
            },
            'right': {
                'displacement': 60,     # Right of center
                'avg_knee': 155,
                'tolerance': 20
            },
            'hopping_left': {
                'displacement': 0,
                'tolerance': 30
            },
            'center': {
                'displacement': 0,
                'avg_knee': 165,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate hop form"""
        feedback = {}
        
        position = angles.get('position', 'center')
        landed = angles.get('landed', False)
        
        # Landing validation
        if phase in ['left', 'right']:
            if landed:
                feedback['landing'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good landing"
                )
            else:
                feedback['landing'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Bend knees on landing"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for side-to-side hops
        
        Rep = complete cycle (left → right → left OR right → left → right)
        """
        rep_done = False
        warnings = []
        
        position = angle.get('position', 'center')
        
        # State machine
        if self.phase == "center":
            # Start by hopping to either side
            if position == "left":
                self.phase = "left"
                self.left_hops += 1
            elif position == "right":
                self.phase = "right"
                self.right_hops += 1
        
        elif self.phase == "left":
            # Hop to right
            if position == "center" or position == "right":
                self.phase = "hopping_right"
        
        elif self.phase == "hopping_right":
            # Landed on right
            if position == "right":
                self.phase = "right"
                self.right_hops += 1
        
        elif self.phase == "right":
            # Hop back to left
            if position == "center" or position == "left":
                self.phase = "hopping_left"
        
        elif self.phase == "hopping_left":
            # Completed one cycle
            if position == "left":
                rep_done = True
                self.phase = "left"
                self.left_hops += 1
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
        
        # Track phase changes
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed cycle"""
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
            
            # Announce every 5 reps
            if self.rep_count % 5 == 0:
                voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        position = angles.get('position', 'center')
        landed = angles.get('landed', False)
        
        # Score based on position and landing
        if self.phase in ['left', 'right'] and position == self.phase and landed:
            form_score = 95.0  # Good landing in correct position
        elif self.phase in ['left', 'right'] and position == self.phase:
            form_score = 85.0  # Correct position
        elif self.phase in ['hopping_left', 'hopping_right']:
            form_score = 80.0  # Transition
        else:
            form_score = 70.0
        
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
            'left_hops': self.left_hops,
            'right_hops': self.right_hops,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("SIDE-TO-SIDE HOPS V2 - Lateral Agility Drill")
    print("="*70)
    print("\n✅ Lateral displacement tracking")
    print("✅ Landing detection")
    print("✅ Position calibration")
    print("✅ Fast lateral movement")
    print("="*70)

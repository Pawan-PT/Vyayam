"""
Burpees V2 - Full Body Cardio Compound

Reference Video: https://www.youtube.com/watch?v=auBLPXO8Fww
(Burpees - Proper Form and Technique)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class BurpeesV2:
    """
    Burpees - Ultimate full-body cardio exercise
    
    Level: Intermediate/Advanced
    Category: Cardio/Strength
    Target: Full body, cardiovascular endurance, explosive power
    
    Reference Video: https://www.youtube.com/watch?v=auBLPXO8Fww
    (Burpees Proper Technique)
    
    Biomechanics:
    - 6-part movement:
      1. Standing position
      2. Squat down, hands on ground
      3. Jump/step back to plank
      4. Push-up (optional, not tracked)
      5. Jump/step feet forward
      6. Jump up with arms overhead
    
    Movement Detection:
    - Hip height (standing vs squat vs plank)
    - Hand position (on ground vs overhead)
    - Vertical jump detection
    
    Phases:
    1. Standing (upright, hands overhead from previous jump)
    2. Squatting (lowering down)
    3. Hands down (hands on ground)
    4. Plank (extended plank position)
    5. Feet forward (jumping feet back to hands)
    6. Jumping up (explosive jump)
    
    Rep = one complete burpee cycle
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=auBLPXO8Fww"
    
    def __init__(self, target_reps=10):  # Fewer reps - very intense
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "standing"
        self.last_phase = "standing"
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 2  # Only 2 for burpees
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
        Calculate positions for burpees
        
        Key measurements:
        - Hip height (standing vs squat vs plank)
        - Hand position (ground vs overhead)
        - Body angle (plank vs standing)
        """
        # Extract joints
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        
        # Hip height (y-coordinate, higher value = lower position)
        avg_hip_y = (lh[1] + rh[1]) / 2
        avg_shoulder_y = (ls[1] + rs[1]) / 2
        avg_wrist_y = (lw[1] + rw[1]) / 2
        avg_ankle_y = (la[1] + ra[1]) / 2
        
        # Classify position based on hip height
        # Standing: hips high (low y value)
        # Squat: hips low (high y value, close to ankles)
        # Plank: hips level with shoulders (horizontal body)
        
        hip_to_ankle = avg_hip_y - avg_ankle_y
        hip_to_shoulder = avg_hip_y - avg_shoulder_y
        
        # Hands on ground (wrists close to ankles in y)
        hands_on_ground = abs(avg_wrist_y - avg_ankle_y) < 100
        
        # Hands overhead (wrists above shoulders)
        hands_overhead = avg_wrist_y < avg_shoulder_y - 50
        
        # Classify body position
        if hip_to_ankle < -200:  # Hips much higher than ankles
            body_position = "standing"
        elif hip_to_ankle < -100:  # Hips somewhat higher
            body_position = "squatting"
        elif -20 < hip_to_shoulder < 60:  # Hips roughly level with shoulders
            body_position = "plank"
        elif hip_to_ankle > -100:  # Hips close to ankles
            body_position = "squat_low"
        else:
            body_position = "transitioning"
        
        # Knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        avg_knee = (left_knee + right_knee) / 2
        
        return {
            'avg_hip_y': avg_hip_y,
            'hip_to_ankle': hip_to_ankle,
            'hip_to_shoulder': hip_to_shoulder,
            'body_position': body_position,
            'hands_on_ground': hands_on_ground,
            'hands_overhead': hands_overhead,
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk, 'la': la, 'ra': ra,
                'lw': lw, 'rw': rw
            }
        }
    
    def get_target_poses(self):
        """Target positions for burpees"""
        return {
            'standing': {
                'body_position': 'standing',
                'avg_knee': 170,
                'tolerance': 15
            },
            'squatting': {
                'body_position': 'squatting',
                'avg_knee': 120,
                'tolerance': 20
            },
            'hands_down': {
                'body_position': 'squat_low',
                'hands_on_ground': True,
                'tolerance': 10
            },
            'plank': {
                'body_position': 'plank',
                'tolerance': 15
            },
            'feet_forward': {
                'body_position': 'squat_low',
                'hands_on_ground': True,
                'tolerance': 15
            },
            'jumping_up': {
                'body_position': 'standing',
                'hands_overhead': True,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate burpee form"""
        feedback = {}
        
        body_pos = angles.get('body_position', '')
        hands_ground = angles.get('hands_on_ground', False)
        hands_overhead = angles.get('hands_overhead', False)
        
        # Plank validation
        if phase == 'plank':
            if body_pos == 'plank':
                feedback['plank'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good plank"
                )
            else:
                feedback['plank'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Extend to full plank"
                )
        
        # Jump validation
        elif phase == 'jumping_up':
            if hands_overhead:
                feedback['jump'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Great jump!"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for burpees
        
        Rep = complete 6-phase cycle
        """
        rep_done = False
        warnings = []
        
        body_pos = angle.get('body_position', '')
        hands_ground = angle.get('hands_on_ground', False)
        hands_overhead = angle.get('hands_overhead', False)
        
        # State machine through burpee phases
        if self.phase == "standing":
            # Start squatting down
            if body_pos in ['squatting', 'squat_low']:
                self.phase = "squatting"
                self.tempo_detector.start_phase('squatting')
        
        elif self.phase == "squatting":
            # Hands reach ground
            if hands_ground and body_pos == 'squat_low':
                self.phase = "hands_down"
        
        elif self.phase == "hands_down":
            # Jump/step back to plank
            if body_pos == 'plank':
                self.phase = "plank"
        
        elif self.phase == "plank":
            # Jump/step feet forward
            if body_pos == 'squat_low' and hands_ground:
                self.phase = "feet_forward"
        
        elif self.phase == "feet_forward":
            # Jump up
            if body_pos in ['standing', 'transitioning'] or hands_overhead:
                self.phase = "jumping_up"
        
        elif self.phase == "jumping_up":
            # Complete - return to standing
            if body_pos == 'standing' and hands_overhead:
                rep_done = True
                self.phase = "standing"
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
        
        # Track phase changes
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed burpee"""
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
            
            # Announce every rep (slower exercise)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        body_pos = angles.get('body_position', '')
        
        # Score based on correct position for phase
        if self.phase == 'standing' and body_pos == 'standing':
            form_score = 95.0
        elif self.phase == 'plank' and body_pos == 'plank':
            form_score = 95.0
        elif self.phase == 'hands_down' and angles.get('hands_on_ground'):
            form_score = 90.0
        elif self.phase == 'jumping_up' and angles.get('hands_overhead'):
            form_score = 95.0
        else:
            form_score = 80.0  # Transitioning
        
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
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("BURPEES V2 - Full Body Compound Cardio")
    print("="*70)
    print("\n✅ 6-phase movement tracking")
    print("✅ Hip height detection")
    print("✅ Hand position tracking")
    print("✅ Plank and jump validation")
    print("="*70)

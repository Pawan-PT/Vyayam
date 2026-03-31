"""
Tuck Jumps V2 - Explosive Plyometric Exercise

Reference Video: https://www.youtube.com/watch?v=KM3jTc9Tl4w
(Tuck Jumps - Proper Form)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class TuckJumpsV2:
    """
    Tuck Jumps - Explosive vertical jump with knee tuck
    
    Level: Advanced
    Category: Cardio/Plyometric
    Target: Explosive power, hip flexors, cardiovascular endurance
    
    Reference Video: https://www.youtube.com/watch?v=KM3jTc9Tl4w
    (Tuck Jumps Proper Form)
    
    Biomechanics:
    - Start standing
    - Explosive vertical jump
    - Pull knees up toward chest mid-air
    - Land softly with bent knees
    - Immediate rebound into next jump
    
    Movement Detection:
    - Vertical displacement (jump height)
    - Hip/knee flexion (tuck depth)
    - Landing detection
    - Jump frequency
    
    Phases:
    1. Standing (ready position)
    2. Loading (slight squat before jump)
    3. Jumping (takeoff)
    4. Tucked (knees pulled up)
    5. Landing (absorbing impact)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=KM3jTc9Tl4w"
    
    def __init__(self, target_reps=10):  # Fewer reps - very intense
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "standing"
        self.last_phase = "standing"
        
        # Jump tracking
        self.baseline_hip_y = None  # Calibrate standing hip height
        self.max_tuck_angle = 180  # Track best tuck in current jump
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 2  # Only 2 for advanced exercise
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
        Calculate angles for tuck jumps
        
        Key measurements:
        - Hip height (vertical displacement)
        - Hip flexion (tuck depth)
        - Knee flexion (tuck depth)
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
        
        # Hip height
        avg_hip_y = (lh[1] + rh[1]) / 2
        
        # Calibrate baseline on first few frames when standing
        if self.baseline_hip_y is None and self.phase == "standing":
            self.baseline_hip_y = avg_hip_y
        
        # Vertical displacement (negative = jumped up)
        if self.baseline_hip_y is not None:
            vertical_displacement = avg_hip_y - self.baseline_hip_y
        else:
            vertical_displacement = 0
        
        # Hip flexion (shoulder-hip-knee)
        left_hip_flexion = analyzer.calculate_angle(ls, lh, lk)
        right_hip_flexion = analyzer.calculate_angle(rs, rh, rk)
        avg_hip_flexion = (left_hip_flexion + right_hip_flexion) / 2
        
        # Knee flexion
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        avg_knee = (left_knee + right_knee) / 2
        
        # In air (vertical displacement indicates jump)
        in_air = vertical_displacement < -30
        
        # Tucked (knees pulled up - high hip flexion)
        is_tucked = avg_hip_flexion < 100 and avg_knee < 100
        
        return {
            'avg_hip_y': avg_hip_y,
            'vertical_displacement': vertical_displacement,
            'avg_hip_flexion': avg_hip_flexion,
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'in_air': in_air,
            'is_tucked': is_tucked,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk, 'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target positions for tuck jumps"""
        return {
            'standing': {
                'vertical_displacement': 0,
                'avg_knee': 170,
                'tolerance': 15
            },
            'loading': {
                'avg_knee': 130,    # Slight squat
                'tolerance': 20
            },
            'jumping': {
                'vertical_displacement': -50,  # Upward
                'tolerance': 30
            },
            'tucked': {
                'avg_hip_flexion': 80,   # Knees to chest
                'avg_knee': 80,
                'in_air': True,
                'tolerance': 20
            },
            'landing': {
                'avg_knee': 130,    # Bent knees
                'tolerance': 20
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate tuck jump form"""
        feedback = {}
        
        is_tucked = angles.get('is_tucked', False)
        avg_hip_flex = angles.get('avg_hip_flexion', 180)
        
        # Tuck validation
        if phase == 'tucked':
            if is_tucked and avg_hip_flex < 90:
                feedback['tuck'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Excellent tuck!"
                )
            elif avg_hip_flex > 120:
                feedback['tuck'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Pull knees higher"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for tuck jumps
        
        Rep = complete jump with tuck
        """
        rep_done = False
        warnings = []
        
        in_air = angle.get('in_air', False)
        is_tucked = angle.get('is_tucked', False)
        vert_disp = angle.get('vertical_displacement', 0)
        avg_knee = angle.get('avg_knee', 180)
        avg_hip_flex = angle.get('avg_hip_flexion', 180)
        
        # State machine
        if self.phase == "standing":
            # Detect loading (slight squat)
            if avg_knee < 150:
                self.phase = "loading"
                self.tempo_detector.start_phase('loading')
                self.max_tuck_angle = 180  # Reset for new jump
        
        elif self.phase == "loading":
            # Takeoff detected
            if vert_disp < -20 or in_air:
                self.phase = "jumping"
        
        elif self.phase == "jumping":
            # Look for tuck
            if is_tucked or avg_hip_flex < 120:
                self.phase = "tucked"
                # Track best tuck angle
                if avg_hip_flex < self.max_tuck_angle:
                    self.max_tuck_angle = avg_hip_flex
        
        elif self.phase == "tucked":
            # Extending for landing
            if avg_hip_flex > 130 or vert_disp > -10:
                self.phase = "landing"
        
        elif self.phase == "landing":
            # Landed - knees bent, back on ground
            if vert_disp > -5 and avg_knee < 160:
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
        """Calculate form score for completed tuck jump"""
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            
            # Bonus for good tuck depth
            if self.max_tuck_angle < 80:
                avg = min(100, avg + 5)
            
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
            
            # Announce every rep
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        is_tucked = angles.get('is_tucked', False)
        avg_hip_flex = angles.get('avg_hip_flexion', 180)
        in_air = angles.get('in_air', False)
        
        # Score based on tuck quality
        if self.phase == 'tucked':
            if is_tucked and avg_hip_flex < 80:
                form_score = 95.0  # Excellent tuck
            elif avg_hip_flex < 100:
                form_score = 85.0  # Good tuck
            elif avg_hip_flex < 120:
                form_score = 75.0  # Moderate tuck
            else:
                form_score = 65.0  # Weak tuck
        elif self.phase in ['jumping', 'landing']:
            form_score = 85.0
        else:
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
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps,
            'best_tuck_angle': round(self.max_tuck_angle, 1)
        }


if __name__ == "__main__":
    print("="*70)
    print("TUCK JUMPS V2 - Explosive Plyometric")
    print("="*70)
    print("\n✅ Vertical jump detection")
    print("✅ Tuck depth tracking")
    print("✅ Hip/knee flexion measurement")
    print("✅ Landing validation")
    print("="*70)

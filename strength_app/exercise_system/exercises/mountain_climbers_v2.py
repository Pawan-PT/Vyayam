"""
Mountain Climbers V2 - Full Body Cardio

Reference Video: https://www.youtube.com/watch?v=nmwgirgXLYM
(Mountain Climbers - Proper Form)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class MountainClimbersV2:
    """
    Mountain Climbers - Dynamic plank cardio
    
    Level: Intermediate
    Category: Cardio/Core
    Target: Cardiovascular endurance, core stability, hip flexors
    
    Reference Video: https://www.youtube.com/watch?v=nmwgirgXLYM
    (Mountain Climbers Proper Form)
    
    Biomechanics:
    - Start in plank position (high plank)
    - Alternating knee drives toward chest
    - Hips stay low (maintain plank)
    - Fast running motion in place
    
    Movement Detection:
    - Plank position (shoulders over wrists)
    - Hip height (shouldn't pike up)
    - Knee drive (hip flexion)
    - Alternating legs
    
    Phases (per leg):
    1. Plank (both legs extended)
    2. Driving left (left knee coming forward)
    3. Left peak (left knee at chest)
    4. Returning left (left leg going back)
    5. Driving right (right knee coming forward)
    6. Right peak (right knee at chest)
    7. Returning right (right leg going back)
    
    Rep = both legs driven forward once each
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=nmwgirgXLYM"
    
    def __init__(self, target_reps=20):  # 20 = 10 per leg
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "plank"
        self.last_phase = "plank"
        
        # Leg tracking
        self.left_drives = 0
        self.right_drives = 0
        self.current_working_leg = None
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 4  # 2 per leg
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
        Calculate angles for mountain climbers
        
        Key measurements:
        - Hip height (maintain plank)
        - Hip flexion (knee drive)
        - Shoulder position (plank stability)
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
        
        # Hip height (should be roughly level with shoulders in plank)
        avg_hip_y = (lh[1] + rh[1]) / 2
        avg_shoulder_y = (ls[1] + rs[1]) / 2
        hip_height_diff = avg_hip_y - avg_shoulder_y
        
        # Plank position check (hips shouldn't be too high)
        good_plank = -20 < hip_height_diff < 60
        
        # Hip flexion (knee position relative to hip)
        # Forward knee drive = knee x-position close to hip x-position
        left_hip_flexion = analyzer.calculate_angle(ls, lh, lk)
        right_hip_flexion = analyzer.calculate_angle(rs, rh, rk)
        
        # Determine which knee is forward (smaller angle = more flexed)
        if left_hip_flexion < 110 and left_hip_flexion < right_hip_flexion - 20:
            working_leg = 'left'
            working_hip_flexion = left_hip_flexion
        elif right_hip_flexion < 110 and right_hip_flexion < left_hip_flexion - 20:
            working_leg = 'right'
            working_hip_flexion = right_hip_flexion
        else:
            working_leg = None
            working_hip_flexion = min(left_hip_flexion, right_hip_flexion)
        
        return {
            'hip_height_diff': hip_height_diff,
            'good_plank': good_plank,
            'left_hip_flexion': left_hip_flexion,
            'right_hip_flexion': right_hip_flexion,
            'working_leg': working_leg,
            'working_hip_flexion': working_hip_flexion,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk, 'la': la, 'ra': ra,
                'lw': lw, 'rw': rw
            }
        }
    
    def get_target_poses(self):
        """Target positions for mountain climbers"""
        return {
            'plank': {
                'hip_height_diff': 20,      # Hips level
                'left_hip_flexion': 160,    # Both legs extended
                'right_hip_flexion': 160,
                'tolerance': 15
            },
            'driving': {
                'working_hip_flexion': 120,  # Mid-drive
                'tolerance': 20
            },
            'peak': {
                'working_hip_flexion': 70,   # Knee at chest
                'tolerance': 15
            },
            'returning': {
                'working_hip_flexion': 120,  # Returning
                'tolerance': 20
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate mountain climber form"""
        feedback = {}
        
        good_plank = angles.get('good_plank', False)
        
        # Plank position is critical throughout
        if not good_plank:
            feedback['plank'] = JointFeedback(
                FormStatus.NEEDS_ADJUSTMENT, 0, "Keep hips low"
            )
        
        # Knee drive validation
        if phase == 'peak':
            working_flex = angles.get('working_hip_flexion', 180)
            if working_flex < 80:
                feedback['drive'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good drive!"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for mountain climbers
        
        Each knee drive = 1 rep (alternating legs)
        """
        rep_done = False
        warnings = []
        
        working_leg = angle.get('working_leg')
        working_flex = angle.get('working_hip_flexion', 180)
        
        # State machine for one knee drive
        if self.phase == "plank":
            # Detect start of drive
            if working_leg is not None and working_flex < 140:
                self.phase = "driving"
                self.current_working_leg = working_leg
                self.tempo_detector.start_phase('driving')
        
        elif self.phase == "driving":
            # Reached peak flexion
            if working_flex < 90:
                self.phase = "peak"
        
        elif self.phase == "peak":
            # Starting to extend
            if working_flex > 100:
                self.phase = "returning"
        
        elif self.phase == "returning":
            # Completed one drive
            if working_flex > 140:
                rep_done = True
                self.phase = "plank"
                
                # Track which leg
                if self.current_working_leg == 'left':
                    self.left_drives += 1
                elif self.current_working_leg == 'right':
                    self.right_drives += 1
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
                
                self.current_working_leg = None
        
        # Track phase changes
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed drive"""
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
                # Only announce every other rep (too fast)
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
            
            # Announce every 10 reps (very fast exercise)
            if self.rep_count % 10 == 0:
                voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        good_plank = angles.get('good_plank', False)
        working_flex = angles.get('working_hip_flexion', 180)
        
        # Plank position is weighted heavily
        plank_score = 95.0 if good_plank else 70.0
        
        # Knee drive score
        if self.phase == 'peak':
            if working_flex < 80:
                drive_score = 95.0
            elif working_flex < 100:
                drive_score = 85.0
            else:
                drive_score = 70.0
        else:
            drive_score = 80.0
        
        # Combined score (60% plank, 40% drive)
        form_score = (plank_score * 0.6) + (drive_score * 0.4)
        
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
            'left_drives': self.left_drives,
            'right_drives': self.right_drives,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("MOUNTAIN CLIMBERS V2 - Full Body Cardio")
    print("="*70)
    print("\n✅ Plank position tracking")
    print("✅ Hip flexion detection")
    print("✅ Alternating leg drives")
    print("✅ Core stability validation")
    print("="*70)

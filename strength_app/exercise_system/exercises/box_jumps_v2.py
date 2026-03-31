"""
Box Jumps V2 - Explosive Power Exercise (OPTIONAL)

Reference Video: https://www.youtube.com/watch?v=NBY9-kTuHEk
(Box Jumps - Proper Form and Technique)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class BoxJumpsV2:
    """
    Box Jumps - Explosive vertical power exercise
    
    Level: Advanced
    Category: Cardio/Plyometric/Power
    Target: Explosive power, vertical jump, lower body strength
    
    Reference Video: https://www.youtube.com/watch?v=NBY9-kTuHEk
    (Box Jumps Proper Technique)
    
    Biomechanics:
    - Start in athletic stance
    - Load with slight squat
    - Explosive jump onto elevated surface
    - Land softly in squat position
    - Step or jump down
    - Reset for next rep
    
    Movement Detection:
    - Hip height change (ground vs elevated)
    - Jump loading (pre-jump squat)
    - Landing position
    - Hip height differential tracking
    
    Phases:
    1. Ground stance (ready on ground)
    2. Loading (squat before jump)
    3. Jumping (explosive takeoff)
    4. Landing (on box, knees bent)
    5. Box stance (standing on box)
    6. Stepping down (returning to ground)
    
    Note: Requires user to position themselves so camera can see both
    ground level and box level.
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=NBY9-kTuHEk"
    
    def __init__(self, target_reps=8):  # Fewer reps - very intense
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "ground_stance"
        self.last_phase = "ground_stance"
        
        # Height calibration
        self.ground_hip_y = None  # Calibrate ground level
        self.box_hip_y = None     # Detect box level
        self.box_height_detected = False
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 2  # Only 2 for advanced
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
        Calculate angles for box jumps
        
        Key measurements:
        - Hip height (ground vs box)
        - Knee angles (loading, landing)
        - Vertical displacement
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
        
        # Calibrate ground level (first frames)
        if self.ground_hip_y is None and self.phase == "ground_stance":
            self.ground_hip_y = avg_hip_y
        
        # Vertical displacement from ground
        if self.ground_hip_y is not None:
            vertical_displacement = avg_hip_y - self.ground_hip_y
        else:
            vertical_displacement = 0
        
        # Detect box height when landed on elevated surface
        if not self.box_height_detected and vertical_displacement < -80:
            # Significantly elevated - on box
            self.box_hip_y = avg_hip_y
            self.box_height_detected = True
        
        # Classify position
        if self.box_height_detected and self.box_hip_y is not None:
            # Compare to box height
            diff_from_box = abs(avg_hip_y - self.box_hip_y)
            diff_from_ground = abs(avg_hip_y - self.ground_hip_y)
            
            if diff_from_box < 40:
                position_level = "box"
            elif diff_from_ground < 40:
                position_level = "ground"
            else:
                position_level = "transitioning"
        else:
            # No box detected yet
            if vertical_displacement < -40:
                position_level = "elevated"
            else:
                position_level = "ground"
        
        # Knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        avg_knee = (left_knee + right_knee) / 2
        
        return {
            'avg_hip_y': avg_hip_y,
            'vertical_displacement': vertical_displacement,
            'position_level': position_level,
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk, 'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target positions for box jumps"""
        return {
            'ground_stance': {
                'position_level': 'ground',
                'avg_knee': 165,
                'tolerance': 15
            },
            'loading': {
                'position_level': 'ground',
                'avg_knee': 120,  # Squat
                'tolerance': 20
            },
            'jumping': {
                'position_level': 'transitioning',
                'tolerance': 40
            },
            'landing': {
                'position_level': 'box',
                'avg_knee': 130,  # Soft landing
                'tolerance': 20
            },
            'box_stance': {
                'position_level': 'box',
                'avg_knee': 165,
                'tolerance': 15
            },
            'stepping_down': {
                'position_level': 'transitioning',
                'tolerance': 40
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate box jump form"""
        feedback = {}
        
        position = angles.get('position_level', '')
        avg_knee = angles.get('avg_knee', 180)
        
        # Landing validation (soft landing with bent knees)
        if phase == 'landing':
            if avg_knee < 140:
                feedback['landing'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Soft landing!"
                )
            elif avg_knee > 160:
                feedback['landing'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Bend knees on landing"
                )
        
        # Loading validation
        elif phase == 'loading':
            if avg_knee < 130:
                feedback['load'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good load"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for box jumps
        
        Rep = complete cycle (ground → box → ground)
        """
        rep_done = False
        warnings = []
        
        position = angle.get('position_level', '')
        avg_knee = angle.get('avg_knee', 180)
        
        # State machine
        if self.phase == "ground_stance":
            # Start loading
            if avg_knee < 150:
                self.phase = "loading"
                self.tempo_detector.start_phase('loading')
        
        elif self.phase == "loading":
            # Explosive takeoff
            if position in ['transitioning', 'elevated', 'box'] or avg_knee > 140:
                self.phase = "jumping"
        
        elif self.phase == "jumping":
            # Landed on box
            if position == 'box' and avg_knee < 150:
                self.phase = "landing"
        
        elif self.phase == "landing":
            # Stand up on box
            if avg_knee > 155:
                self.phase = "box_stance"
        
        elif self.phase == "box_stance":
            # Step down
            if position in ['transitioning', 'ground']:
                self.phase = "stepping_down"
        
        elif self.phase == "stepping_down":
            # Complete - back on ground
            if position == 'ground' and avg_knee > 150:
                rep_done = True
                self.phase = "ground_stance"
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
        
        # Track phase changes
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed box jump"""
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
            
            # Announce every rep (slower, intense exercise)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        position = angles.get('position_level', '')
        avg_knee = angles.get('avg_knee', 180)
        
        # Score based on position and knee angle
        if self.phase == 'landing' and position == 'box' and avg_knee < 140:
            form_score = 95.0  # Perfect soft landing
        elif self.phase == 'loading' and avg_knee < 130:
            form_score = 90.0  # Good loading
        elif self.phase in ['ground_stance', 'box_stance']:
            form_score = 85.0
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
        
        box_height = 0
        if self.box_height_detected and self.ground_hip_y and self.box_hip_y:
            box_height = abs(self.ground_hip_y - self.box_hip_y)
        
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'box_height_pixels': round(box_height, 0),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("BOX JUMPS V2 - Explosive Power (OPTIONAL)")
    print("="*70)
    print("\n✅ Height tracking (ground vs box)")
    print("✅ Explosive jump detection")
    print("✅ Soft landing validation")
    print("✅ Box height auto-calibration")
    print("\nNote: Requires elevated surface (box/platform)")
    print("="*70)

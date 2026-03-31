"""
Sprint in Place V2 - High-Intensity Running Drill

Reference Video: https://www.youtube.com/watch?v=8opcQdC-V-U
(High Knees Sprint in Place)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SprintInPlaceV2:
    """
    Sprint in Place - High-intensity running drill
    
    Level: Intermediate
    Category: Cardio
    Target: Cardiovascular endurance, hip flexors, running form, speed
    
    Reference Video: https://www.youtube.com/watch?v=8opcQdC-V-U
    (High Knees Sprint in Place)
    
    Biomechanics:
    - Fast alternating knee drives
    - Knees lift to hip height (90° hip flexion)
    - Arms pump in opposition to legs
    - Upper body upright
    - Fast cadence (faster than high knees)
    
    Movement Detection:
    - Knee height (hip flexion)
    - Alternating legs
    - High cadence detection
    - Upright posture
    
    Phases (per leg):
    1. Stance (foot on ground)
    2. Driving (knee lifting)
    3. Peak (knee at hip height)
    4. Lowering (foot returning to ground)
    
    Rep = each knee drive (alternating)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=8opcQdC-V-U"
    
    def __init__(self, target_reps=40):  # High reps for cardio
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "stance"
        self.last_phase = "stance"
        
        # Leg tracking
        self.left_drives = 0
        self.right_drives = 0
        self.current_working_leg = None
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 6  # 3 per leg
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        # Cadence tracking
        self.last_rep_time = None
        self.cadence_samples = []  # Track steps per second
        
        # Detectors
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate angles for sprint in place
        
        Key measurements:
        - Hip flexion (knee drive height)
        - Posture (upright torso)
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
        
        # Hip flexion angles
        left_hip_flexion = analyzer.calculate_angle(ls, lh, lk)
        right_hip_flexion = analyzer.calculate_angle(rs, rh, rk)
        
        # Determine working leg (higher knee = more flexed hip)
        if left_hip_flexion < 110 and left_hip_flexion < right_hip_flexion - 20:
            working_leg = 'left'
            working_hip_flexion = left_hip_flexion
        elif right_hip_flexion < 110 and right_hip_flexion < left_hip_flexion - 20:
            working_leg = 'right'
            working_hip_flexion = right_hip_flexion
        else:
            working_leg = None
            working_hip_flexion = min(left_hip_flexion, right_hip_flexion)
        
        # Posture check (torso should be upright)
        # Check shoulder-hip alignment
        avg_shoulder_y = (ls[1] + rs[1]) / 2
        avg_hip_y = (lh[1] + rh[1]) / 2
        posture_good = avg_shoulder_y < avg_hip_y  # Shoulders above hips
        
        return {
            'left_hip_flexion': left_hip_flexion,
            'right_hip_flexion': right_hip_flexion,
            'working_leg': working_leg,
            'working_hip_flexion': working_hip_flexion,
            'posture_good': posture_good,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk, 'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target positions for sprint in place"""
        return {
            'stance': {
                'working_hip_flexion': 160,  # Leg mostly extended
                'tolerance': 15
            },
            'driving': {
                'working_hip_flexion': 120,  # Mid-drive
                'tolerance': 20
            },
            'peak': {
                'working_hip_flexion': 85,   # Knee at hip height
                'tolerance': 15
            },
            'lowering': {
                'working_hip_flexion': 120,  # Returning
                'tolerance': 20
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate sprint form"""
        feedback = {}
        
        posture_good = angles.get('posture_good', False)
        working_flex = angles.get('working_hip_flexion', 180)
        
        # Posture validation
        if not posture_good:
            feedback['posture'] = JointFeedback(
                FormStatus.NEEDS_ADJUSTMENT, 0, "Stay upright"
            )
        
        # Knee drive validation
        if phase == 'peak':
            if working_flex < 90:
                feedback['drive'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good drive!"
                )
            elif working_flex > 110:
                feedback['drive'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Drive knee higher"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for sprint in place
        
        Each knee drive = 1 rep (alternating)
        """
        rep_done = False
        warnings = []
        
        working_leg = angle.get('working_leg')
        working_flex = angle.get('working_hip_flexion', 180)
        
        # State machine for one knee drive
        if self.phase == "stance":
            # Detect start of drive
            if working_leg is not None and working_flex < 140:
                self.phase = "driving"
                self.current_working_leg = working_leg
                self.tempo_detector.start_phase('driving')
        
        elif self.phase == "driving":
            # Reached peak flexion
            if working_flex < 100:
                self.phase = "peak"
        
        elif self.phase == "peak":
            # Starting to lower
            if working_flex > 110:
                self.phase = "lowering"
        
        elif self.phase == "lowering":
            # Completed one drive
            if working_flex > 140:
                rep_done = True
                self.phase = "stance"
                
                # Track which leg
                if self.current_working_leg == 'left':
                    self.left_drives += 1
                elif self.current_working_leg == 'right':
                    self.right_drives += 1
                
                # Track cadence
                current_time = time.time()
                if self.last_rep_time is not None:
                    time_diff = current_time - self.last_rep_time
                    if time_diff > 0:
                        cadence = 1.0 / time_diff  # Steps per second
                        self.cadence_samples.append(cadence)
                        if len(self.cadence_samples) > 10:
                            self.cadence_samples.pop(0)
                self.last_rep_time = current_time
                
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
            
            # Bonus for maintaining high cadence
            if self.cadence_samples:
                avg_cadence = sum(self.cadence_samples) / len(self.cadence_samples)
                if avg_cadence > 3.0:  # More than 3 steps/second
                    avg = min(100, avg + 3)
            
            return avg
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        """Handle rep completion"""
        if self.probation_mode:
            if form_score >= 85:
                self.practice_reps_completed += 1
                # Only announce every 3 reps (very fast)
                if self.practice_reps_completed % 3 == 0:
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
        
        posture_good = angles.get('posture_good', False)
        working_flex = angles.get('working_hip_flexion', 180)
        
        # Posture weighted heavily
        posture_score = 95.0 if posture_good else 75.0
        
        # Knee drive score
        if self.phase == 'peak':
            if working_flex < 85:
                drive_score = 95.0
            elif working_flex < 100:
                drive_score = 85.0
            else:
                drive_score = 70.0
        else:
            drive_score = 80.0
        
        # Combined score (50% posture, 50% drive)
        form_score = (posture_score * 0.5) + (drive_score * 0.5)
        
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
        
        avg_cadence = (
            sum(self.cadence_samples) / len(self.cadence_samples)
            if self.cadence_samples else 0
        )
        
        return {
            'reps_completed': self.rep_count,
            'left_drives': self.left_drives,
            'right_drives': self.right_drives,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'avg_cadence_sps': round(avg_cadence, 2),  # Steps per second
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("SPRINT IN PLACE V2 - High-Intensity Running")
    print("="*70)
    print("\n✅ Hip flexion tracking")
    print("✅ Alternating knee drives")
    print("✅ Cadence measurement")
    print("✅ Posture validation")
    print("="*70)

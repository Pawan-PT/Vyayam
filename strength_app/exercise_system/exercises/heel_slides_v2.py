"""
Heel Slides V2 - ROM Restoration Exercise

Reference Video: https://www.youtube.com/watch?v=QNaJoQ8nWNc
(Heel Slides - Knee ROM Restoration)

CHANGES FROM V1:
- Added form calculator integration
- Integrated voice coach V2 with atomic sentences
- Added AR overlay V2 with Green/Yellow/Red
- Improved hold counting at bent position (2 seconds)
- Added stability tracking
- Fixed practice mode (3 GREEN reps required)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HeelSlidesV2:
    """
    Heel Slides - ROM Restoration
    
    Level: Foundation
    Category: Mobility/ROM
    Target: Knee flexion range of motion
    
    Reference Video: https://www.youtube.com/watch?v=QNaJoQ8nWNc
    (Heel Slides Technique)
    
    Biomechanics:
    - Primary angle: Knee flexion (hip → knee → ankle)
    - Straight: 170-180° (starting position)
    - Target bent: 80-110° (goal ROM - patient dependent)
    - Hold: 2 seconds at maximum flexion
    - Critical: Heel stays on ground, smooth sliding motion
    
    Phases:
    1. Straight (starting position)
    2. Sliding (bringing heel toward buttocks)
    3. Bent (maximum comfortable flexion)
    4. Holding (2-second hold)
    5. Returning (sliding heel back to straight)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=QNaJoQ8nWNc"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "straight"
        self.last_phase = "straight"
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        # Hold tracking
        self.hold_start_time = None
        self.hold_duration_required = 2.0
        self.hold_announced_seconds = set()
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        # Detectors
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """Calculate knee angles for heel slides"""
        # Extract joints
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Calculate knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Smooth
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')
        
        avg_knee = (left_knee + right_knee) / 2
        
        # Check if heels lifted (should stay on ground)
        ankle_height_diff = abs(la[1] - ra[1])
        heel_lifted = ankle_height_diff > 40
        
        # Check symmetry
        knee_diff = abs(left_knee - right_knee)
        asymmetric = knee_diff > 20
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'knee_diff': knee_diff,
            'heel_lifted': heel_lifted,
            'asymmetric': asymmetric,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'straight': {
                'avg_knee': 175,
                'tolerance': 8
            },
            'sliding': {
                'avg_knee': 135,
                'tolerance': 15
            },
            'bent': {
                'avg_knee': 90,       # Target ROM (flexible)
                'tolerance': 15       # Wide tolerance - patient dependent
            },
            'holding': {
                'avg_knee': 90,
                'tolerance': 15
            },
            'returning': {
                'avg_knee': 135,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form"""
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # CRITICAL: Heels must stay on ground
        if angles.get('heel_lifted', False):
            feedback['heel'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Keep heels on ground"
            )
        
        # Check asymmetry
        if angles.get('asymmetric', False):
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['knee_diff'],
                message="Slide both heels evenly"
            )
        
        # Phase-specific validation
        knee_angle = angles.get('avg_knee', 0)
        knee_target = targets['avg_knee']
        knee_tolerance = targets['tolerance']
        
        if phase == 'straight':
            if knee_angle >= 170:
                feedback['position'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=knee_angle,
                    message="Good starting position"
                )
            else:
                feedback['position'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=knee_angle,
                    message="Straighten legs first"
                )
        
        elif phase in ['bent', 'holding']:
            # Flexible ROM target - depends on patient
            if 80 <= knee_angle <= 110:
                feedback['rom'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=knee_angle,
                    message="Excellent ROM"
                )
            elif 110 < knee_angle <= 130:
                feedback['rom'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=knee_angle,
                    message="Good progress"
                )
            elif knee_angle > 150:
                feedback['rom'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=knee_angle,
                    message="Slide heel closer"
                )
        
        elif phase == 'sliding':
            if abs(knee_angle - knee_target) <= knee_tolerance:
                feedback['movement'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=knee_angle,
                    message="Smooth slide"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update rep counter"""
        rep_done = False
        warnings = []
        
        # Phase state machine
        if self.phase == "straight":
            if angle >= 165:
                if self.tempo_detector.current_phase != 'straight':
                    self.tempo_detector.start_phase('straight')
            
            if angle < 160:
                self.phase = "sliding"
                self.tempo_detector.start_phase('sliding')
                voice.speak("Slide heel in", priority=False)
        
        elif self.phase == "sliding":
            if angle <= 130:
                self.phase = "bent"
                self.tempo_detector.start_phase('bent')
        
        elif self.phase == "bent":
            # Start hold timer
            if self.hold_start_time is None:
                self.hold_start_time = time.time()
                self.hold_announced_seconds = set()
                self.phase = "holding"
                voice.speak("Hold position", priority=False)
        
        elif self.phase == "holding":
            if self.hold_start_time:
                hold_elapsed = time.time() - self.hold_start_time
                current_second = int(hold_elapsed)
                
                # Count each second
                if current_second > 0 and current_second not in self.hold_announced_seconds:
                    self.hold_announced_seconds.add(current_second)
                    voice.count_hold_seconds(current_second, int(self.hold_duration_required))
                
                # Check if hold complete
                if hold_elapsed >= self.hold_duration_required:
                    self.phase = "returning"
                    self.hold_start_time = None
                    voice.speak("Slide back slowly", priority=False)
        
        elif self.phase == "returning":
            if angle >= 165:
                # Rep complete
                rep_done = True
                self.phase = "straight"
                
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate average form score for completed rep"""
        if self.current_rep_form_scores:
            avg_form = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg_form
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
                voice.provide_ar_feedback(form_score)
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
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
    print("HEEL SLIDES V2")
    print("="*70)
    print("\n✅ ROM restoration with 2-second hold")
    print("✅ Heel-on-ground tracking")
    print("✅ Form calculator integration")
    print("✅ Voice V2 with hold counting")
    print("✅ AR overlay V2")
    print("="*70)
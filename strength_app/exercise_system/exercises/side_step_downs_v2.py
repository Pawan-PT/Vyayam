"""
Side Step Downs V2 - Lateral eccentric step down exercise

NEW EXERCISE for eccentric control and lateral stability

Level: Intermediate
Category: Strength (Eccentric), Balance
Target: Quadriceps, glutes, eccentric control
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback
from ..core.unilateral_handler import UnilateralExerciseHandler, Side


class SideStepDownsV2:
    """
    Side Step Downs - Lateral eccentric step down from platform
    
    Level: Intermediate
    Category: Strength (Eccentric), Balance
    Target: Quadriceps, glutes, hip abductors, eccentric control
    
    Reference Video: https://www.youtube.com/watch?v=XZ9L3OU0NfM
    (Lateral Step Down Exercise - Proper Form)
    
    Biomechanics:
    - Primary: Working leg knee flexion (ECCENTRIC control)
    - Secondary: Working leg hip flexion
    - Starting: 175° knee/hip extension (standing on platform)
    - Bottom: 110° knee/hip flexion (controlled descent)
    - CRITICAL: Slow descent (3+ seconds), controlled return
    
    UNILATERAL: Track working leg (stays on platform)
    - Left leg works (standing on left, lowering right) → complete reps
    - Switch sides  
    - Right leg works (standing on right, lowering left) → complete reps
    
    Phases:
    1. Top (standing on platform, one leg)
    2. Descending (controlled eccentric lowering)
    3. Touch (opposite foot taps ground lightly)
    4. Ascending (return to standing)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=XZ9L3OU0NfM"
    
    def __init__(self, target_reps=10):
        self.target_reps_per_side = target_reps
        
        # UNILATERAL HANDLER
        self.unilateral = UnilateralExerciseHandler(
            total_reps=target_reps,
            exercise_name="Side Step Downs"
        )
        
        self.phase = "top"
        self.last_phase = "top"
        
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        # Custom tempo for eccentric exercises
        self.tempo_detector.phase_durations['descending'] = (3.0, 5.0)  # 3-5 seconds descent
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
        self.voice.speak("Stand on left leg", priority=True)
    
    def calculate_angles(self, analyzer, results, shape):
        """Calculate angles for both legs"""
        # Left side
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        
        # Right side
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Calculate angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        left_hip = analyzer.calculate_angle(ls, lh, lk)
        right_hip = analyzer.calculate_angle(rs, rh, rk)
        
        # Smooth
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'left_hip': left_hip,
            'right_hip': right_hip,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_current_side_angles(self, all_angles):
        """Filter to current working leg"""
        return self.unilateral.filter_angles_for_current_side(all_angles)
    
    def get_current_side_joints(self, all_joints):
        """Filter joints to current side"""
        return self.unilateral.filter_joints_for_current_side(all_joints)
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'top': {
                'knee': 175,  # Straight, standing on platform
                'hip': 175,
                'tolerance': 10
            },
            'descending': {
                'knee': 140,  # Controlled descent
                'hip': 145,
                'tolerance': 15
            },
            'touch': {
                'knee': 110,  # Deep bend, opposite foot touches ground
                'hip': 120,
                'tolerance': 12
            },
            'ascending': {
                'knee': 150,  # Coming back up
                'hip': 155,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form - emphasis on control"""
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Knee angle
        knee_angle = angles.get('knee', 0)
        knee_target = targets['knee']
        
        if abs(knee_angle - knee_target) <= 12:
            feedback['knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_angle,
                message="Good control"
            )
        else:
            feedback['knee'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_angle,
                message="Control the descent"
            )
        
        # Hip angle
        hip_angle = angles.get('hip', 0)
        hip_target = targets['hip']
        
        if abs(hip_angle - hip_target) <= 12:
            feedback['hip'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=hip_angle,
                message="Good hip position"
            )
        else:
            feedback['hip'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=hip_angle,
                message="Adjust hip"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update rep counter"""
        rep_done = False
        warnings = []
        
        # State machine for step down (eccentric focus)
        if self.phase == "top" and angle < 165:
            self.phase = "descending"
            self.tempo_detector.start_phase('descending')
            voice.speak("Lower slowly", priority=False)
        
        elif self.phase == "descending" and angle < 120:
            self.phase = "touch"
            self.tempo_detector.start_phase('touch')
            voice.speak("Light tap", priority=False)
        
        elif self.phase == "touch" and angle > 125:
            self.phase = "ascending"
            self.tempo_detector.start_phase('ascending')
            voice.speak("Push back up", priority=False)
        
        elif self.phase == "ascending" and angle > 170:
            # Rep complete
            rep_done = True
            self.phase = "top"
            
            form_score = self._calculate_rep_form_score()
            
            # Extra check for tempo (eccentric exercises need slow descent)
            tempo_data = self.tempo_detector.check_tempo()
            if tempo_data.get('too_fast'):
                form_score = min(form_score, 70)  # Penalty for rushing eccentric
            
            self._handle_rep_completion(form_score, voice)
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score"""
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
                voice.provide_ar_feedback(form_score)
        else:
            self.unilateral.increment_rep(form_score)
            current_reps = self.unilateral.get_reps_completed_current_side()
            voice.announce_rep(current_reps, self.target_reps_per_side, form_score)
    
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
        
        # Extra penalty for going too fast on eccentric phase
        if self.phase == "descending" and tempo_data.get('too_fast'):
            form_score -= 20  # Significant penalty
        
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
    
    def check_side_switch_needed(self):
        """Check if need to switch sides"""
        return self.unilateral.needs_side_switch
    
    def handle_side_switch(self, frame):
        """Handle side switch UI"""
        self.unilateral.draw_switch_prompt(frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            self.unilateral.switch_to_right_side()
            self.voice.speak("Stand on right leg", priority=True)
            self.probation_mode = True
            self.practice_reps_completed = 0
    
    def get_stats(self):
        """Get statistics"""
        return self.unilateral.get_stats()


if __name__ == "__main__":
    print("SIDE STEP DOWNS V2 - Eccentric step down exercise")
    print("Controlled eccentric loading")
    print("Ready to run!")
"""
Side Step Ups V2 - Lateral step up exercise

NEW EXERCISE for lateral strength and stability

Level: Intermediate
Category: Strength, Balance
Target: Quadriceps, glutes, hip abductors
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback
from ..core.unilateral_handler import UnilateralExerciseHandler, Side


class SideStepUpsV2:
    """
    Side Step Ups - Lateral step up onto platform
    
    Level: Intermediate
    Category: Strength, Balance
    Target: Quadriceps, glutes, hip abductors, lateral stability
    
    Reference Video: https://www.youtube.com/watch?v=5_fSJI8Qfng
    (Lateral Step Up Exercise - Proper Technique)
    
    Biomechanics:
    - Primary: Leading leg knee extension (hip → knee → ankle)
    - Secondary: Leading leg hip extension (shoulder → hip → knee)
    - Starting: 90° knee/hip flexion (leg on platform)
    - Top: 175° knee/hip extension (standing on platform)
    
    UNILATERAL: Track leading leg only
    - Left leg leads (step up with left) → complete reps
    - Switch sides
    - Right leg leads (step up with right) → complete reps
    
    Phases:
    1. Ground (both feet on floor, facing platform)
    2. Placing (leading foot on platform)
    3. Pushing (extending leading leg)
    4. Top (standing on platform, both legs straight)
    5. Descending (controlled lowering back to ground)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=5_fSJI8Qfng"
    
    def __init__(self, target_reps=10):
        self.target_reps_per_side = target_reps
        
        # UNILATERAL HANDLER
        self.unilateral = UnilateralExerciseHandler(
            total_reps=target_reps,
            exercise_name="Side Step Ups"
        )
        
        self.phase = "ground"
        self.last_phase = "ground"
        
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
        self.voice.speak("Position for left leg", priority=True)
    
    def calculate_angles(self, analyzer, results, shape):
        """Calculate angles for both legs (handler filters to current)"""
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
        """Filter to current leading leg"""
        return self.unilateral.filter_angles_for_current_side(all_angles)
    
    def get_current_side_joints(self, all_joints):
        """Filter joints to current side"""
        return self.unilateral.filter_joints_for_current_side(all_joints)
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'ground': {
                'knee': 175,  # Nearly straight
                'hip': 175,
                'tolerance': 10
            },
            'placing': {
                'knee': 90,   # Leg on platform, bent
                'hip': 90,
                'tolerance': 15
            },
            'pushing': {
                'knee': 130,  # Extending
                'hip': 140,
                'tolerance': 15
            },
            'top': {
                'knee': 175,  # Fully extended on platform
                'hip': 175,
                'tolerance': 10
            },
            'descending': {
                'knee': 120,  # Controlled bend
                'hip': 130,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form for current phase"""
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Knee angle
        knee_angle = angles.get('knee', 0)
        knee_target = targets['knee']
        
        if abs(knee_angle - knee_target) <= 12:
            feedback['knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_angle,
                message="Good leg position"
            )
        else:
            feedback['knee'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_angle,
                message="Adjust leg angle"
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
        """Update rep counter with state machine"""
        rep_done = False
        warnings = []
        
        # State machine for step up
        if self.phase == "ground" and angle < 140:
            self.phase = "placing"
            self.tempo_detector.start_phase('placing')
            voice.speak("Place foot", priority=False)
        
        elif self.phase == "placing" and angle < 100:
            self.phase = "pushing"
            self.tempo_detector.start_phase('pushing')
            voice.speak("Push up", priority=False)
        
        elif self.phase == "pushing" and angle > 160:
            self.phase = "top"
            self.tempo_detector.start_phase('top')
            voice.speak("Stand tall", priority=False)
        
        elif self.phase == "top" and angle < 165:
            self.phase = "descending"
            self.tempo_detector.start_phase('descending')
            voice.speak("Control down", priority=False)
        
        elif self.phase == "descending" and angle > 170:
            # Rep complete
            rep_done = True
            self.phase = "ground"
            
            form_score = self._calculate_rep_form_score()
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
            # Increment unilateral handler
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
            self.voice.speak("Position for right leg", priority=True)
            self.probation_mode = True
            self.practice_reps_completed = 0
    
    def get_stats(self):
        """Get statistics"""
        return self.unilateral.get_stats()


if __name__ == "__main__":
    print("SIDE STEP UPS V2 - Lateral step up exercise")
    print("Unilateral strength and balance training")
    print("Ready to run!")
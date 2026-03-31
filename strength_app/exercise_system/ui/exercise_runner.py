"""
Streamlit Exercise Runner
UI-based exercise execution with real-time feedback

FIXED: Corrected class names VoiceCoachV2 and AROverlayV2
"""

import streamlit as st
import cv2
import time
import numpy as np
from PIL import Image

from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2  # ✅ FIXED: Was VoiceCoach
from ..core.visual_overlay import JointHighlighter
from ..core.ar_overlay_v2 import AROverlayV2  # ✅ FIXED: Was AROverlaySystem
from ..core.data_models import FormStatus


class ExerciseRunner:
    """Streamlit-based exercise runner with UI controls"""
    
    def __init__(self, exercise, enable_voice=True):
        self.exercise = exercise
        self.voice = VoiceCoachV2() if enable_voice else None  # ✅ FIXED: Was VoiceCoach()
        
        self.analyzer = PoseAnalyzer()
        self.highlighter = JointHighlighter()
        self.ar_system = AROverlayV2()  # ✅ FIXED: Was AROverlaySystem()
        
        self.start_time = None
        self.frame_placeholder = None
    
    def run(self):
        """Run exercise with Streamlit UI"""
        st.markdown(f"## {self.exercise.__class__.__name__}")
        
        # Create UI elements
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rep_counter = st.empty()
        with col2:
            form_score = st.empty()
        with col3:
            phase_indicator = st.empty()
        
        # Video frame placeholder
        self.frame_placeholder = st.empty()
        
        # Control buttons
        col_start, col_stop = st.columns(2)
        with col_start:
            start_button = st.button("▶️ Start Exercise", use_container_width=True)
        with col_stop:
            stop_button = st.button("⏹️ Stop", use_container_width=True)
        
        if start_button:
            self._run_exercise_loop(rep_counter, form_score, phase_indicator)
    
    def _run_exercise_loop(self, rep_counter, form_score, phase_indicator):
        """Main exercise execution loop"""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            st.error("❌ Cannot access camera")
            return
        
        self.start_time = time.time()
        
        # Announce exercise start
        if hasattr(self.exercise, 'voice') and self.exercise.voice:
            exercise_name = self.exercise.__class__.__name__.replace('V2', '').replace('V1', '')
            # Convert CamelCase to Title Case
            import re
            exercise_name = re.sub(r'([A-Z])', r' \1', exercise_name).strip()
            self.exercise.voice.start_exercise(exercise_name, self.exercise.target_reps)
        
        # Session state for stop button
        if 'stop_exercise' not in st.session_state:
            st.session_state.stop_exercise = False
        
        while cap.isOpened() and not st.session_state.stop_exercise:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)
            
            # Pose detection
            results = self.analyzer.detect_pose(frame)
            
            if results.pose_landmarks:
                # Calculate angles
                angles = self.exercise.calculate_angles(
                    self.analyzer, results, frame.shape
                )
                
                # Validate form
                feedback = self.exercise.validate_form(
                    angles, self.exercise.phase
                )
                
                # Get primary angle for rep counting
                primary_angle = self._get_primary_angle(angles)
                
                # Update rep counter
                rep_done, phase, warnings = self.exercise.update_rep_counter(
                    primary_angle, feedback, self.voice
                )
                
                # Get joints for AR overlay
                joints = angles.get("joints_coords", {})
                
                # Calculate real-time form score
                current_form_score = self.exercise.calculate_real_time_form_score(
                    angles, joints
                )
                
                # Draw AR overlay based on mode
                if self.exercise.probation_mode:
                    # Practice mode - show target overlay
                    targets = self.exercise.get_target_poses().get(self.exercise.phase, {})
                    frame, position_matched = self.ar_system.draw_practice_mode(
                        frame, joints, angles, targets, current_form_score
                    )
                else:
                    # Counted mode - simple skeleton
                    frame = self.ar_system.draw_counted_mode(
                        frame, joints, current_form_score
                    )
                
                # Draw feedback
                self.highlighter.draw_feedback(frame, feedback, warnings)
                
                # Update UI
                rep_counter.metric(
                    "Reps Completed",
                    f"{self.exercise.rep_count}/{self.exercise.target_reps}"
                )
                form_score.metric("Form Score", f"{current_form_score:.1f}%")
                phase_indicator.metric("Phase", self.exercise.phase.replace('_', ' ').title())
                
                # Check if exercise complete
                if rep_done and self.exercise.rep_count >= self.exercise.target_reps:
                    break
            
            # Convert frame for Streamlit
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
        
        cap.release()
        
        # Show completion stats
        self._show_completion_stats()
    
    def _get_primary_angle(self, angles):
        """Extract primary angle from angles dict"""
        for key, value in angles.items():
            if isinstance(value, (int, float)) and key not in ['joints_coords']:
                return value
        return 0
    
    def _show_completion_stats(self):
        """Display exercise completion statistics"""
        stats = self.exercise.get_stats()
        
        st.success("🎉 Exercise Complete!")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Reps", stats['reps_completed'])
        with col2:
            st.metric("Avg Form Score", f"{stats['avg_form_score']:.1f}%")
        with col3:
            st.metric("Practice Reps", stats['practice_reps'])
        
        if stats['rejected_reps'] > 0:
            st.warning(f"⚠️ {stats['rejected_reps']} reps rejected due to form")
        
        # Form score chart
        if stats['form_scores']:
            st.line_chart(stats['form_scores'])
"""
Base class for all exercises - defines the interface
UPDATED: Added get_target_poses() for AR overlay system
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, List
import time


class BaseExercise(ABC):
    """
    Abstract base class for all exercises.
    Each exercise MUST implement these methods.
    """
    
    def __init__(self):
        self.phase = "standing"
        self.rep_count = 0
        self.practice_count = 0
        self.in_rep = False
        self.phase_start = time.time()
        self.rep_start_time = 0
        self.last_rep_time = 0
        self.reached_bottom = False
        self.probation_mode = True
        self.rejected_count = 0
        self.critical_errors_this_rep = 0
        self.frame_counter = 0
    
    @abstractmethod
    def get_config(self) -> Dict:
        """
        Return exercise configuration
        Must include: name, target_muscles, difficulty, youtube_url, 
                     instructions, tracking_joints
        """
        pass
    
    @abstractmethod
    def get_required_practice_reps(self) -> int:
        """Return number of practice reps required"""
        pass
    
    @abstractmethod
    def get_target_poses(self) -> Dict:
        """
        NEW METHOD: Define target angles for AR overlay system
        
        Returns:
            Dict with target angles for each exercise phase
            
        Example for dynamic exercise (squats):
            {
                'standing': {
                    'avg_knee': 170,
                    'back': 165,
                    'tolerance': 8
                },
                'bottom': {
                    'avg_knee': 140,
                    'back': 160,
                    'tolerance': 8
                }
            }
        
        Example for static exercise (stretches):
            {
                'holding': {
                    'back_knee': 170,
                    'front_knee': 140,
                    'tolerance': 8
                }
            }
        
        The 'tolerance' field is optional (defaults to 8 degrees)
        """
        pass
    
    @abstractmethod
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """
        Validate exercise form
        Args:
            angles: Dict with calculated angles (e.g., left_knee, right_knee, etc.)
            phase: Current phase of exercise
        Returns:
            Dict of JointFeedback objects
        """
        pass
    
    @abstractmethod
    def calculate_angles(self, analyzer, results, frame_shape) -> Dict:
        """
        Calculate all angles needed for this exercise
        Args:
            analyzer: PoseAnalyzer instance
            results: MediaPipe pose results
            frame_shape: Frame dimensions
        Returns:
            Dict with all calculated angles
        """
        pass
    
    @abstractmethod
    def update_rep_counter(self, primary_angle: float, feedback: Dict, voice_coach) -> Tuple[bool, str, List[str]]:
        """
        Update rep counting state machine
        Args:
            primary_angle: Main angle to track (e.g., average knee angle)
            feedback: Validation feedback
            voice_coach: VoiceCoach instance
        Returns:
            Tuple of (rep_done, phase, warnings)
        """
        pass
    
    @abstractmethod
    def get_joint_mapping(self, feedback: Dict, joints: Dict) -> Dict:
        """
        Map feedback to joint positions for visual display
        Args:
            feedback: Validation feedback
            joints: Dict of joint positions
        Returns:
            Dict mapping positions to FormStatus
        """
        pass
    
    def reset(self):
        """Reset exercise state"""
        self.phase = "standing"
        self.rep_count = 0
        self.practice_count = 0
        self.probation_mode = True
        self.rejected_count = 0
        self.critical_errors_this_rep = 0
        self.frame_counter = 0
    
    def get_status(self) -> str:
        """Get current status string"""
        if self.probation_mode:
            return f"PRACTICE: {self.practice_count}/{self.get_required_practice_reps()}"
        return f"REPS: {self.rep_count}"
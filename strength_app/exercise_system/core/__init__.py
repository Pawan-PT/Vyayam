"""
Core components - reusable across all exercises
UPDATED: Added V2 modules (voice_coach_v2, ar_overlay_v2, form_calculator, unilateral_handler)
"""

from .data_models import FormStatus, JointFeedback, ExerciseStats
from .pose_analyzer import PoseAnalyzer
from .visual_overlay import JointHighlighter

# V2 Core Modules (NEW)
from .voice_coach_v2 import VoiceCoachV2
from .ar_overlay_v2 import AROverlayV2
from .form_calculator import FormCalculator, StabilityDetector, TempoDetector
from .unilateral_handler import UnilateralExerciseHandler, Side

__all__ = [
    # Data Models
    'FormStatus',
    'JointFeedback',
    'ExerciseStats',
    
    # Analysis & Detection
    'PoseAnalyzer',
    
    # Visual Feedback (Original)
    'JointHighlighter',
    
    # V2 Enhanced Modules
    'VoiceCoachV2',            # voice_coach_v2 (atomic sentences, smooth transitions)
    'AROverlayV2',             # ar_overlay_v2 (Green/Yellow/Red in both modes)
    'FormCalculator',          # Real form scoring (angle + stability + tempo)
    'StabilityDetector',       # Part of form_calculator
    'TempoDetector',           # Part of form_calculator
    'UnilateralExerciseHandler',  # Manages left/right side tracking
    'Side',                    # Enum for Side.LEFT / Side.RIGHT
]
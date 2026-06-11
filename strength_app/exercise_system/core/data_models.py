"""
Data models used across the system - EXACT COPY from working code
"""

from dataclasses import dataclass
from enum import Enum


class FormStatus(Enum):
    CORRECT = "correct"
    NEEDS_ADJUSTMENT = "adjustment"
    INCORRECT = "incorrect"
    # Aliases (DA-EX-core): 63 modules reference FormStatus.WARNING and 13
    # FormStatus.GOOD — both crashed with AttributeError at runtime. Enum
    # aliasing keeps the value space unchanged for downstream comparisons.
    GOOD = "correct"
    WARNING = "adjustment"
    INFO = "correct"


@dataclass
class JointFeedback:
    status: FormStatus = None
    angle: float = 0.0
    message: str = ""
    joint: str = ""

    def __post_init__(self):
        # Convention shim (DA-EX-core): 38 modules construct with
        # joint=/status=/message= keywords (crashed: unexpected kwarg) and
        # 29 pass (joint_name, FormStatus, message) positionally (silently
        # put the joint STRING into .status, breaking AR color mapping).
        # Detect the joint-first positional form and reshuffle so .status
        # is always a FormStatus.
        if isinstance(self.status, str) and isinstance(self.angle, FormStatus):
            self.joint = self.status
            self.status = self.angle
            self.angle = 0.0


@dataclass
class ExerciseStats:
    reps_completed: int = 0
    target_reps: int = 10
    form_score: float = 100.0
    elapsed_time: float = 0.0
    current_phase: str = "standing"
    practice_reps: int = 0
    rejected_reps: int = 0

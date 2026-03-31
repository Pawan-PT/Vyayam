"""
VYAYAM STRENGTH TRAINING - DATABASE SCHEMA
Complete data structure for patient profiles, sessions, and reports
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS - System States
# ============================================================================

class PrescriptionMode(Enum):
    """Who controls the prescription"""
    AI_AUTO = "ai_auto"  # System prescribes and auto-progresses
    THERAPIST_MANUAL = "therapist_manual"  # Therapist prescribes, system tracks only


class CapabilityLevel(Enum):
    """Gate test result categories"""
    CANNOT_DO = "cannot_do"  # Can't perform exercise
    STRUGGLING = "struggling"  # Can do but with significant difficulty
    MANAGEABLE = "manageable"  # Can do with moderate effort
    EASY = "easy"  # Can do easily, ready for more


class FormQuality(Enum):
    """Rep quality classification"""
    GREEN = "green"  # Good form, counts toward total
    YELLOW = "yellow"  # Poor form, doesn't count
    RED = "red"  # Dangerous form, stop immediately


class ExerciseCategory(Enum):
    """Main exercise categories for gate testing"""
    LOWER_BODY = "lower_body"  # Squats
    POSTERIOR_CHAIN = "posterior_chain"  # Deadlifts
    UPPER_BODY = "upper_body"  # Rows
    CARDIO = "cardio"  # Endurance work
    STRETCHING = "stretching"  # Mobility/flexibility


# ============================================================================
# HEALTH PROFILE - The 8 Parameters + Patient Data
# ============================================================================

@dataclass
class PatientProfile:
    """
    Complete patient health profile with all 8 clusteral dimensions
    This is the foundation of personalized prescription
    """
    # Basic Information
    patient_id: str
    name: str
    phone: str
    password_hash: str  # Encrypted
    created_at: datetime = field(default_factory=datetime.now)
    
    # 8 CLUSTERAL DIMENSIONS
    # 1. Age
    age: int = 0
    
    # 2. Fitness Level (proven through gate tests)
    fitness_level: Dict[str, CapabilityLevel] = field(default_factory=dict)
    # Example: {'squat': CapabilityLevel.MANAGEABLE, 'deadlift': CapabilityLevel.STRUGGLING}
    
    # 3. Goals
    goals: str = ""  # "Build strength for daily activities"
    goal_type: str = ""  # "functional" / "athletic" / "rehabilitation"
    
    # 4. Biomechanics (inferred from activity)
    biomechanics: str = ""  # "desk_job_posture" / "athletic_overuse" / "sedentary_underuse"
    activity_pattern: str = ""  # "desk_job" / "manual_labor" / "athlete"
    
    # 5. Pain Tolerance (we call it "difficulty tolerance" for strength training)
    difficulty_tolerance: int = 5  # 1-10 scale, from gate test
    
    # 6. Lifestyle
    lifestyle: str = ""  # "sedentary" / "active" / "very_active"
    occupation: str = ""
    daily_sitting_hours: int = 0
    
    # 7. Compliance (proven through gate test completion)
    compliance_proven: bool = False  # Did they complete gate test?
    adherence_rate: float = 0.0  # % of prescribed sessions completed
    
    # 8. Timeline
    timeline: str = ""  # "no_rush" / "moderate" / "urgent"
    target_weeks: int = 12  # Default 12-week program
    
    # Medical History (for safety)
    medical_conditions: List[str] = field(default_factory=list)
    # Example: ["high_bp", "diabetes", "previous_knee_surgery"]
    
    contraindications: List[str] = field(default_factory=list)
    # Example: ["no_high_intensity", "no_jumping", "limited_rom"]
    
    # Prescription Mode
    prescription_mode: PrescriptionMode = PrescriptionMode.AI_AUTO
    assigned_therapist_id: Optional[str] = None
    
    # Current Status
    current_week: int = 0
    program_start_date: Optional[datetime] = None
    program_end_date: Optional[datetime] = None
    status: str = "active"  # "active" / "completed" / "paused"


# ============================================================================
# GATE TEST - Capability Assessment
# ============================================================================

@dataclass
class GateTestResult:
    """Results from a single gate test (per exercise category)"""
    patient_id: str
    category: ExerciseCategory
    test_exercise: str  # "partial_squat" / "bodyweight_deadlift" / etc.
    test_date: datetime = field(default_factory=datetime.now)
    
    # Performance Metrics
    reps_completed: int = 0  # How many they could do
    depth_achieved: float = 0.0  # Squat depth in degrees (30-90)
    difficulty_reported: int = 5  # 1-10 scale, how hard was it?
    pain_during: int = 0  # 0-10 scale (we track even though we call it "difficulty")
    
    # Determined Capability Level
    capability_level: CapabilityLevel = CapabilityLevel.MANAGEABLE
    
    # Prescription Determined
    starting_sets: int = 3
    starting_reps: int = 10
    starting_phase: str = "phase_1_standard"
    # Options: "phase_0" / "phase_1_low" / "phase_1_standard" / "phase_1_high"
    
    # Notes
    notes: str = ""
    went_to_practice_mode: bool = False  # Did they need practice reps?
    advancement_from_gate: int = 0  # How many levels they advanced during "too easy" flow


@dataclass
class GateTestSession:
    """Complete gate test session across all categories"""
    patient_id: str
    session_date: datetime = field(default_factory=datetime.now)
    tests_completed: List[GateTestResult] = field(default_factory=list)
    overall_fitness_level: str = "beginner"  # "beginner" / "intermediate" / "advanced"
    ready_for_prescription: bool = False


# ============================================================================
# EXERCISE SESSION - Daily Workout Tracking
# ============================================================================

@dataclass
class RepData:
    """Data for a single repetition"""
    rep_number: int
    form_score: float  # 0-100%
    form_quality: FormQuality  # GREEN / YELLOW / RED
    
    # Form Components (for detailed feedback)
    angle_accuracy: float = 0.0  # 0-1
    stability: float = 0.0  # 0-1
    tempo_control: float = 0.0  # 0-1
    
    # Voice guidance given
    feedback_given: List[str] = field(default_factory=list)
    # Example: ["Lower your hips more", "Keep your back straight"]


@dataclass
class SetData:
    """Data for a single set of an exercise"""
    set_number: int
    prescribed_reps: int
    reps_attempted: int
    reps_completed_green: int  # Only green reps count
    reps_yellow: int
    reps_red: int
    
    # Detailed rep data
    rep_data: List[RepData] = field(default_factory=list)
    
    # Set-level metrics
    average_form_score: float = 0.0
    set_completed: bool = False
    stopped_reason: Optional[str] = None  # "form_failure" / "fatigue" / "pain"


@dataclass
class ExerciseData:
    """Data for a single exercise in a workout"""
    exercise_id: str
    exercise_name: str
    category: ExerciseCategory
    
    # Prescription (what was prescribed)
    prescribed_sets: int
    prescribed_reps: int
    prescribed_hold_duration: float = 0.0  # seconds
    prescribed_rest: int = 60  # seconds
    
    # Execution (what actually happened)
    sets_completed: List[SetData] = field(default_factory=list)
    total_green_reps: int = 0
    total_yellow_reps: int = 0
    total_red_reps: int = 0
    
    # Exercise-level metrics
    overall_form_score: float = 0.0  # Mean across all reps
    completion_percentage: float = 0.0  # % of prescribed work completed
    
    # Practice Mode
    practice_mode_entered: bool = False
    practice_reps_done: int = 0
    went_back_one_level: bool = False  # Did they regress during exercise?


@dataclass
class WorkoutSession:
    """Complete daily workout session"""
    patient_id: str
    session_date: datetime = field(default_factory=datetime.now)
    week_number: int = 1
    
    # Workout Structure (in order)
    stretching_exercises: List[ExerciseData] = field(default_factory=list)
    strength_exercises: List[ExerciseData] = field(default_factory=list)
    cardio_exercises: List[ExerciseData] = field(default_factory=list)
    
    # Session-level metrics
    total_duration_minutes: int = 0
    total_exercises_completed: int = 0
    total_green_reps_all: int = 0
    overall_session_form_score: float = 0.0
    
    # Daily Feedback
    patient_comfortable: bool = True  # "Were you comfortable?"
    difficulty_rating: int = 3  # 1-5 scale
    patient_notes: str = ""
    
    # Prescription info
    prescription_mode: PrescriptionMode = PrescriptionMode.AI_AUTO
    prescribed_by_therapist_id: Optional[str] = None


# ============================================================================
# PROGRESSION TRACKING
# ============================================================================

@dataclass
class ExerciseProgressionState:
    """Track progression for a specific exercise"""
    patient_id: str
    exercise_category: ExerciseCategory
    current_exercise_id: str
    current_level: str  # "normal_squat" / "spanish_squat" / "decline_squat" / etc.
    
    # Current prescription
    current_sets: int = 3
    current_reps: int = 10
    
    # Progression tracking
    weeks_at_current_level: int = 0
    threshold_met: bool = False  # Has patient hit 15 reps × 3 sets?
    ready_to_advance: bool = False
    
    # Comfort tracking (for auto-adjustment)
    consecutive_uncomfortable_days: int = 0
    consecutive_comfortable_days: int = 0
    
    # Last progression/regression
    last_advancement_date: Optional[datetime] = None
    last_regression_date: Optional[datetime] = None
    
    # History
    progression_history: List[str] = field(default_factory=list)
    # Example: ["Week 1: normal_squat 10×3", "Week 2: spanish_squat 8×2"]


@dataclass
class WeeklyProgress:
    """Summary of a full week of training"""
    patient_id: str
    week_number: int
    start_date: datetime
    end_date: datetime
    
    # Sessions completed
    sessions_completed: int = 0
    sessions_prescribed: int = 7  # Daily program
    adherence_rate: float = 0.0
    
    # Performance metrics
    total_green_reps: int = 0
    average_form_score: float = 0.0
    exercises_progressed: List[str] = field(default_factory=list)
    exercises_regressed: List[str] = field(default_factory=list)
    
    # Exercise-specific data
    exercise_volumes: Dict[str, int] = field(default_factory=dict)
    # Example: {'squat': 150, 'deadlift': 120} (total reps)
    
    exercise_levels: Dict[str, str] = field(default_factory=dict)
    # Example: {'squat': 'spanish_squat', 'deadlift': 'conventional_deadlift'}


# ============================================================================
# PROFESSIONAL REPORT DATA
# ============================================================================

@dataclass
class ProgressReport:
    """Professional physiotherapy progress report"""
    patient_id: str
    report_date: datetime = field(default_factory=datetime.now)
    report_period: str = ""  # "Week 1-2" / "Weeks 1-4" / etc.
    
    # Patient Information
    patient_name: str = ""
    patient_age: int = 0
    program_start_date: datetime = None
    
    # Assessment Summary
    initial_fitness_levels: Dict[str, str] = field(default_factory=dict)
    current_fitness_levels: Dict[str, str] = field(default_factory=dict)
    
    # Intervention Details
    prescription_mode: str = ""  # "AI Auto-Prescription" / "Therapist Manual"
    prescribed_by: str = ""  # Therapist name or "AI System"
    reason_for_prescription: str = "Strength training program"
    
    # Week-by-Week Comparison
    weekly_summaries: List[WeeklyProgress] = field(default_factory=list)
    
    # Overall Outcomes
    total_sessions_completed: int = 0
    total_sessions_prescribed: int = 0
    overall_adherence_rate: float = 0.0
    
    # Exercise Progression
    exercises_advanced: List[Dict[str, str]] = field(default_factory=list)
    # Example: [{'exercise': 'Squat', 'from': 'Normal', 'to': 'Spanish', 'week': '2'}]
    
    exercises_current_levels: Dict[str, str] = field(default_factory=dict)
    
    # Performance Metrics
    total_green_reps_period: int = 0
    average_form_score_period: float = 0.0
    form_improvement: float = 0.0  # % improvement from start to end
    
    # Volume Analysis
    volume_by_exercise: Dict[str, List[int]] = field(default_factory=dict)
    # Example: {'squat': [90, 105, 120, 135]} (reps per week)
    
    # Clinical Notes
    therapist_notes: str = ""
    patient_feedback_summary: str = ""
    
    # Recommendations
    continue_current_program: bool = True
    recommended_next_steps: str = ""
    
    # Report metadata
    generated_by: str = "VYAYAM Strength Training System"
    report_version: str = "1.0"


# ============================================================================
# THERAPIST DATA (for Manual Mode)
# ============================================================================

@dataclass
class TherapistProfile:
    """Licensed therapist who can manually prescribe"""
    therapist_id: str
    name: str
    license_number: str
    specialization: str
    email: str
    phone: str
    
    # Patients assigned
    assigned_patients: List[str] = field(default_factory=list)
    
    # Dashboard preferences
    show_ai_suggestions: bool = True
    auto_generate_reports: bool = True


@dataclass
class TherapistPrescription:
    """Manual prescription by therapist"""
    prescription_id: str
    patient_id: str
    therapist_id: str
    created_date: datetime = field(default_factory=datetime.now)
    
    # Prescribed exercises
    exercises: List[Dict] = field(default_factory=list)
    # Example: [
    #   {'exercise_id': 'normal_squat', 'sets': 3, 'reps': 10, 'hold': 2, 'rest': 60},
    #   {'exercise_id': 'deadlift', 'sets': 2, 'reps': 8, 'hold': 0, 'rest': 90}
    # ]
    
    # Prescription details
    duration_weeks: int = 1
    frequency_per_week: int = 7  # Daily
    
    # Notes
    clinical_reasoning: str = ""
    special_instructions: str = ""
    
    # Status
    active: bool = True
    completed: bool = False


# ============================================================================
# SYSTEM STATE
# ============================================================================

@dataclass
class SystemState:
    """Current state of the entire system for a patient"""
    patient_id: str
    
    # Profile
    patient_profile: PatientProfile
    
    # Assessment
    latest_gate_test: Optional[GateTestSession] = None
    
    # Current prescription
    current_prescription_mode: PrescriptionMode = PrescriptionMode.AI_AUTO
    current_therapist_prescription: Optional[TherapistPrescription] = None
    
    # Active progression states
    exercise_progressions: Dict[str, ExerciseProgressionState] = field(default_factory=dict)
    # Key: exercise_category (e.g., 'squat'), Value: progression state
    
    # History
    all_sessions: List[WorkoutSession] = field(default_factory=list)
    all_weekly_progress: List[WeeklyProgress] = field(default_factory=list)
    all_reports: List[ProgressReport] = field(default_factory=list)
    
    # Current week
    current_week_number: int = 0
    current_week_sessions: List[WorkoutSession] = field(default_factory=list)


# ============================================================================
# EXAMPLE INSTANTIATION
# ============================================================================

if __name__ == "__main__":
    # Example: Create a new patient profile
    patient = PatientProfile(
        patient_id="P001",
        name="Rahul Sharma",
        phone="+91-9876543210",
        password_hash="hashed_password_here",
        age=35,
        goals="Build functional strength for daily activities",
        goal_type="functional",
        biomechanics="desk_job_posture",
        activity_pattern="desk_job",
        lifestyle="sedentary",
        occupation="Software Engineer",
        daily_sitting_hours=10,
        timeline="no_rush",
        target_weeks=12,
        medical_conditions=["high_bp"],
        contraindications=["no_high_intensity"],
        prescription_mode=PrescriptionMode.AI_AUTO
    )
    
    print(f"✅ Patient Profile Created: {patient.name}")
    print(f"   Age: {patient.age}, Goal: {patient.goals}")
    print(f"   Mode: {patient.prescription_mode.value}")

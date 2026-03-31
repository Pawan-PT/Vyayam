"""
MAIN SYSTEM COORDINATOR
Orchestrates all components for complete user journey
"""

from .database_schema import (
    PatientProfile, SystemState, ExerciseProgressionState,
    PrescriptionMode, ExerciseCategory, CapabilityLevel,
    TherapistPrescription, TherapistProfile
)
from .gate_test_system import GateTestEngine, GateTestCoordinator
from .prescription_engine import PrescriptionEngine
from .session_execution import SessionExecutor, DailyFeedbackLoop
from .report_generator import ReportGenerator
from typing import Dict, List
from datetime import datetime, timedelta


class VyayamStrengthSystem:
    """
    Main system coordinator
    Manages complete patient journey from onboarding to discharge
    """
    
    def __init__(self):
        # Initialize all subsystems
        self.gate_test_engine = GateTestEngine()
        self.gate_test_coordinator = GateTestCoordinator()
        self.prescription_engine = PrescriptionEngine()
        self.session_executor = SessionExecutor()
        self.feedback_loop = DailyFeedbackLoop()
        self.report_generator = ReportGenerator()
        
        # Patient database (in production: real database)
        self.patients: Dict[str, SystemState] = {}
        self.therapists: Dict[str, TherapistProfile] = {}
    
    
    def create_patient(
        self,
        name: str,
        phone: str,
        password: str,
        age: int,
        goals: str,
        occupation: str,
        lifestyle: str,
        medical_conditions: List[str] = None,
        prescription_mode: PrescriptionMode = PrescriptionMode.AI_AUTO,
        assigned_therapist_id: str = None
    ) -> str:
        """
        PHASE 0: Create new patient account
        """
        
        patient_id = f"P{len(self.patients) + 1:04d}"
        
        profile = PatientProfile(
            patient_id=patient_id,
            name=name,
            phone=phone,
            password_hash=f"hashed_{password}",  # In production: proper hashing
            age=age,
            goals=goals,
            occupation=occupation,
            lifestyle=lifestyle,
            medical_conditions=medical_conditions or [],
            prescription_mode=prescription_mode,
            assigned_therapist_id=assigned_therapist_id,
            program_start_date=datetime.now()
        )
        
        # Infer clusteral dimensions from provided info
        self._infer_clusteral_dimensions(profile)
        
        # Create system state
        system_state = SystemState(
            patient_id=patient_id,
            patient_profile=profile,
            current_prescription_mode=prescription_mode
        )
        
        self.patients[patient_id] = system_state
        
        print(f"✅ Patient created: {name} (ID: {patient_id})")
        return patient_id
    
    
    def _infer_clusteral_dimensions(self, profile: PatientProfile):
        """
        Fill in the 8 clusteral dimensions from basic info
        
        Parameters already filled: Age, Lifestyle, Goals
        Need to infer: Biomechanics, Timeline
        Will be filled later: Fitness, Pain Tolerance, Compliance
        """
        
        # Infer biomechanics from occupation
        if "desk" in profile.occupation.lower() or "software" in profile.occupation.lower():
            profile.biomechanics = "desk_job_posture"
            profile.activity_pattern = "desk_job"
            profile.daily_sitting_hours = 8
        elif "manual" in profile.occupation.lower() or "labor" in profile.occupation.lower():
            profile.biomechanics = "manual_labor_overuse"
            profile.activity_pattern = "manual_labor"
        elif "athlete" in profile.occupation.lower() or "sports" in profile.occupation.lower():
            profile.biomechanics = "athletic_overuse"
            profile.activity_pattern = "athlete"
        else:
            profile.biomechanics = "general_sedentary"
            profile.activity_pattern = "general"
        
        # Infer goal type
        if "sport" in profile.goals.lower() or "athlete" in profile.goals.lower():
            profile.goal_type = "athletic"
            profile.timeline = "moderate"
        elif "pain" in profile.goals.lower() or "rehab" in profile.goals.lower():
            profile.goal_type = "rehabilitation"
            profile.timeline = "no_rush"
        else:
            profile.goal_type = "functional"
            profile.timeline = "no_rush"
        
        # Set contraindications based on medical conditions
        for condition in profile.medical_conditions:
            if "bp" in condition.lower() or "blood pressure" in condition.lower():
                profile.contraindications.append("no_high_intensity")
            if "diabetes" in condition.lower():
                profile.contraindications.append("monitor_blood_sugar")
            if "knee" in condition.lower() or "joint" in condition.lower():
                profile.contraindications.append("limited_rom")
    
    
    def conduct_gate_testing(
        self,
        patient_id: str
    ) -> bool:
        """
        PHASE 1: Conduct gate tests across all categories
        Returns True if ready for prescription
        """
        
        if patient_id not in self.patients:
            print(f"❌ Patient {patient_id} not found")
            return False
        
        state = self.patients[patient_id]
        profile = state.patient_profile
        
        print(f"\n{'='*70}")
        print(f"GATE TESTING - {profile.name}")
        print(f"{'='*70}\n")
        
        # In real system: interactive UI
        # For now: simulate gate test results based on age/lifestyle
        
        test_results = []
        
        # 1. Lower Body (Squat) Gate Test
        print("1️⃣  LOWER BODY GATE TEST")
        squat_result = self._simulate_gate_test(
            patient_id=patient_id,
            category=ExerciseCategory.LOWER_BODY,
            test_exercise="partial_squat",
            profile=profile
        )
        test_results.append(squat_result)
        
        # 2. Posterior Chain (Deadlift) Gate Test
        print("\n2️⃣  POSTERIOR CHAIN GATE TEST")
        deadlift_result = self._simulate_gate_test(
            patient_id=patient_id,
            category=ExerciseCategory.POSTERIOR_CHAIN,
            test_exercise="hip_hinge",
            profile=profile
        )
        test_results.append(deadlift_result)
        
        # 3. Upper Body (Row) Gate Test
        print("\n3️⃣  UPPER BODY GATE TEST")
        row_result = self._simulate_gate_test(
            patient_id=patient_id,
            category=ExerciseCategory.UPPER_BODY,
            test_exercise="bent_over_row",
            profile=profile
        )
        test_results.append(row_result)
        
        # 4. Cardio Gate Test
        print("\n4️⃣  CARDIO ENDURANCE TEST")
        cardio_result = self._simulate_gate_test(
            patient_id=patient_id,
            category=ExerciseCategory.CARDIO,
            test_exercise="walking",
            profile=profile
        )
        test_results.append(cardio_result)
        
        # Create gate test session
        gate_session = self.gate_test_coordinator.create_gate_test_session(
            patient_id=patient_id,
            test_results=test_results
        )
        
        # Update patient fitness levels
        profile = self.gate_test_coordinator.update_patient_fitness_levels(
            patient=profile,
            gate_session=gate_session
        )
        
        state.patient_profile = profile
        state.latest_gate_test = gate_session
        
        print(f"\n✅ GATE TESTING COMPLETE")
        print(f"   Overall Fitness: {gate_session.overall_fitness_level.upper()}")
        print(f"   Ready for Prescription: {gate_session.ready_for_prescription}")
        
        return gate_session.ready_for_prescription
    
    
    def _simulate_gate_test(self, patient_id, category, test_exercise, profile):
        """Helper to simulate gate test based on patient characteristics"""
        
        # Adjust performance based on age and lifestyle
        if profile.age < 30 and profile.lifestyle == "active":
            reps = 12
            depth = 85.0
            difficulty = 2
        elif profile.age < 40 and profile.lifestyle == "sedentary":
            reps = 6
            depth = 50.0
            difficulty = 4
        elif profile.age >= 60:
            reps = 3
            depth = 35.0
            difficulty = 6
        else:
            reps = 8
            depth = 60.0
            difficulty = 3
        
        result = self.gate_test_engine.conduct_gate_test(
            patient_id=patient_id,
            category=category,
            test_exercise=test_exercise,
            reps_completed=reps,
            depth_achieved=depth,
            difficulty_reported=difficulty,
            pain_during=1
        )
        
        print(f"   {test_exercise}: {result.capability_level.value.upper()}")
        print(f"   → Prescription: {result.starting_sets}×{result.starting_reps}")
        
        return result
    
    
    def generate_prescription(
        self,
        patient_id: str,
        week_number: int = 1
    ) -> Dict:
        """
        PHASE 2: Generate exercise prescription
        Either AI auto or therapist manual
        """
        
        if patient_id not in self.patients:
            print(f"❌ Patient {patient_id} not found")
            return {}
        
        state = self.patients[patient_id]
        profile = state.patient_profile
        
        if state.current_prescription_mode == PrescriptionMode.AI_AUTO:
            # AI auto-prescription
            print(f"\n🤖 GENERATING AI AUTO-PRESCRIPTION (Week {week_number})")
            
            if not state.latest_gate_test:
                print("❌ No gate test results available")
                return {}
            
            prescription = self.prescription_engine.prescribe_ai_auto(
                patient=profile,
                gate_session=state.latest_gate_test,
                week_number=week_number
            )
            
        else:
            # Therapist manual prescription
            print(f"\n👨‍⚕️ USING THERAPIST MANUAL PRESCRIPTION (Week {week_number})")
            
            if not state.current_therapist_prescription:
                print("❌ No therapist prescription available")
                return {}
            
            prescription = self.prescription_engine.prescribe_therapist_manual(
                therapist_prescription=state.current_therapist_prescription
            )
        
        # Initialize progression states for tracking
        for ex in prescription.get('strength', []):
            if ex.get('progression_type'):
                exercise_id = ex['exercise_id']
                if exercise_id not in state.exercise_progressions:
                    state.exercise_progressions[exercise_id] = ExerciseProgressionState(
                        patient_id=patient_id,
                        exercise_category=ex['category'],
                        current_exercise_id=exercise_id,
                        current_level=ex['exercise_name'],
                        current_sets=ex['sets'],
                        current_reps=ex['reps']
                    )
        
        return prescription
    
    
    def execute_daily_session(
        self,
        patient_id: str,
        prescription: Dict
    ) -> bool:
        """
        PHASE 3: Execute daily workout session
        """
        
        if patient_id not in self.patients:
            return False
        
        state = self.patients[patient_id]
        profile = state.patient_profile
        
        # Execute session
        session = self.session_executor.execute_workout_session(
            patient_id=patient_id,
            week_number=profile.current_week,
            prescription=prescription,
            prescription_mode=state.current_prescription_mode
        )
        
        # Collect feedback
        feedback = self.feedback_loop.collect_daily_feedback(
            patient_id=patient_id,
            session=session
        )
        
        # Store session
        state.all_sessions.append(session)
        state.current_week_sessions.append(session)
        
        # Update adherence
        profile.adherence_rate = len(state.all_sessions) / (profile.current_week * 7) * 100
        
        return True
    
    
    def check_weekly_progression(
        self,
        patient_id: str
    ) -> Dict:
        """
        PHASE 4: Check if progression/regression needed at end of week
        """
        
        if patient_id not in self.patients:
            return {}
        
        state = self.patients[patient_id]
        
        # Get last session's feedback
        if not state.current_week_sessions:
            return {}
        
        latest_session = state.current_week_sessions[-1]
        latest_feedback = {
            'patient_comfortable': latest_session.patient_comfortable,
            'difficulty_rating': latest_session.difficulty_rating
        }
        
        # Check for auto-adjustments
        adjustments = self.feedback_loop.check_auto_adjustment_needed(
            patient_id=patient_id,
            progression_states=state.exercise_progressions,
            latest_feedback=latest_feedback
        )
        
        return adjustments
    
    
    def generate_weekly_report(
        self,
        patient_id: str,
        week_number: int
    ):
        """
        PHASE 5: Generate weekly progress report
        """
        
        if patient_id not in self.patients:
            return None
        
        state = self.patients[patient_id]
        
        # Generate report for all sessions up to this point
        report = self.report_generator.generate_progress_report(
            patient=state.patient_profile,
            all_sessions=state.all_sessions,
            report_period=f"Weeks 1-{week_number}"
        )
        
        # Store report
        state.all_reports.append(report)
        
        return report


# ============================================================================
# DEMO - Complete End-to-End Flow
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("VYAYAM STRENGTH TRAINING SYSTEM - COMPLETE DEMO")
    print("="*80)
    
    # Initialize system
    system = VyayamStrengthSystem()
    
    # PHASE 0: Create Patient
    print("\n📝 PHASE 0: PATIENT REGISTRATION")
    print("-"*80)
    
    patient_id = system.create_patient(
        name="Rahul Sharma",
        phone="+91-9876543210",
        password="secure_password",
        age=35,
        goals="Build functional strength for daily activities",
        occupation="Software Engineer",
        lifestyle="sedentary",
        medical_conditions=["high_bp"],
        prescription_mode=PrescriptionMode.AI_AUTO
    )
    
    # PHASE 1: Gate Testing
    print("\n📊 PHASE 1: GATE TESTING")
    print("-"*80)
    
    ready = system.conduct_gate_testing(patient_id)
    
    if not ready:
        print("❌ Gate testing incomplete")
        exit()
    
    # PHASE 2: Generate Prescription
    print("\n📋 PHASE 2: PRESCRIPTION GENERATION")
    print("-"*80)
    
    prescription = system.generate_prescription(patient_id, week_number=1)
    
    print("\nPrescription Summary:")
    print(f"  Stretching: {len(prescription['stretching'])} exercises")
    print(f"  Strength: {len(prescription['strength'])} exercises")
    print(f"  Cardio: {len(prescription['cardio'])} exercises")
    
    # PHASE 3: Execute Sessions (Week 1)
    print("\n\n🏋️ PHASE 3: WEEK 1 EXECUTION")
    print("-"*80)
    
    print("\nSimulating 5 sessions in Week 1...")
    
    for day in range(1, 6):
        print(f"\n--- DAY {day} ---")
        system.execute_daily_session(patient_id, prescription)
    
    # PHASE 4: Weekly Check & Progression
    print("\n\n📈 PHASE 4: WEEKLY PROGRESSION CHECK")
    print("-"*80)
    
    adjustments = system.check_weekly_progression(patient_id)
    
    if adjustments:
        print("\nAdjustments needed:")
        for exercise, action in adjustments.items():
            print(f"  • {exercise}: {action}")
    else:
        print("✅ No adjustments needed, continue current program")
    
    # PHASE 5: Generate Report
    print("\n\n📄 PHASE 5: PROGRESS REPORT GENERATION")
    print("-"*80)
    
    report = system.generate_weekly_report(patient_id, week_number=1)
    
    if report:
        report_text = system.report_generator.format_report_text(report)
        print("\n" + report_text)
    
    print("\n\n" + "="*80)
    print("✅ COMPLETE SYSTEM DEMO FINISHED!")
    print("="*80)
    print("\nAll components working:")
    print("  ✅ Patient registration")
    print("  ✅ Gate testing")
    print("  ✅ AI prescription")
    print("  ✅ Session execution")
    print("  ✅ Form tracking")
    print("  ✅ Daily feedback")
    print("  ✅ Weekly progression")
    print("  ✅ Report generation")
    print("\n🎉 System ready for integration with exercise library!")

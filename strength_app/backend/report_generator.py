"""
PROFESSIONAL PHYSIOTHERAPY REPORT GENERATOR
Generates comprehensive progress reports with all clinical data
"""

from .database_schema import (
    ProgressReport, WeeklyProgress, WorkoutSession,
    PatientProfile, PrescriptionMode
)
from typing import List, Dict
from datetime import datetime, timedelta


class ReportGenerator:
    """
    Generates professional physiotherapy reports
    Contains all data a professional physio report should have
    """
    
    def generate_weekly_summary(
        self,
        patient_id: str,
        week_number: int,
        sessions: List[WorkoutSession]
    ) -> WeeklyProgress:
        """
        Create a weekly summary from session data
        """
        
        if not sessions:
            # No sessions this week
            return WeeklyProgress(
                patient_id=patient_id,
                week_number=week_number,
                start_date=datetime.now(),
                end_date=datetime.now(),
                sessions_completed=0,
                sessions_prescribed=7,
                adherence_rate=0.0
            )
        
        weekly = WeeklyProgress(
            patient_id=patient_id,
            week_number=week_number,
            start_date=sessions[0].session_date,
            end_date=sessions[-1].session_date,
            sessions_completed=len(sessions),
            sessions_prescribed=7  # Daily program
        )
        
        # Calculate adherence
        weekly.adherence_rate = (weekly.sessions_completed / weekly.sessions_prescribed) * 100
        
        # Aggregate performance metrics
        total_green_reps = 0
        total_form_scores = []
        
        for session in sessions:
            total_green_reps += session.total_green_reps_all
            if session.overall_session_form_score > 0:
                total_form_scores.append(session.overall_session_form_score)
        
        weekly.total_green_reps = total_green_reps
        
        if total_form_scores:
            weekly.average_form_score = sum(total_form_scores) / len(total_form_scores)
        
        # Track exercise volumes and levels
        exercise_volumes = {}
        exercise_levels = {}
        
        for session in sessions:
            all_exercises = session.strength_exercises + session.cardio_exercises
            
            for ex in all_exercises:
                # Accumulate volume
                if ex.exercise_id not in exercise_volumes:
                    exercise_volumes[ex.exercise_id] = 0
                exercise_volumes[ex.exercise_id] += ex.total_green_reps
                
                # Track current level
                exercise_levels[ex.exercise_id] = ex.exercise_name
        
        weekly.exercise_volumes = exercise_volumes
        weekly.exercise_levels = exercise_levels
        
        return weekly
    
    
    def compare_weeks(
        self,
        week1: WeeklyProgress,
        week2: WeeklyProgress
    ) -> Dict:
        """
        Compare two weeks and identify progressions/regressions
        """
        
        comparison = {
            'adherence_change': week2.adherence_rate - week1.adherence_rate,
            'form_improvement': week2.average_form_score - week1.average_form_score,
            'volume_changes': {},
            'exercise_changes': []
        }
        
        # Volume changes
        for exercise_id in week2.exercise_volumes:
            vol_week1 = week1.exercise_volumes.get(exercise_id, 0)
            vol_week2 = week2.exercise_volumes[exercise_id]
            
            if vol_week1 > 0:
                change_pct = ((vol_week2 - vol_week1) / vol_week1) * 100
                comparison['volume_changes'][exercise_id] = change_pct
        
        # Exercise level changes (progressions/regressions)
        for exercise_id in week2.exercise_levels:
            level_week1 = week1.exercise_levels.get(exercise_id, "")
            level_week2 = week2.exercise_levels[exercise_id]
            
            if level_week1 and level_week1 != level_week2:
                # Exercise changed!
                # Determine if progression or regression based on naming
                # (In real system, track index in progression ladder)
                comparison['exercise_changes'].append({
                    'exercise_id': exercise_id,
                    'from': level_week1,
                    'to': level_week2,
                    'type': 'progression'  # Simplified - would check actual progression
                })
        
        return comparison
    
    
    def generate_progress_report(
        self,
        patient: PatientProfile,
        all_sessions: List[WorkoutSession],
        report_period: str = "Week 1-4"
    ) -> ProgressReport:
        """
        Generate comprehensive professional report
        """
        
        report = ProgressReport(
            patient_id=patient.patient_id,
            report_date=datetime.now(),
            report_period=report_period,
            patient_name=patient.name,
            patient_age=patient.age,
            program_start_date=patient.program_start_date
        )
        
        # Prescription details
        if patient.prescription_mode == PrescriptionMode.AI_AUTO:
            report.prescription_mode = "AI Auto-Prescription"
            report.prescribed_by = "VYAYAM AI System"
        else:
            report.prescription_mode = "Therapist Manual Prescription"
            report.prescribed_by = f"Therapist ID: {patient.assigned_therapist_id}"
        
        # Initial vs current fitness levels
        report.initial_fitness_levels = {
            category: level.value
            for category, level in patient.fitness_level.items()
        }
        
        # Group sessions by week
        weeks = {}
        for session in all_sessions:
            week_num = session.week_number
            if week_num not in weeks:
                weeks[week_num] = []
            weeks[week_num].append(session)
        
        # Generate weekly summaries
        for week_num in sorted(weeks.keys()):
            weekly = self.generate_weekly_summary(
                patient.patient_id,
                week_num,
                weeks[week_num]
            )
            report.weekly_summaries.append(weekly)
        
        # Calculate overall metrics
        report.total_sessions_completed = len(all_sessions)
        report.total_sessions_prescribed = len(report.weekly_summaries) * 7
        
        if report.total_sessions_prescribed > 0:
            report.overall_adherence_rate = (report.total_sessions_completed / report.total_sessions_prescribed) * 100
        
        # Total green reps
        report.total_green_reps_period = sum(s.total_green_reps_all for s in all_sessions)
        
        # Average form score
        form_scores = [s.overall_session_form_score for s in all_sessions if s.overall_session_form_score > 0]
        if form_scores:
            report.average_form_score_period = sum(form_scores) / len(form_scores)
            
            # Form improvement (first week vs last week)
            if len(report.weekly_summaries) >= 2:
                first_week_form = report.weekly_summaries[0].average_form_score
                last_week_form = report.weekly_summaries[-1].average_form_score
                if first_week_form > 0:
                    report.form_improvement = ((last_week_form - first_week_form) / first_week_form) * 100
        
        # Track exercise progressions
        if len(report.weekly_summaries) >= 2:
            for i in range(len(report.weekly_summaries) - 1):
                comparison = self.compare_weeks(
                    report.weekly_summaries[i],
                    report.weekly_summaries[i + 1]
                )
                
                for change in comparison['exercise_changes']:
                    report.exercises_advanced.append({
                        'exercise': change['exercise_id'],
                        'from': change['from'],
                        'to': change['to'],
                        'week': str(i + 2)  # Week number where advancement happened
                    })
        
        # Current exercise levels
        if report.weekly_summaries:
            report.exercises_current_levels = report.weekly_summaries[-1].exercise_levels
        
        # Volume by exercise over time
        for weekly in report.weekly_summaries:
            for exercise_id, volume in weekly.exercise_volumes.items():
                if exercise_id not in report.volume_by_exercise:
                    report.volume_by_exercise[exercise_id] = []
                report.volume_by_exercise[exercise_id].append(volume)
        
        return report
    
    
    def format_report_text(
        self,
        report: ProgressReport,
        include_clinical_notes: bool = True
    ) -> str:
        """
        Format report as professional text document
        """
        
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("VYAYAM STRENGTH TRAINING - PROGRESS REPORT")
        lines.append("=" * 80)
        lines.append(f"Report Date: {report.report_date.strftime('%B %d, %Y')}")
        lines.append(f"Report Period: {report.report_period}")
        lines.append(f"Generated by: {report.generated_by} (v{report.report_version})")
        lines.append("")
        
        # Patient Information
        lines.append("PATIENT INFORMATION")
        lines.append("-" * 80)
        lines.append(f"Name: {report.patient_name}")
        lines.append(f"Age: {report.patient_age} years")
        lines.append(f"Patient ID: {report.patient_id}")
        if report.program_start_date:
            lines.append(f"Program Start: {report.program_start_date.strftime('%B %d, %Y')}")
        lines.append("")
        
        # Intervention Details
        lines.append("INTERVENTION DETAILS")
        lines.append("-" * 80)
        lines.append(f"Prescription Mode: {report.prescription_mode}")
        lines.append(f"Prescribed By: {report.prescribed_by}")
        lines.append(f"Reason for Prescription: {report.reason_for_prescription}")
        lines.append("")
        
        # Assessment Summary
        lines.append("INITIAL ASSESSMENT")
        lines.append("-" * 80)
        for category, level in report.initial_fitness_levels.items():
            lines.append(f"  • {category.replace('_', ' ').title()}: {level.upper()}")
        lines.append("")
        
        # Overall Outcomes
        lines.append("OVERALL OUTCOMES")
        lines.append("-" * 80)
        lines.append(f"Sessions Completed: {report.total_sessions_completed}/{report.total_sessions_prescribed}")
        lines.append(f"Overall Adherence: {report.overall_adherence_rate:.1f}%")
        lines.append(f"Total Green Reps: {report.total_green_reps_period}")
        lines.append(f"Average Form Score: {report.average_form_score_period:.1f}%")
        if report.form_improvement != 0:
            lines.append(f"Form Improvement: {report.form_improvement:+.1f}%")
        lines.append("")
        
        # Week-by-Week Breakdown
        lines.append("WEEK-BY-WEEK PROGRESS")
        lines.append("-" * 80)
        
        for weekly in report.weekly_summaries:
            lines.append(f"\nWeek {weekly.week_number}:")
            lines.append(f"  Sessions: {weekly.sessions_completed}/{weekly.sessions_prescribed} ({weekly.adherence_rate:.0f}% adherence)")
            lines.append(f"  Total Reps: {weekly.total_green_reps}")
            lines.append(f"  Form Score: {weekly.average_form_score:.1f}%")
            
            if weekly.exercises_progressed:
                lines.append(f"  ✅ Progressed: {', '.join(weekly.exercises_progressed)}")
            if weekly.exercises_regressed:
                lines.append(f"  ⬅️  Regressed: {', '.join(weekly.exercises_regressed)}")
        
        lines.append("")
        
        # Exercise Progression
        if report.exercises_advanced:
            lines.append("EXERCISE PROGRESSIONS")
            lines.append("-" * 80)
            for advancement in report.exercises_advanced:
                lines.append(f"Week {advancement['week']}: {advancement['exercise']}")
                lines.append(f"  From: {advancement['from']}")
                lines.append(f"  To:   {advancement['to']}")
            lines.append("")
        
        # Current Exercise Levels
        lines.append("CURRENT EXERCISE LEVELS")
        lines.append("-" * 80)
        for exercise_id, exercise_name in report.exercises_current_levels.items():
            lines.append(f"  • {exercise_name}")
        lines.append("")
        
        # Volume Analysis
        if report.volume_by_exercise:
            lines.append("VOLUME PROGRESSION (Reps per Week)")
            lines.append("-" * 80)
            for exercise_id, volumes in report.volume_by_exercise.items():
                volume_str = " → ".join(str(v) for v in volumes)
                lines.append(f"  {exercise_id}: {volume_str}")
            lines.append("")
        
        # Clinical Notes
        if include_clinical_notes and report.therapist_notes:
            lines.append("THERAPIST CLINICAL NOTES")
            lines.append("-" * 80)
            lines.append(report.therapist_notes)
            lines.append("")
        
        # Patient Feedback Summary
        if report.patient_feedback_summary:
            lines.append("PATIENT FEEDBACK SUMMARY")
            lines.append("-" * 80)
            lines.append(report.patient_feedback_summary)
            lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        if report.continue_current_program:
            lines.append("✅ Continue current program")
        else:
            lines.append("⚠️  Program adjustment recommended")
        
        if report.recommended_next_steps:
            lines.append(f"\nNext Steps: {report.recommended_next_steps}")
        lines.append("")
        
        # Footer
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("REPORT GENERATOR - DEMO")
    print("=" * 80)
    
    # Create mock patient
    patient = PatientProfile(
        patient_id="P001",
        name="Rahul Sharma",
        phone="+91-9876543210",
        password_hash="hashed",
        age=35,
        goals="Build functional strength for daily activities",
        goal_type="functional",
        lifestyle="sedentary",
        occupation="Software Engineer",
        prescription_mode=PrescriptionMode.AI_AUTO,
        program_start_date=datetime.now() - timedelta(weeks=4)
    )
    
    patient.fitness_level = {
        'lower_body': 'manageable',
        'posterior_chain': 'struggling',
        'upper_body': 'manageable'
    }
    
    # Mock sessions (4 weeks)
    sessions = []
    
    for week in range(1, 5):
        for day in range(5):  # 5 sessions per week
            session = WorkoutSession(
                patient_id="P001",
                session_date=datetime.now() - timedelta(weeks=4-week, days=day),
                week_number=week,
                total_duration_minutes=35 + week * 2,  # Gradually increasing
                total_exercises_completed=8,
                total_green_reps_all=80 + week * 10,  # Improving volume
                overall_session_form_score=75 + week * 3,  # Improving form
                patient_comfortable=True,
                difficulty_rating=3
            )
            sessions.append(session)
    
    # Generate report
    generator = ReportGenerator()
    
    report = generator.generate_progress_report(
        patient=patient,
        all_sessions=sessions,
        report_period="Weeks 1-4"
    )
    
    # Add some clinical notes
    report.therapist_notes = """
Patient has shown excellent adherence and consistent improvement in both 
volume and form quality over the 4-week period. Started with manageable 
capability in lower body and upper body work, struggling with posterior 
chain. Progressive overload protocol has been well-tolerated.

Notable improvements:
- Form score increased from 75% to 87% (+16% improvement)
- Total weekly volume increased from ~400 reps to ~520 reps (+30%)
- Patient reports improved functional capacity in daily activities

Recommend continuing current progression for 4 more weeks before 
reassessment. Patient appears ready for Phase 2 exercises in lower body.
"""
    
    report.patient_feedback_summary = """
Patient consistently reported feeling comfortable with prescribed exercises.
Progression was well-tolerated with no adverse events or regression periods.
Patient expressed satisfaction with program structure and visual form feedback.
"""
    
    report.continue_current_program = True
    report.recommended_next_steps = "Advance to Phase 2 lower body exercises (Week 5)"
    
    # Format and print report
    report_text = generator.format_report_text(report)
    
    print("\n\n")
    print(report_text)
    
    print("\n\n✅ Report Generator Ready!")
    print("📄 Report can be saved as PDF/DOCX and stored in patient health profile")

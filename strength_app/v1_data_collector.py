"""
VYAYAM V2 Data Foundation — Anonymised Session Logger

Logs anonymised session data after each completed session IF the patient
has given consent (patient.data_consent == True).

Data collected is fully anonymised (no names, IDs, or personal details).
Used to train the V2 Bayesian prescription engine.
"""

from .v1_constants import get_age_bracket


def _anonymise_exercises(working_sets):
    """Strip personal context, keep only movement pattern + dosage data."""
    result = []
    for ex in (working_sets or []):
        result.append({
            'movement_pattern': ex.get('movement_pattern', ''),
            'sets': ex.get('sets', 0),
            'reps': ex.get('reps', 0),
            'tempo': ex.get('tempo', ''),
            'rest_seconds': ex.get('rest_seconds', 0),
        })
    return result


def log_session_data(patient, session_data, feedback):
    """
    Log anonymised session data for V2 Bayesian engine training.
    Only logs if patient.data_consent is True.

    Args:
        patient: PatientProfile instance
        session_data: dict returned by generate_v1_session
        feedback: SessionFeedback instance or None
    """
    if not getattr(patient, 'data_consent', False):
        return

    try:
        from .models import AnonymisedSessionLog
        AnonymisedSessionLog.objects.create(
            age_bracket=get_age_bracket(patient.age or 25),
            biological_sex=patient.biological_sex or '',
            goal_type=patient.goal_type or '',
            training_history=patient.training_history or '',
            session_phase=session_data.get('meta', {}).get('periodisation_phase', ''),
            exercises_json=_anonymise_exercises(session_data.get('working_sets', [])),
            feedback_difficulty=getattr(feedback, 'perceived_difficulty', '') or '',
            feedback_pain=getattr(feedback, 'pain_reported', '') or '',
            feedback_pain_location=getattr(feedback, 'pain_location', '') or '',
            traffic_light=getattr(feedback, 'traffic_light', '') or '',
        )
    except Exception:
        pass  # Data collection must never break the main flow

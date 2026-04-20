"""
VYAYAM V1 — Red Flag → Exercise Exclusion → Alternative Map
Every condition maps to specific exercises that are excluded and specific safe alternatives.
"""

RED_FLAG_EXERCISE_MAP = {

    'acl_grade_1_2': {
        'exclude_exercises': [
            'jump_squats', 'depth_jump', 'lateral_bound', 'single_leg_landing',
            'change_of_direction', 'plyometric_lunge', 'tuck_jumps', 'box_jumps',
            'skaters', 'lateral_hops', 'lateral_Hops', 'side_to_side_hops',
        ],
        'exclude_patterns_above_level': {'lunge': 3},  # No lunge exercises above level 3
        'replace_with': {
            'lower_power': 'single_leg_squat_to_box',
            'lunge_advanced': 'reverse_lunges',
        },
        'unlock_criteria': 'acl_programme_week_4',
        'notes': 'No high-impact plyometrics. No sudden change of direction.',
    },

    'knee_pain_patellofemoral': {
        'exclude_exercises': [
            'full_squats', 'jump_squats', 'lunges', 'step_ups',
            'decline_squats', 'pistol_squat', 'depth_jump',
        ],
        'replace_with': {
            'squat': 'terminal_knee_extension',
            'lunge': 'reverse_lunges',
            'step': 'step_ups',  # Low box only
        },
        'notes': 'Avoid deep knee flexion > 90 degrees under load.',
    },

    'hernia': {
        'exclude_exercises': [
            'burpees', 'tuck_jumps', 'mountain_climbers', 'russian_twist_bw',
            'hanging_leg_raise', 'dragon_flag_progression', 'hollow_body_hold',
            'hollow_body_rock', 'jump_squats', 'depth_jump',
        ],
        'exclude_categories': ['power'],  # No explosive loading
        'replace_with': {
            'core': 'dead_bug',
            'core_lateral': 'pallof_press_isometric',
            'hinge': 'glute_bridge',
        },
        'notes': 'NO intra-abdominal pressure increase. No Valsalva. No loaded rotation.',
    },

    'lower_back_disc': {
        'exclude_exercises': [
            'good_morning', 'deadlift_dumbbell', 'russian_twist_bw',
            'band_woodchop', 'rotational_swings', 'hanging_leg_raise',
            'straight_leg_raises',
        ],
        'replace_with': {
            'hinge': 'glute_bridge',
            'core': 'bird_dog',
            'extension': 'prone_hip_extension',
        },
        'notes': 'No loaded spinal flexion. No loaded rotation. Extension-based core only.',
    },

    'shoulder_impingement': {
        'exclude_exercises': [
            'pike_push_up', 'pike_push_up_elevated', 'wall_handstand_push_up',
            'handstand_wall_hold', 'wide_grip_push_up', 'shoulder_stretch',
        ],
        'replace_with': {
            'push_vertical': 'wall_push_up',
            'pull_vertical': 'dumbbell_rowing',
        },
        'notes': 'No overhead pressing. No wide grip pull. Neutral grip only.',
    },

    'rotator_cuff_partial': {
        'exclude_exercises': [
            'pike_push_up', 'pike_push_up_elevated', 'wall_handstand_push_up',
            'handstand_wall_hold', 'archer_pull_up', 'l_sit_pull_up',
            'muscle_up_progression', 'ring_push_up',
        ],
        'replace_with': {
            'shoulder_stability': 'prone_y_t_w',
            'push': 'wall_push_up',
        },
        'notes': 'No loading above 90 degrees shoulder flexion.',
    },

    'osteoporosis': {
        'exclude_exercises': [
            'jump_squats', 'depth_jump', 'tuck_jumps', 'box_jumps',
            'plyometric_lunge', 'lateral_bound', 'burpees',
        ],
        'replace_with': {
            'power': 'farmer_carry',
            'impact': 'marching_on_spot',
        },
        'notes': 'Weight bearing IS good. Only remove high impact. Maintain loaded exercises.',
    },

    'hypertension': {
        'exclude_exercises': [],  # No specific exercises excluded
        'modifications': {
            'avoid_prolonged_isometric': True,  # Reduce hold durations
            'max_hold_seconds': 20,
            'avoid_valsalva': True,
            'max_intensity_percent': 80,
        },
        'notes': 'Exercise IS recommended. Modify intensity only. Avoid breath holding.',
    },

    'ankle_sprain_acute': {
        'exclude_exercises': [
            'jump_squats', 'lateral_hops', 'lateral_Hops', 'side_to_side_hops',
            'skaters', 'lateral_bound', 'change_of_direction', 'plyometric_lunge',
            'single_leg_balance', 'tandem_walking', 'lateral_lunges',
        ],
        'replace_with': {
            'balance': 'double_leg_balance',
            'lunge': 'split_squat_static',
        },
        'notes': 'No lateral movement. No single leg impact. Seated or supine alternatives.',
    },

    'wrist_pain': {
        'exclude_exercises': [
            'push_ups', 'wide_grip_push_up', 'close_grip_push_up',
            'decline_push_up', 'archer_push_up', 'pike_push_up',
            'pseudo_planche_push_up', 'handstand_wall_hold',
            'bear_crawl', 'crab_walk', 'mountain_climbers',
        ],
        'replace_with': {
            'push': 'wall_push_up',  # Reduced wrist extension demand
        },
        'notes': 'Fist push-ups or push-up handles recommended if continuing push pattern.',
    },

    'elbow_tendinopathy': {
        'exclude_exercises': [
            'chin_up', 'bicep_curls', 'archer_pull_up',
            'close_grip_push_up', 'tricep_extensions',
        ],
        'replace_with': {
            'pull': 'dumbbell_rowing',
            'push': 'push_ups',
        },
        'notes': 'Isometric holds initially. No full range elbow exercises until pain-free.',
    },
}


def get_excluded_exercises(red_flags_list):
    """Given a list of red flag IDs, return the complete set of excluded exercise IDs."""
    excluded = set()
    for flag_id in red_flags_list:
        flag_config = RED_FLAG_EXERCISE_MAP.get(flag_id, {})
        excluded.update(flag_config.get('exclude_exercises', []))
    return excluded


def get_alternative(red_flag_id, pattern):
    """Get the replacement exercise for a given red flag and movement pattern."""
    flag_config = RED_FLAG_EXERCISE_MAP.get(red_flag_id, {})
    replacements = flag_config.get('replace_with', {})
    return replacements.get(pattern, None)


def get_pattern_level_caps(red_flags_list):
    """
    Return the most restrictive level cap per pattern across all active red flags.

    Returns:
        dict[str, int] — e.g. {'lunge': 3} meaning lunge exercises must not exceed level 3.
    """
    caps = {}
    for flag_id in red_flags_list:
        flag_config = RED_FLAG_EXERCISE_MAP.get(flag_id, {})
        for pattern, max_level in flag_config.get('exclude_patterns_above_level', {}).items():
            if pattern not in caps or max_level < caps[pattern]:
                caps[pattern] = max_level
    return caps

"""
VYAYAM V1 — 7 Movement Pattern Progression Chains
Each pattern has 5 capability levels with exercises appropriate for each.
Exercises marked with # NEW will be added in Sprints 3-5.
"""

V1_PROGRESSION_CHAINS = {

    'squat': {
        'name': 'Squat Pattern',
        'description': 'Bilateral knee-dominant lower body strength',
        'icon': '🦵',
        'levels': [
            # Level 1 — Entry/Cannot do full squat
            {'level': 1, 'exercises': [
                'sit_to_stand',        # Existing
                'wall_sit',            # NEW Sprint 3
                'box_squat',           # NEW Sprint 3
            ]},
            # Level 2 — Building
            {'level': 2, 'exercises': [
                'partial_squats',      # Existing
                'goblet_squat',        # NEW Sprint 3
                'sumo_squat',          # NEW Sprint 3
            ]},
            # Level 3 — Intermediate
            {'level': 3, 'exercises': [
                'full_squats',              # Existing
                'pause_squat',             # NEW Sprint 3
                'heel_elevated_squat',     # NEW Sprint 3
                'mini_squats_with_band',   # Existing
            ]},
            # Level 4 — Advanced
            {'level': 4, 'exercises': [
                'bulgarian_split_squats',  # Existing
                'decline_squats',          # Existing
                'spanish_squat',           # Existing
                'single_leg_squat_to_box', # NEW Sprint 3
            ]},
            # Level 5 — Athletic/Power
            {'level': 5, 'exercises': [
                'jump_squats',             # Existing
                'single_leg_squats',       # Existing
                'pistol_squat',            # NEW Sprint 3
                'depth_jump',              # NEW Sprint 3
            ]},
        ],
    },

    'hinge': {
        'name': 'Hinge Pattern',
        'description': 'Hip-dominant posterior chain strength',
        'icon': '🍑',
        'levels': [
            {'level': 1, 'exercises': [
                'glute_bridge',            # Existing
                'hip_hinge_wall',          # NEW Sprint 3
                'prone_hip_extension',     # NEW Sprint 3
            ]},
            {'level': 2, 'exercises': [
                'single_leg_glute_bridge', # Existing
                'bodyweight_rdl',          # NEW Sprint 3
                'good_morning',            # NEW Sprint 3
            ]},
            {'level': 3, 'exercises': [
                'single_leg_rdl',          # Existing
                'nordic_hamstring_curl',   # NEW Sprint 3
                'hip_thrust_bodyweight',   # NEW Sprint 3
            ]},
            {'level': 4, 'exercises': [
                'nordic_curl_partner',     # NEW Sprint 3
                'single_leg_hip_thrust',   # NEW Sprint 3
                'sliding_leg_curl',        # NEW Sprint 3
                'deadlift_dumbbell',       # Existing
            ]},
            {'level': 5, 'exercises': [
                'banded_rdl',              # NEW Sprint 3
                'nordic_curl_weighted',    # NEW Sprint 3
                'single_leg_slider_curl',  # NEW Sprint 3
            ]},
        ],
    },

    'lunge': {
        'name': 'Lunge Pattern',
        'description': 'Unilateral lower body strength and stability',
        'icon': '🏃',
        'levels': [
            {'level': 1, 'exercises': [
                'split_squat_static',      # NEW Sprint 3
                'reverse_lunges',          # Existing
                'step_ups',                # Existing
            ]},
            {'level': 2, 'exercises': [
                'lunges',                  # Existing (forward lunge)
                'lateral_lunges',          # Existing
                'curtsy_lunge',            # NEW Sprint 3
            ]},
            {'level': 3, 'exercises': [
                'walking_lunge',           # NEW Sprint 3
                'deficit_reverse_lunge',   # NEW Sprint 3
                'side_step_ups',           # Existing
            ]},
            {'level': 4, 'exercises': [
                'bulgarian_split_squats',  # Existing (also in squat L4)
                'single_leg_squat_to_box', # NEW Sprint 3
                'plyometric_lunge',        # NEW Sprint 3
            ]},
            {'level': 5, 'exercises': [
                'single_leg_landing',      # NEW Sprint 3
                'lateral_bound',           # NEW Sprint 3
                'change_of_direction',     # NEW Sprint 3
            ]},
        ],
    },

    'push': {
        'name': 'Push Pattern',
        'description': 'Upper body pushing — horizontal and vertical',
        'icon': '💪',
        'levels': [
            {'level': 1, 'exercises': [
                'wall_push_up',            # NEW Sprint 4
                'incline_push_up',         # NEW Sprint 4
                'box_push_up',             # NEW Sprint 4
            ]},
            {'level': 2, 'exercises': [
                'knee_push_up',            # NEW Sprint 4
                'push_ups',                # Existing
                'wide_grip_push_up',       # NEW Sprint 4
            ]},
            {'level': 3, 'exercises': [
                'close_grip_push_up',      # NEW Sprint 4
                'decline_push_up',         # NEW Sprint 4
                'archer_push_up',          # NEW Sprint 4
                'pike_push_up',            # NEW Sprint 4
            ]},
            {'level': 4, 'exercises': [
                'single_arm_push_up_prog', # NEW Sprint 4
                'pseudo_planche_push_up',  # NEW Sprint 4
                'handstand_wall_hold',     # NEW Sprint 4
            ]},
            {'level': 5, 'exercises': [
                'pike_push_up_elevated',   # NEW Sprint 4
                'wall_handstand_push_up',  # NEW Sprint 4
                'ring_push_up',            # NEW Sprint 4
            ]},
        ],
    },

    'pull': {
        'name': 'Pull Pattern',
        'description': 'Upper body pulling — horizontal and vertical',
        'icon': '🧲',
        'levels': [
            {'level': 1, 'exercises': [
                'prone_y_t_w',             # NEW Sprint 4
                'superman_hold',           # NEW Sprint 4
                'doorframe_row',           # NEW Sprint 4
                'towel_row',               # NEW Sprint 4
            ]},
            {'level': 2, 'exercises': [
                'table_row',               # NEW Sprint 4
                'bedsheet_row',            # NEW Sprint 4
                'negative_table_row',      # NEW Sprint 4
                'scapular_pull',           # NEW Sprint 4
                'negative_pull_up',        # NEW Sprint 4
            ]},
            {'level': 3, 'exercises': [
                'elevated_table_row',      # NEW Sprint 4
                'band_assisted_pull_up',   # NEW Sprint 4
                'full_pull_up',            # NEW Sprint 4
                'chin_up',                 # NEW Sprint 4
                'dumbbell_rowing',         # Existing
            ]},
            {'level': 4, 'exercises': [
                'archer_pull_up',          # NEW Sprint 4
                'l_sit_pull_up',           # NEW Sprint 4
                'weighted_pull_up',        # NEW Sprint 4
                'single_arm_towel_row',    # NEW Sprint 4
            ]},
            {'level': 5, 'exercises': [
                'single_arm_pull_up_prog', # NEW Sprint 4
                'muscle_up_progression',   # NEW Sprint 4
            ]},
        ],
    },

    'rotate': {
        'name': 'Rotate Pattern',
        'description': 'Core rotation and anti-rotation strength',
        'icon': '🔄',
        'levels': [
            {'level': 1, 'exercises': [
                'dead_bug',                # NEW Sprint 5
                'bird_dog',                # NEW Sprint 5
                'pallof_press_isometric',  # NEW Sprint 5
            ]},
            {'level': 2, 'exercises': [
                'russian_twist_bw',        # NEW Sprint 5
                'side_plank',              # NEW Sprint 5
                'side_plank_rotation',     # NEW Sprint 5
                'pallof_press_dynamic',    # NEW Sprint 5
            ]},
            {'level': 3, 'exercises': [
                'side_plank_hip_dip',      # NEW Sprint 5
                'single_leg_dead_bug',     # NEW Sprint 5
                'copenhagen_plank',        # NEW Sprint 5
                'band_woodchop',           # NEW Sprint 5
            ]},
            {'level': 4, 'exercises': [
                'copenhagen_with_movement',    # NEW Sprint 5
                'single_arm_plank',            # NEW Sprint 5
                'hollow_body_hold',            # NEW Sprint 5
                'dragon_flag_progression',     # NEW Sprint 5
            ]},
            {'level': 5, 'exercises': [
                'hanging_leg_raise',               # NEW Sprint 5
                'hollow_body_rock',                # NEW Sprint 5
                'single_arm_single_leg_plank',     # NEW Sprint 5
            ]},
        ],
    },

    'carry': {
        'name': 'Carry Pattern',
        'description': 'Loaded locomotion — total body stability',
        'icon': '🏋️',
        'levels': [
            {'level': 1, 'exercises': [
                'farmer_carry',            # NEW Sprint 5
                'suitcase_carry',          # NEW Sprint 5
                'waiter_carry',            # NEW Sprint 5
            ]},
            {'level': 2, 'exercises': [
                'bear_crawl',              # NEW Sprint 5
                'crab_walk',               # NEW Sprint 5
                'lateral_bear_crawl',      # NEW Sprint 5
            ]},
            {'level': 3, 'exercises': [
                'bear_crawl_with_reach',   # NEW Sprint 5
                'single_arm_farmer_heavy', # NEW Sprint 5
                'waiter_farmer_combined',  # NEW Sprint 5
            ]},
            # Levels 4-5: same exercises with increased load/duration
            {'level': 4, 'exercises': [
                'farmer_carry',
                'bear_crawl_with_reach',
                'single_arm_farmer_heavy',
            ]},
            {'level': 5, 'exercises': [
                'farmer_carry',
                'waiter_farmer_combined',
                'bear_crawl_with_reach',
            ]},
        ],
    },
}

# Equipment routing: exercise_id → equipment required
EXERCISE_EQUIPMENT = {
    # No equipment (bodyweight)
    'sit_to_stand': 'none', 'partial_squats': 'none', 'full_squats': 'none',
    'glute_bridge': 'none', 'push_ups': 'none', 'planks': 'none',
    'lunges': 'none', 'reverse_lunges': 'none',
    # Pull-up bar required
    'full_pull_up': 'pullup_bar', 'chin_up': 'pullup_bar',
    'negative_pull_up': 'pullup_bar', 'archer_pull_up': 'pullup_bar',
    'hanging_leg_raise': 'pullup_bar', 'muscle_up_progression': 'pullup_bar',
    # Resistance band
    'mini_squats_with_band': 'bands', 'band_woodchop': 'bands',
    'banded_rdl': 'bands', 'pallof_press_isometric': 'bands',
    # Dumbbells
    'deadlift_dumbbell': 'dumbbells', 'goblet_squat': 'dumbbells',
    'dumbbell_rowing': 'dumbbells',
}

# Default: if exercise not in EXERCISE_EQUIPMENT, assume 'none' (bodyweight)

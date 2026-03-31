"""
VYAYAM V1 - Equipment Routing Tables
Routes exercises to correct variants based on user's available equipment.
"""

# ============================================================================
# Equipment requirements per exercise
# [] = bodyweight / no equipment required
# ============================================================================

EXERCISE_EQUIPMENT_REQUIRED = {

    # ------------------------------------------------------------------
    # BODYWEIGHT - no equipment
    # ------------------------------------------------------------------
    # Squat pattern
    'sit_to_stand': [],
    'partial_squats': [],
    'full_squats': [],
    'pause_squat': [],
    'jump_squats': [],
    'wall_sit': [],
    'single_leg_squats': [],
    'pistol_squat': [],
    'shrimp_squat': [],
    'cossack_squat': [],
    'squat_to_stand_stretch': [],
    # Hinge pattern
    'glute_bridge': [],
    'single_leg_glute_bridge': [],
    'bodyweight_rdl': [],
    'good_morning': [],
    'single_leg_rdl': [],
    'nordic_hamstring_curl': [],
    'sliding_leg_curl': [],
    'donkey_kick': [],
    'hip_extension_standing': [],
    'hyperextension_floor': [],
    # Push pattern
    'push_ups': [],
    'knee_push_ups': [],
    'wall_push_ups': [],
    'incline_push_ups': [],
    'wide_push_ups': [],
    'narrow_push_ups': [],
    'pike_push_up': [],
    'diamond_push_ups': [],
    'archer_push_up': [],
    'clap_push_up': [],
    'pseudo_planche_push_up': [],
    # Pull pattern (bodyweight / improvised)
    'prone_y_t_w': [],
    'superman_hold': [],
    'doorframe_row': [],
    'towel_row': [],
    'table_row': [],
    'bedsheet_row': [],
    'negative_table_row': [],
    'elevated_table_row': [],
    'inverted_row_floor': [],
    # Lunge pattern
    'lunges': [],
    'reverse_lunges': [],
    'lateral_lunges': [],
    'curtsy_lunges': [],
    'walking_lunges': [],
    'deficit_reverse_lunge': [],
    'jumping_lunge': [],
    # Core / carry (bodyweight)
    'planks': [],
    'side_plank': [],
    'dead_bug': [],
    'bird_dog': [],
    'bear_crawl': [],
    'hollow_body_hold': [],
    'hollow_body_rock': [],
    'ab_wheel_rollout_floor': [],
    'v_sit_hold': [],
    'leg_raises_floor': [],
    'flutter_kicks': [],
    'mountain_climbers': [],
    'russian_twist_bw': [],
    'bicycle_crunch': [],
    'crunch': [],
    'reverse_crunch': [],
    'windshield_wipers': [],
    # Rotation pattern (bodyweight)
    'standing_trunk_rotation': [],
    'seated_trunk_rotation': [],
    'pallof_press_bw': [],
    'rotational_chop_bw': [],
    # Carry (bodyweight / locomotion)
    'bear_crawl_carry': [],
    'crab_walk': [],
    'lateral_band_walk_bw': [],
    # Warm-up / mobility
    'hip_circles_standing': [],
    'hip_cars_standing': [],
    'cat_cow': [],
    'child_pose': [],
    'world_greatest_stretch': [],
    'thoracic_extension_floor': [],
    'ankle_circles_bw': [],
    'shoulder_rolls_bw': [],
    'neck_semicircle_bw': [],
    'wrist_circles_bw': [],

    # ------------------------------------------------------------------
    # BENCH / ELEVATED SURFACE required
    # ------------------------------------------------------------------
    'hip_thrust_bodyweight': ['bench'],
    'decline_push_up': ['bench'],
    'bulgarian_split_squats': ['bench'],
    'table_row': ['bench'],
    'copenhagen_plank': ['bench'],
    'step_ups': ['bench'],
    'box_squat': ['bench'],
    'box_jump': ['bench'],
    'incline_push_up_elevated': ['bench'],
    'single_leg_hip_thrust_bench': ['bench'],
    'dips_parallel_bars': ['bench'],
    'tricep_dips_bench': ['bench'],
    'l_sit_on_bench': ['bench'],
    'seated_dumbbell_press': ['bench', 'dumbbells'],
    'incline_dumbbell_press': ['bench', 'dumbbells'],
    'incline_dumbbell_row': ['bench', 'dumbbells'],
    'single_arm_dumbbell_row_bench': ['bench', 'dumbbells'],
    'hip_thrust_dumbbell': ['bench', 'dumbbells'],
    'hip_thrust_barbell': ['bench', 'barbell'],

    # ------------------------------------------------------------------
    # RESISTANCE BANDS required
    # ------------------------------------------------------------------
    'mini_squats_with_band': ['bands'],
    'banded_squat': ['bands'],
    'banded_rdl': ['bands'],
    'banded_hip_thrust': ['bands'],
    'banded_good_morning': ['bands'],
    'pallof_press_isometric': ['bands'],
    'pallof_press_dynamic': ['bands'],
    'band_woodchop': ['bands'],
    'band_anti_rotation_hold': ['bands'],
    'band_pull_apart': ['bands'],
    'band_row_standing': ['bands'],
    'band_pulldown': ['bands'],
    'band_face_pull': ['bands'],
    'band_pull_through': ['bands'],
    'band_lateral_walk': ['bands'],
    'banded_glute_bridge': ['bands'],
    'banded_clamshell': ['bands'],
    'banded_fire_hydrant': ['bands'],
    'banded_push_up': ['bands'],
    'band_chest_press_standing': ['bands'],
    'band_shoulder_press': ['bands'],
    'band_bicep_curl': ['bands'],
    'band_tricep_pushdown': ['bands'],
    'band_reverse_fly': ['bands'],
    'band_external_rotation': ['bands'],
    'band_internal_rotation': ['bands'],
    'terminal_knee_extension_band': ['bands'],
    'banded_lunge': ['bands'],
    'band_assisted_pull_up': ['bands', 'pullup_bar'],
    'band_assisted_chin_up': ['bands', 'pullup_bar'],

    # ------------------------------------------------------------------
    # PULL-UP BAR required
    # ------------------------------------------------------------------
    'full_pull_up': ['pullup_bar'],
    'chin_up': ['pullup_bar'],
    'negative_pull_up': ['pullup_bar'],
    'scapular_pull': ['pullup_bar'],
    'archer_pull_up': ['pullup_bar'],
    'l_sit_pull_up': ['pullup_bar'],
    'weighted_pull_up': ['pullup_bar'],
    'hanging_leg_raise': ['pullup_bar'],
    'muscle_up_progression': ['pullup_bar'],
    'dead_hang': ['pullup_bar'],
    'active_hang': ['pullup_bar'],
    'toes_to_bar': ['pullup_bar'],
    'typewriter_pull_up': ['pullup_bar'],
    'wide_grip_pull_up': ['pullup_bar'],
    'commando_pull_up': ['pullup_bar'],
    'hanging_knee_raise': ['pullup_bar'],
    'hanging_windshield_wiper': ['pullup_bar'],

    # ------------------------------------------------------------------
    # DUMBBELLS required
    # ------------------------------------------------------------------
    'dumbbell_deadlift': ['dumbbells'],
    'goblet_squat': ['dumbbells'],
    'db_front_squat': ['dumbbells'],
    'dumbell_rowing': ['dumbbells'],
    'single_arm_row': ['dumbbells'],
    'renegade_row': ['dumbbells'],
    'farmer_carry': ['dumbbells'],
    'suitcase_carry': ['dumbbells'],
    'waiter_carry': ['dumbbells'],
    'db_rdl': ['dumbbells'],
    'db_hip_thrust': ['dumbbells'],
    'db_single_leg_rdl': ['dumbbells'],
    'dumbbell_bench_press': ['dumbbells', 'bench'],
    'dumbbell_fly': ['dumbbells', 'bench'],
    'dumbbell_shoulder_press': ['dumbbells'],
    'dumbbell_lateral_raise': ['dumbbells'],
    'dumbbell_front_raise': ['dumbbells'],
    'dumbbell_bent_over_row': ['dumbbells'],
    'dumbbell_bicep_curl': ['dumbbells'],
    'dumbbell_hammer_curl': ['dumbbells'],
    'dumbbell_tricep_kickback': ['dumbbells'],
    'dumbbell_overhead_press': ['dumbbells'],
    'dumbbell_snatch': ['dumbbells'],
    'dumbbell_clean': ['dumbbells'],
    'dumbbell_swing': ['dumbbells'],
    'dumbbell_goblet_split_squat': ['dumbbells'],
    'dumbbell_lunge': ['dumbbells'],
    'dumbbell_walking_lunge': ['dumbbells'],
    'dumbbell_step_up': ['dumbbells', 'bench'],
    'dumbbell_bulgarian_split_squat': ['dumbbells', 'bench'],
    'dumbbell_woodchop': ['dumbbells'],
    'dumbbell_russian_twist': ['dumbbells'],
    'dumbbell_pullover': ['dumbbells'],
    'dumbbell_reverse_fly': ['dumbbells'],
    'dumbbell_shrug': ['dumbbells'],

    # ------------------------------------------------------------------
    # BARBELL required
    # ------------------------------------------------------------------
    'barbell_squat': ['barbell'],
    'barbell_front_squat': ['barbell'],
    'barbell_rdl': ['barbell'],
    'barbell_deadlift': ['barbell'],
    'barbell_row': ['barbell'],
    'barbell_bench_press': ['barbell', 'bench'],
    'barbell_overhead_press': ['barbell'],
    'barbell_lunge': ['barbell'],
    'barbell_good_morning': ['barbell'],

    # ------------------------------------------------------------------
    # AB WHEEL required
    # ------------------------------------------------------------------
    'ab_wheel_rollout': ['ab_wheel'],
    'ab_wheel_pike': ['ab_wheel'],

    # ------------------------------------------------------------------
    # KETTLEBELL required
    # ------------------------------------------------------------------
    'kettlebell_swing': ['kettlebell'],
    'kettlebell_goblet_squat': ['kettlebell'],
    'kettlebell_rdl': ['kettlebell'],
    'kettlebell_clean': ['kettlebell'],
    'kettlebell_press': ['kettlebell'],
    'kettlebell_snatch': ['kettlebell'],
    'kettlebell_windmill': ['kettlebell'],
    'kettlebell_turkish_get_up': ['kettlebell'],
    'kettlebell_farmer_carry': ['kettlebell'],

    # ------------------------------------------------------------------
    # GYMNASTIC RINGS required
    # ------------------------------------------------------------------
    'ring_push_up': ['rings'],
    'ring_row': ['rings'],
    'ring_dip': ['rings'],
    'ring_pull_up': ['rings', 'pullup_bar'],
    'ring_muscle_up': ['rings', 'pullup_bar'],
    'ring_l_sit': ['rings'],
    'ring_front_lever_tuck': ['rings'],

    # ------------------------------------------------------------------
    # PARALLETTES required
    # ------------------------------------------------------------------
    'parallette_l_sit': ['parallettes'],
    'parallette_push_up': ['parallettes'],
    'parallette_handstand_push_up': ['parallettes'],
    'parallette_tuck_planche': ['parallettes'],
    'parallette_dip': ['parallettes'],
}

# ============================================================================
# Equipment-based routing for each movement pattern
# Given user's equipment → which track of exercises to use
# ============================================================================

PATTERN_EQUIPMENT_ROUTING = {

    # -----------------------------------------------------------------------
    # PULL
    # -----------------------------------------------------------------------
    'pull': {
        'none': {
            'exercises': [
                'prone_y_t_w', 'superman_hold', 'doorframe_row', 'towel_row',
                'table_row', 'bedsheet_row', 'negative_table_row', 'elevated_table_row',
                'inverted_row_floor',
            ],
            'label': 'No-Equipment Pull Track',
        },
        'bands': {
            'exercises': [
                'band_pull_apart', 'band_row_standing', 'band_pulldown',
                'band_face_pull', 'band_reverse_fly', 'band_external_rotation',
            ],
            'label': 'Band Pull Track',
        },
        'pullup_bar': {
            'exercises': [
                'dead_hang', 'active_hang', 'scapular_pull', 'negative_pull_up',
                'band_assisted_pull_up', 'full_pull_up', 'chin_up',
                'wide_grip_pull_up', 'commando_pull_up', 'archer_pull_up',
                'l_sit_pull_up', 'weighted_pull_up', 'typewriter_pull_up',
            ],
            'label': 'Pull-Up Bar Track',
        },
        'dumbbells': {
            'exercises': [
                'dumbell_rowing', 'single_arm_row', 'renegade_row',
                'dumbbell_bent_over_row', 'dumbbell_reverse_fly', 'dumbbell_shrug',
            ],
            'label': 'Dumbbell Pull Track',
        },
        'rings': {
            'exercises': [
                'ring_row', 'ring_pull_up', 'ring_muscle_up',
                'ring_front_lever_tuck',
            ],
            'label': 'Gymnastic Rings Pull Track',
        },
    },

    # -----------------------------------------------------------------------
    # PUSH
    # -----------------------------------------------------------------------
    'push': {
        'none': {
            'exercises': [
                'wall_push_ups', 'knee_push_ups', 'incline_push_ups',
                'push_ups', 'wide_push_ups', 'narrow_push_ups',
                'pike_push_up', 'diamond_push_ups', 'archer_push_up',
                'pseudo_planche_push_up', 'clap_push_up',
            ],
            'label': 'Bodyweight Push Track',
        },
        'bands': {
            'exercises': [
                'banded_push_up', 'band_chest_press_standing',
                'band_shoulder_press', 'band_tricep_pushdown',
            ],
            'label': 'Band Push Track',
        },
        'bench': {
            'exercises': [
                'decline_push_up', 'incline_push_up_elevated',
                'tricep_dips_bench', 'dips_parallel_bars',
            ],
            'label': 'Bench Push Track',
        },
        'dumbbells': {
            'exercises': [
                'dumbbell_shoulder_press', 'dumbbell_lateral_raise',
                'dumbbell_front_raise', 'dumbbell_tricep_kickback',
                'dumbbell_overhead_press',
            ],
            'label': 'Dumbbell Push Track',
        },
        'rings': {
            'exercises': [
                'ring_push_up', 'ring_dip', 'ring_muscle_up',
            ],
            'label': 'Gymnastic Rings Push Track',
        },
        'parallettes': {
            'exercises': [
                'parallette_push_up', 'parallette_handstand_push_up',
                'parallette_dip', 'parallette_tuck_planche',
            ],
            'label': 'Parallettes Push Track',
        },
    },

    # -----------------------------------------------------------------------
    # SQUAT
    # -----------------------------------------------------------------------
    'squat': {
        'none': {
            'exercises': [
                'sit_to_stand', 'wall_sit', 'partial_squats', 'full_squats',
                'pause_squat', 'jump_squats', 'single_leg_squats',
                'cossack_squat', 'shrimp_squat', 'pistol_squat',
            ],
            'label': 'Bodyweight Squat Track',
        },
        'bands': {
            'exercises': [
                'mini_squats_with_band', 'banded_squat', 'banded_glute_bridge',
                'band_lateral_walk',
            ],
            'label': 'Banded Squat Track',
        },
        'bench': {
            'exercises': [
                'box_squat', 'box_jump', 'step_ups', 'bulgarian_split_squats',
            ],
            'label': 'Bench Squat Track',
        },
        'dumbbells': {
            'exercises': [
                'goblet_squat', 'db_front_squat', 'dumbbell_goblet_split_squat',
            ],
            'label': 'Dumbbell Squat Track',
        },
        'kettlebell': {
            'exercises': [
                'kettlebell_goblet_squat',
            ],
            'label': 'Kettlebell Squat Track',
        },
    },

    # -----------------------------------------------------------------------
    # HINGE
    # -----------------------------------------------------------------------
    'hinge': {
        'none': {
            'exercises': [
                'glute_bridge', 'single_leg_glute_bridge', 'bodyweight_rdl',
                'good_morning', 'single_leg_rdl', 'nordic_hamstring_curl',
                'hip_thrust_bodyweight', 'sliding_leg_curl', 'donkey_kick',
                'hyperextension_floor', 'hip_extension_standing',
            ],
            'label': 'Bodyweight Hinge Track',
        },
        'bands': {
            'exercises': [
                'banded_rdl', 'banded_hip_thrust', 'banded_good_morning',
                'band_pull_through', 'banded_glute_bridge',
            ],
            'label': 'Banded Hinge Track',
        },
        'bench': {
            'exercises': [
                'single_leg_hip_thrust_bench', 'hip_thrust_bodyweight',
            ],
            'label': 'Bench Hinge Track',
        },
        'dumbbells': {
            'exercises': [
                'dumbbell_deadlift', 'db_rdl', 'db_hip_thrust',
                'db_single_leg_rdl',
            ],
            'label': 'Dumbbell Hinge Track',
        },
        'kettlebell': {
            'exercises': [
                'kettlebell_swing', 'kettlebell_rdl', 'kettlebell_clean',
                'kettlebell_snatch',
            ],
            'label': 'Kettlebell Hinge Track',
        },
    },

    # -----------------------------------------------------------------------
    # LUNGE
    # -----------------------------------------------------------------------
    'lunge': {
        'none': {
            'exercises': [
                'lunges', 'reverse_lunges', 'lateral_lunges', 'curtsy_lunges',
                'walking_lunges', 'jumping_lunge', 'deficit_reverse_lunge',
            ],
            'label': 'Bodyweight Lunge Track',
        },
        'bands': {
            'exercises': [
                'banded_lunge', 'banded_clamshell', 'banded_fire_hydrant',
            ],
            'label': 'Banded Lunge Track',
        },
        'bench': {
            'exercises': [
                'bulgarian_split_squats', 'step_ups',
            ],
            'label': 'Bench Lunge Track',
        },
        'dumbbells': {
            'exercises': [
                'dumbbell_lunge', 'dumbbell_walking_lunge',
                'dumbbell_goblet_split_squat', 'dumbbell_step_up',
                'dumbbell_bulgarian_split_squat',
            ],
            'label': 'Dumbbell Lunge Track',
        },
    },

    # -----------------------------------------------------------------------
    # ROTATE
    # -----------------------------------------------------------------------
    'rotate': {
        'none': {
            'exercises': [
                'russian_twist_bw', 'bicycle_crunch', 'standing_trunk_rotation',
                'seated_trunk_rotation', 'rotational_chop_bw', 'windshield_wipers',
            ],
            'label': 'Bodyweight Rotation Track',
        },
        'bands': {
            'exercises': [
                'pallof_press_isometric', 'pallof_press_dynamic',
                'band_woodchop', 'band_anti_rotation_hold',
            ],
            'label': 'Band Rotation Track',
        },
        'dumbbells': {
            'exercises': [
                'dumbbell_woodchop', 'dumbbell_russian_twist',
            ],
            'label': 'Dumbbell Rotation Track',
        },
        'rings': {
            'exercises': [
                'hanging_windshield_wiper',
            ],
            'label': 'Rings Rotation Track',
        },
        'pullup_bar': {
            'exercises': [
                'hanging_windshield_wiper', 'toes_to_bar',
            ],
            'label': 'Hanging Rotation Track',
        },
    },

    # -----------------------------------------------------------------------
    # CARRY
    # -----------------------------------------------------------------------
    'carry': {
        'none': {
            'exercises': [
                'bear_crawl', 'bear_crawl_carry', 'crab_walk',
                'hollow_body_walk', 'lateral_band_walk_bw',
            ],
            'label': 'Bodyweight Carry Track',
        },
        'bands': {
            'exercises': [
                'band_lateral_walk', 'band_anti_rotation_hold',
            ],
            'label': 'Band Carry Track',
        },
        'dumbbells': {
            'exercises': [
                'farmer_carry', 'suitcase_carry', 'waiter_carry',
                'renegade_row',
            ],
            'label': 'Dumbbell Carry Track',
        },
        'kettlebell': {
            'exercises': [
                'kettlebell_farmer_carry', 'kettlebell_turkish_get_up',
                'kettlebell_windmill',
            ],
            'label': 'Kettlebell Carry Track',
        },
    },
}


def get_available_exercises(user_equipment_list, movement_pattern):
    """Given user's equipment list and a pattern, return all exercises they can do."""
    available = set()
    routing = PATTERN_EQUIPMENT_ROUTING.get(movement_pattern, {})

    # Always include bodyweight track
    if 'none' in routing:
        available.update(routing['none']['exercises'])

    # Add equipment-specific tracks
    for equip in user_equipment_list:
        if equip in routing:
            available.update(routing[equip]['exercises'])

    # Remove any exercise whose required equipment the user doesn't have
    user_equipment_set = set(user_equipment_list)
    filtered = []
    for ex in available:
        required = EXERCISE_EQUIPMENT_REQUIRED.get(ex, [])
        if all(e in user_equipment_set for e in required):
            filtered.append(ex)

    return filtered


def get_exercise_alternative(exercise_id, user_equipment_list):
    """If user can't do an exercise (missing equipment), find the closest alternative."""
    required = EXERCISE_EQUIPMENT_REQUIRED.get(exercise_id, [])
    if not required or all(e in user_equipment_list for e in required):
        return exercise_id  # Can do the original

    alternatives = {
        # Pull alternatives
        'full_pull_up': 'table_row',
        'chin_up': 'towel_row',
        'archer_pull_up': 'doorframe_row',
        'l_sit_pull_up': 'table_row',
        'weighted_pull_up': 'negative_pull_up',
        'toes_to_bar': 'hanging_leg_raise',
        'hanging_leg_raise': 'hollow_body_hold',
        'muscle_up_progression': 'scapular_pull',
        'ring_row': 'table_row',
        'ring_pull_up': 'towel_row',
        # Push alternatives
        'decline_push_up': 'pike_push_up',
        'dips_parallel_bars': 'tricep_dips_bench',
        'ring_push_up': 'archer_push_up',
        'ring_dip': 'diamond_push_ups',
        'parallette_push_up': 'push_ups',
        'parallette_handstand_push_up': 'pike_push_up',
        # Squat alternatives
        'goblet_squat': 'full_squats',
        'db_front_squat': 'pause_squat',
        'box_squat': 'full_squats',
        'box_jump': 'jump_squats',
        'bulgarian_split_squats': 'reverse_lunges',
        'dumbbell_bulgarian_split_squat': 'reverse_lunges',
        'pistol_squat': 'single_leg_squats',
        'shrimp_squat': 'reverse_lunges',
        'kettlebell_goblet_squat': 'goblet_squat',
        # Hinge alternatives
        'dumbbell_deadlift': 'bodyweight_rdl',
        'db_rdl': 'bodyweight_rdl',
        'db_single_leg_rdl': 'single_leg_rdl',
        'db_hip_thrust': 'hip_thrust_bodyweight',
        'hip_thrust_dumbbell': 'hip_thrust_bodyweight',
        'hip_thrust_barbell': 'hip_thrust_bodyweight',
        'single_leg_hip_thrust_bench': 'single_leg_glute_bridge',
        'banded_hip_thrust': 'glute_bridge',
        'kettlebell_swing': 'good_morning',
        'kettlebell_rdl': 'bodyweight_rdl',
        # Pull / row alternatives
        'dumbell_rowing': 'doorframe_row',
        'single_arm_row': 'towel_row',
        'renegade_row': 'table_row',
        'dumbbell_bent_over_row': 'towel_row',
        'incline_dumbbell_row': 'table_row',
        'single_arm_dumbbell_row_bench': 'doorframe_row',
        # Carry alternatives
        'farmer_carry': 'bear_crawl',
        'suitcase_carry': 'bear_crawl',
        'waiter_carry': 'bear_crawl',
        'kettlebell_farmer_carry': 'bear_crawl',
        'kettlebell_turkish_get_up': 'dead_bug',
        # Rotation alternatives
        'band_woodchop': 'russian_twist_bw',
        'pallof_press_isometric': 'hollow_body_hold',
        'pallof_press_dynamic': 'rotational_chop_bw',
        'dumbbell_woodchop': 'rotational_chop_bw',
        'hanging_windshield_wiper': 'windshield_wipers',
        # Lunge alternatives
        'dumbbell_lunge': 'lunges',
        'dumbbell_walking_lunge': 'walking_lunges',
        'dumbbell_step_up': 'step_ups',
        'step_ups': 'reverse_lunges',
        # Core
        'ab_wheel_rollout': 'hollow_body_hold',
        'ab_wheel_pike': 'hollow_body_rock',
        'ring_l_sit': 'hollow_body_hold',
        'parallette_l_sit': 'hollow_body_hold',
        'l_sit_on_bench': 'hollow_body_hold',
        # Upper body / accessories
        'dumbbell_shoulder_press': 'pike_push_up',
        'dumbbell_lateral_raise': 'band_reverse_fly',
        'dumbbell_bicep_curl': 'band_bicep_curl',
        'dumbbell_hammer_curl': 'band_bicep_curl',
        'dumbbell_tricep_kickback': 'diamond_push_ups',
        'dumbbell_pullover': 'lat_stretch_overhead',
        'seated_dumbbell_press': 'dumbbell_shoulder_press',
        'incline_dumbbell_press': 'push_ups',
        'dumbbell_fly': 'wide_push_ups',
        'dumbbell_bench_press': 'push_ups',
        'barbell_squat': 'goblet_squat',
        'barbell_deadlift': 'dumbbell_deadlift',
        'barbell_rdl': 'db_rdl',
        'barbell_row': 'dumbell_rowing',
        'barbell_bench_press': 'push_ups',
        'barbell_overhead_press': 'dumbbell_shoulder_press',
        'barbell_lunge': 'dumbbell_lunge',
        'barbell_good_morning': 'good_morning',
        'barbell_front_squat': 'db_front_squat',
        'barbell_hip_thrust': 'hip_thrust_bodyweight',
        # Rings further
        'ring_front_lever_tuck': 'hollow_body_hold',
        'ring_muscle_up': 'full_pull_up',
        'parallette_tuck_planche': 'pseudo_planche_push_up',
        # Bands without bar
        'band_assisted_pull_up': 'negative_pull_up',
        'band_assisted_chin_up': 'negative_pull_up',
    }
    return alternatives.get(exercise_id, exercise_id)


def get_exercise_track_label(user_equipment_list, movement_pattern):
    """Return the human-readable track label for the user's equipment and pattern."""
    routing = PATTERN_EQUIPMENT_ROUTING.get(movement_pattern, {})
    user_equipment_set = set(user_equipment_list)

    # Determine highest-priority track available
    priority_order = ['rings', 'parallettes', 'pullup_bar', 'kettlebell', 'barbell',
                      'dumbbells', 'bench', 'bands', 'none']
    for equip in priority_order:
        if (equip == 'none' or equip in user_equipment_set) and equip in routing:
            return routing[equip].get('label', f'{movement_pattern.title()} Track')
    return f'{movement_pattern.title()} Bodyweight Track'

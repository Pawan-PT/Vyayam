/**
 * Exercise-Specific Pose Analysis Module
 * Handles different rep detection logic for various exercises
 */

class ExerciseAnalyzer {
    constructor(exerciseId) {
        this.exerciseId = exerciseId;
        this.phase = 'standing';
        this.lastAngles = {};
        this.repStarted = false;
        this.minAngleThreshold = 100;
        this.maxAngleThreshold = 140;
        
        // Initialize exercise-specific parameters
        this.initializeExercise();
    }

    initializeExercise() {
        const exerciseConfig = {
            // SQUAT VARIATIONS
            'partial_squats_v2': {
                type: 'squat',
                minKnee: 120,
                maxKnee: 160,
                phases: ['standing', 'descending', 'bottom', 'ascending']
            },
            'full_squat_v2': {
                type: 'squat',
                minKnee: 80,
                maxKnee: 160,
                phases: ['standing', 'descending', 'bottom', 'ascending']
            },
            'spanish_squat_v2': {
                type: 'squat',
                minKnee: 100,
                maxKnee: 160,
                phases: ['standing', 'descending', 'bottom', 'ascending']
            },
            'decline_squats_v2': {
                type: 'squat',
                minKnee: 90,
                maxKnee: 160,
                phases: ['standing', 'descending', 'bottom', 'ascending']
            },
            'mini_squats_with_band_v2': {
                type: 'squat',
                minKnee: 140,
                maxKnee: 170,
                phases: ['standing', 'descending', 'bottom', 'ascending']
            },

            // LUNGE VARIATIONS
            'lunges_v2': {
                type: 'lunge',
                minKnee: 90,
                maxKnee: 160,
                phases: ['standing', 'descending', 'bottom', 'ascending']
            },
            'reverse_lunges_v2': {
                type: 'lunge',
                minKnee: 90,
                maxKnee: 160,
                phases: ['standing', 'descending', 'bottom', 'ascending']
            },
            'lateral_lunges_v2': {
                type: 'lunge',
                minKnee: 100,
                maxKnee: 160,
                phases: ['standing', 'descending', 'bottom', 'ascending']
            },

            // BRIDGE VARIATIONS
            'glute_bridge_v2': {
                type: 'bridge',
                minHip: 140,
                maxHip: 180,
                phases: ['down', 'lifting', 'top', 'lowering']
            },
            'single_leg_glute_bridge_v2': {
                type: 'bridge',
                minHip: 140,
                maxHip: 180,
                phases: ['down', 'lifting', 'top', 'lowering']
            },

            // BALANCE EXERCISES
            'single_leg_balance_v2': {
                type: 'balance',
                minTime: 5,
                phases: ['standing', 'balanced']
            },
            'double_leg_balance_v2': {
                type: 'balance',
                minTime: 10,
                phases: ['standing', 'balanced']
            },

            // STEP EXERCISES
            'step_ups_v2': {
                type: 'step',
                minKnee: 90,
                maxKnee: 160,
                phases: ['down', 'stepping', 'up', 'descending']
            },
            'step_downs_v2': {
                type: 'step',
                minKnee: 90,
                maxKnee: 160,
                phases: ['up', 'descending', 'down', 'ascending']
            },

            // JUMPING EXERCISES
            'jump_squats_v2': {
                type: 'jump',
                minKnee: 90,
                maxKnee: 160,
                phases: ['standing', 'descending', 'jumping', 'landing']
            },
            'box_jumps_v2': {
                type: 'jump',
                minKnee: 90,
                maxKnee: 160,
                phases: ['standing', 'descending', 'jumping', 'landing']
            },

            // CARDIO EXERCISES
            'jumping_jacks_v2': {
                type: 'cardio',
                phases: ['closed', 'opening', 'open', 'closing']
            },
            'high_knees_v2': {
                type: 'cardio',
                phases: ['left_down', 'left_up', 'right_down', 'right_up']
            },
            'butt_kicks_v2': {
                type: 'cardio',
                phases: ['left_down', 'left_up', 'right_down', 'right_up']
            },

            // PLANKS
            'planks_v2': {
                type: 'hold',
                minTime: 30,
                phases: ['down', 'holding']
            },

            // STRETCHES
            'hamstring_stretch_v2': {
                type: 'stretch',
                minTime: 20,
                phases: ['starting', 'stretching']
            },
            'quadriceps_stretch_v2': {
                type: 'stretch',
                minTime: 20,
                phases: ['starting', 'stretching']
            }
        };

        this.config = exerciseConfig[this.exerciseId] || {
            type: 'squat',
            minKnee: 90,
            maxKnee: 160,
            phases: ['standing', 'descending', 'bottom', 'ascending']
        };
    }

    detectRep(landmarks, currentPhase) {
        switch (this.config.type) {
            case 'squat':
                return this.detectSquatRep(landmarks, currentPhase);
            case 'lunge':
                return this.detectLungeRep(landmarks, currentPhase);
            case 'bridge':
                return this.detectBridgeRep(landmarks, currentPhase);
            case 'balance':
                return this.detectBalanceRep(landmarks, currentPhase);
            case 'step':
                return this.detectStepRep(landmarks, currentPhase);
            case 'jump':
                return this.detectJumpRep(landmarks, currentPhase);
            case 'cardio':
                return this.detectCardioRep(landmarks, currentPhase);
            case 'hold':
                return this.detectHoldRep(landmarks, currentPhase);
            case 'stretch':
                return this.detectStretchRep(landmarks, currentPhase);
            default:
                return { repComplete: false, newPhase: currentPhase };
        }
    }

    detectSquatRep(landmarks, currentPhase) {
        const leftKnee = this.calculateAngle(landmarks[23], landmarks[25], landmarks[27]);
        const rightKnee = this.calculateAngle(landmarks[24], landmarks[26], landmarks[28]);
        const avgKnee = (leftKnee + rightKnee) / 2;

        let newPhase = currentPhase;
        let repComplete = false;

        switch (currentPhase) {
            case 'standing':
                if (avgKnee < this.config.maxKnee) {
                    newPhase = 'descending';
                    this.repStarted = true;
                }
                break;
            
            case 'descending':
                if (avgKnee < this.config.minKnee + 10) {
                    newPhase = 'bottom';
                }
                break;
            
            case 'bottom':
                if (avgKnee > this.config.minKnee + 20) {
                    newPhase = 'ascending';
                }
                break;
            
            case 'ascending':
                if (avgKnee > this.config.maxKnee - 10) {
                    newPhase = 'standing';
                    repComplete = true;
                    this.repStarted = false;
                }
                break;
        }

        return { repComplete, newPhase, angles: { leftKnee, rightKnee, avgKnee } };
    }

    detectLungeRep(landmarks, currentPhase) {
        const leftKnee = this.calculateAngle(landmarks[23], landmarks[25], landmarks[27]);
        const rightKnee = this.calculateAngle(landmarks[24], landmarks[26], landmarks[28]);
        const frontKnee = Math.min(leftKnee, rightKnee);

        let newPhase = currentPhase;
        let repComplete = false;

        switch (currentPhase) {
            case 'standing':
                if (frontKnee < this.config.maxKnee) {
                    newPhase = 'descending';
                }
                break;
            
            case 'descending':
                if (frontKnee < this.config.minKnee + 10) {
                    newPhase = 'bottom';
                }
                break;
            
            case 'bottom':
                if (frontKnee > this.config.minKnee + 20) {
                    newPhase = 'ascending';
                }
                break;
            
            case 'ascending':
                if (frontKnee > this.config.maxKnee - 10) {
                    newPhase = 'standing';
                    repComplete = true;
                }
                break;
        }

        return { repComplete, newPhase, angles: { leftKnee, rightKnee, frontKnee } };
    }

    detectBridgeRep(landmarks, currentPhase) {
        const leftHip = this.calculateAngle(landmarks[11], landmarks[23], landmarks[25]);
        const rightHip = this.calculateAngle(landmarks[12], landmarks[24], landmarks[26]);
        const avgHip = (leftHip + rightHip) / 2;

        let newPhase = currentPhase;
        let repComplete = false;

        switch (currentPhase) {
            case 'down':
                if (avgHip > this.config.minHip) {
                    newPhase = 'lifting';
                }
                break;
            
            case 'lifting':
                if (avgHip > this.config.maxHip - 20) {
                    newPhase = 'top';
                }
                break;
            
            case 'top':
                if (avgHip < this.config.maxHip - 30) {
                    newPhase = 'lowering';
                }
                break;
            
            case 'lowering':
                if (avgHip < this.config.minHip + 20) {
                    newPhase = 'down';
                    repComplete = true;
                }
                break;
        }

        return { repComplete, newPhase, angles: { leftHip, rightHip, avgHip } };
    }

    detectBalanceRep(landmarks, currentPhase) {
        // Balance is time-based
        const leftAnkle = landmarks[27];
        const rightAnkle = landmarks[28];
        const heightDiff = Math.abs(leftAnkle.y - rightAnkle.y);

        let newPhase = currentPhase;
        let repComplete = false;

        if (heightDiff > 0.1) { // One leg is lifted
            if (currentPhase === 'standing') {
                newPhase = 'balanced';
                this.balanceStartTime = Date.now();
            } else if (currentPhase === 'balanced') {
                const elapsed = (Date.now() - this.balanceStartTime) / 1000;
                if (elapsed >= this.config.minTime) {
                    repComplete = true;
                }
            }
        } else {
            newPhase = 'standing';
        }

        return { repComplete, newPhase };
    }

    detectStepRep(landmarks, currentPhase) {
        // Similar to squat but tracks vertical position
        const leftKnee = this.calculateAngle(landmarks[23], landmarks[25], landmarks[27]);
        const rightKnee = this.calculateAngle(landmarks[24], landmarks[26], landmarks[28]);
        const leftHip = landmarks[23];
        const rightHip = landmarks[24];
        const avgHipY = (leftHip.y + rightHip.y) / 2;

        let newPhase = currentPhase;
        let repComplete = false;

        // Simplified step detection
        if (currentPhase === 'down' && avgHipY < this.lastHipY - 0.05) {
            newPhase = 'stepping';
        } else if (currentPhase === 'stepping' && avgHipY < this.lastHipY - 0.1) {
            newPhase = 'up';
        } else if (currentPhase === 'up' && avgHipY > this.lastHipY + 0.05) {
            newPhase = 'descending';
        } else if (currentPhase === 'descending' && avgHipY > this.lastHipY + 0.1) {
            newPhase = 'down';
            repComplete = true;
        }

        this.lastHipY = avgHipY;
        return { repComplete, newPhase };
    }

    detectJumpRep(landmarks, currentPhase) {
        const leftAnkle = landmarks[27];
        const rightAnkle = landmarks[28];
        const avgAnkleY = (leftAnkle.y + rightAnkle.y) / 2;

        let newPhase = currentPhase;
        let repComplete = false;

        // Track vertical movement
        if (currentPhase === 'standing' && avgAnkleY > this.lastAnkleY + 0.05) {
            newPhase = 'descending';
        } else if (currentPhase === 'descending' && avgAnkleY < this.lastAnkleY - 0.1) {
            newPhase = 'jumping';
        } else if (currentPhase === 'jumping' && avgAnkleY > this.lastAnkleY) {
            newPhase = 'landing';
        } else if (currentPhase === 'landing' && Math.abs(avgAnkleY - this.baselineY) < 0.02) {
            newPhase = 'standing';
            repComplete = true;
        }

        if (!this.baselineY) this.baselineY = avgAnkleY;
        this.lastAnkleY = avgAnkleY;

        return { repComplete, newPhase };
    }

    detectCardioRep(landmarks, currentPhase) {
        // Cardio exercises are typically alternating movements
        const leftKnee = this.calculateAngle(landmarks[23], landmarks[25], landmarks[27]);
        const rightKnee = this.calculateAngle(landmarks[24], landmarks[26], landmarks[28]);

        let repComplete = false;

        // High knees: detect when knee goes above 90 degrees
        if (this.exerciseId.includes('high_knees')) {
            if (leftKnee < 90 && this.lastSide !== 'left') {
                repComplete = true;
                this.lastSide = 'left';
            } else if (rightKnee < 90 && this.lastSide !== 'right') {
                repComplete = true;
                this.lastSide = 'right';
            }
        }

        return { repComplete, newPhase: currentPhase };
    }

    detectHoldRep(landmarks, currentPhase) {
        // Hold exercises are time-based
        if (currentPhase === 'down') {
            this.holdStartTime = Date.now();
            return { repComplete: false, newPhase: 'holding' };
        } else if (currentPhase === 'holding') {
            const elapsed = (Date.now() - this.holdStartTime) / 1000;
            if (elapsed >= this.config.minTime) {
                return { repComplete: true, newPhase: 'down' };
            }
        }

        return { repComplete: false, newPhase: currentPhase };
    }

    detectStretchRep(landmarks, currentPhase) {
        // Stretch exercises are time-based
        if (currentPhase === 'starting') {
            this.stretchStartTime = Date.now();
            return { repComplete: false, newPhase: 'stretching' };
        } else if (currentPhase === 'stretching') {
            const elapsed = (Date.now() - this.stretchStartTime) / 1000;
            if (elapsed >= this.config.minTime) {
                return { repComplete: true, newPhase: 'starting' };
            }
        }

        return { repComplete: false, newPhase: currentPhase };
    }

    calculateAngle(a, b, c) {
        const radians = Math.atan2(c.y - b.y, c.x - b.x) - 
                       Math.atan2(a.y - b.y, a.x - b.x);
        let angle = Math.abs(radians * 180.0 / Math.PI);
        if (angle > 180.0) {
            angle = 360 - angle;
        }
        return angle;
    }

    calculateFormScore(landmarks) {
        switch (this.config.type) {
            case 'squat':
            case 'lunge':
                return this.calculateSquatFormScore(landmarks);
            case 'bridge':
                return this.calculateBridgeFormScore(landmarks);
            default:
                return 80; // Default good form
        }
    }

    calculateSquatFormScore(landmarks) {
        const leftKnee = this.calculateAngle(landmarks[23], landmarks[25], landmarks[27]);
        const rightKnee = this.calculateAngle(landmarks[24], landmarks[26], landmarks[28]);
        
        // Knee alignment
        const kneeDiff = Math.abs(leftKnee - rightKnee);
        const alignmentScore = Math.max(0, 100 - (kneeDiff * 3));
        
        // Depth
        const avgKnee = (leftKnee + rightKnee) / 2;
        let depthScore;
        if (avgKnee >= this.config.minKnee && avgKnee <= this.config.maxKnee) {
            depthScore = 100;
        } else {
            depthScore = Math.max(0, 100 - Math.abs(avgKnee - ((this.config.minKnee + this.config.maxKnee) / 2)) * 2);
        }
        
        // Back alignment (check hip-shoulder-ankle alignment)
        const leftShoulder = landmarks[11];
        const rightShoulder = landmarks[12];
        const shoulderTilt = Math.abs(leftShoulder.y - rightShoulder.y);
        const backScore = Math.max(0, 100 - (shoulderTilt * 500));
        
        return (alignmentScore + depthScore + backScore) / 3;
    }

    calculateBridgeFormScore(landmarks) {
        const leftHip = this.calculateAngle(landmarks[11], landmarks[23], landmarks[25]);
        const rightHip = this.calculateAngle(landmarks[12], landmarks[24], landmarks[26]);
        
        // Hip alignment
        const hipDiff = Math.abs(leftHip - rightHip);
        const alignmentScore = Math.max(0, 100 - (hipDiff * 3));
        
        // Hip height
        const avgHip = (leftHip + rightHip) / 2;
        let heightScore;
        if (avgHip >= this.config.minHip && avgHip <= this.config.maxHip) {
            heightScore = 100;
        } else {
            heightScore = Math.max(0, 100 - Math.abs(avgHip - ((this.config.minHip + this.config.maxHip) / 2)) * 2);
        }
        
        return (alignmentScore + heightScore) / 2;
    }
}

// Export for use in main template
window.ExerciseAnalyzer = ExerciseAnalyzer;

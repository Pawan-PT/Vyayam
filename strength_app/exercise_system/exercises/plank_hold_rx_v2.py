"""Plank Hold — prescription tier (2026-07 dark camera coach).

Subclasses PlanksV2 verbatim (H2 green at 100). Distinct key so the
therapist-tier coach (js_type PLANK_RX, hip sag/pike fault cues) ships
DARK without touching the live self-serve `planks` (PLANK) experience.
"""

from .planks_v2 import PlanksV2


class PlankHoldRxV2(PlanksV2):
    pass

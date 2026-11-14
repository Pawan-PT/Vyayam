#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --no-input

# DEMO ONLY: seeds public logins with fixed passwords. Off unless DEMO_SEED=1.
# A seed failure is logged but must not stop the demo from starting.
if [ "${DEMO_SEED:-}" = "1" ]; then
    python manage.py seed_demo_patient || echo "WARN: seed_demo_patient failed"
    python manage.py seed_therapist_demo || echo "WARN: seed_therapist_demo failed"
fi

# ONE worker + --preload: importing exercise_registry_v2 costs ~450 MB RSS and
# ~55 s (516 modules load cv2/mediapipe). A second worker would OOM.
exec gunicorn vyayam_project.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 1 --threads 4 \
    --preload \
    --timeout 120 \
    --access-logfile -

#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --no-input

# ONE worker + --preload: importing exercise_registry_v2 costs ~450 MB RSS and
# ~55 s (516 modules load cv2/mediapipe). A second worker would OOM.
exec gunicorn vyayam_project.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 1 --threads 4 \
    --preload \
    --timeout 120 \
    --access-logfile -

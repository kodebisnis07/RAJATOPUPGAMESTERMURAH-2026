# Production checklist

1. Set `SECRET_KEY` and `SETTINGS_ENCRYPTION_KEY` to different random values and never rotate the encryption key without decrypting/re-encrypting stored gateway credentials.
2. Set `DATABASE_URL` to PostgreSQL and `RATELIMIT_STORAGE_URI` to a managed Redis URL.
3. Configure Cloudinary for persistent uploads on Render.
4. Use sandbox credentials first and verify signed payment callbacks before enabling production.
5. Enable Render database backups, test restore procedures, and configure external uptime/error monitoring.
6. Rotate any credential exposed in screenshots, logs, commits, or chat.
7. Run `python tests_static.py`, `python -m compileall -q app`, and `pytest -q` before deployment.

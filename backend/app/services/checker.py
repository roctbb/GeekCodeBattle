import time

import jwt
import requests
from flask import current_app


def _service_token() -> str:
    payload = {"service": "geekcodebattle", "iat": int(time.time())}
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def submit_for_check(callback_url: str, callback_id: str, code: str, lang: str, task_text: str, check_type: str, check_config: dict):
    payload = {
        "callback_url": callback_url,
        "callback_id": callback_id,
        "code": code,
        "lang": lang,
        "task_text": task_text,
        "check_type": check_type,
        "check_config": check_config or {},
    }
    headers = {"Authorization": f"Bearer {_service_token()}"}
    current_app.logger.info(
        "checker_submit_request callback_id=%s lang=%s check_type=%s api_url=%s callback_url=%s",
        callback_id,
        lang,
        check_type,
        current_app.config["GEEKPASTE_API_URL"],
        callback_url,
    )
    response = requests.post(current_app.config["GEEKPASTE_API_URL"], json=payload, headers=headers, timeout=10)
    current_app.logger.info(
        "checker_submit_response callback_id=%s status_code=%s",
        callback_id,
        response.status_code,
    )
    response.raise_for_status()
    result = response.json()
    current_app.logger.info(
        "checker_submit_accepted callback_id=%s job_id=%s",
        callback_id,
        result.get("job_id"),
    )
    return result

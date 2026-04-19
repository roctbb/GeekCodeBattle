from flask import jsonify


def ok(payload=None, status=200):
    if payload is None:
        payload = {"status": "ok"}
    return jsonify(payload), status


def fail(message, status=400, code=None, details=None):
    body = {"error": {"message": message}}
    if code is not None:
        body["error"]["code"] = code
    if details is not None:
        body["error"]["details"] = details
    return jsonify(body), status

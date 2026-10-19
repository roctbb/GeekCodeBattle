"""Normalize checker metadata; only allowlisted categories and counts are public."""
import json
import re


ERROR_MESSAGES = {
    'compilation_error': 'Ошибка компиляции.',
    'runtime_error': 'Ошибка времени выполнения.',
    'time_limit_exceeded': 'Превышен лимит времени.',
    'output_limit_exceeded': 'Превышен лимит вывода.',
    'internal_error': 'Ошибка проверки решения.',
}


def feedback_payload(raw):
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        parsed = raw
    if isinstance(parsed, dict):
        return parsed
    return {'details': parsed} if isinstance(parsed, list) else {'comment': parsed}


def checker_error_type(payload):
    explicit = payload.get('error_type')
    if isinstance(explicit, str) and explicit in ERROR_MESSAGES:
        return explicit
    errors = []
    details = payload.get('details')
    for detail in details if isinstance(details, list) else []:
        if not isinstance(detail, dict):
            continue
        kind = detail.get('error_type')
        if isinstance(kind, str) and kind in ERROR_MESSAGES:
            errors.append(kind)
        else:
            # Legacy GeekPaste supplied diagnostics only in error/stderr.
            kind = _legacy_error_type(detail.get('error') or detail.get('stderr'))
            if kind:
                errors.append(kind)
    if 'internal_error' in errors:
        return 'internal_error'
    if errors:
        return errors[0]
    if payload.get('status') == 'error':
        comment = payload.get('comment')
        if isinstance(comment, dict):
            if comment.get('compile_error'):
                return 'compilation_error'
            comment = comment.get('error') or comment.get('stderr') or comment.get('message')
        return _legacy_error_type(comment)
    return None


def _legacy_error_type(text):
    if not isinstance(text, str):
        return None
    text = text.lower().strip()
    if text.startswith(('compilation failed', 'compilation error', 'compilation timed out', 'compilation output limit')):
        return 'compilation_error'
    if text.startswith(('test failed: execution timed out', 'execution timed out', 'time limit exceeded',
                        'execution container stopped after a timeout')):
        return 'time_limit_exceeded'
    if text.startswith('output limit exceeded'):
        return 'output_limit_exceeded'
    if text.startswith('runtime error:'):
        return 'runtime_error'
    return None


def checker_verdict(payload, progress):
    error = checker_error_type(payload)
    if error:
        return error
    if payload.get('status') != 'success':
        return 'internal_error'
    return 'accepted' if progress >= 1 else 'wrong_answer'


def _count(value):
    # Counts must not be silently truncated scores or booleans.
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _pair(passed, total):
    passed, total = _count(passed), _count(total)
    return (passed, total) if passed is not None and total is not None and passed <= total else (None, None)


def checker_test_counts(payload, *, check_type=None, tests=None):
    counts = _pair(payload.get('tests_passed'), payload.get('tests_total'))
    if counts[0] is not None:
        return counts
    visible = _pair(payload.get('visible_tests_passed'), payload.get('visible_tests_total'))
    hidden = _pair(payload.get('hidden_tests_passed'), payload.get('hidden_tests_total'))
    if visible[0] is not None and hidden[0] is not None:
        return visible[0] + hidden[0], visible[1] + hidden[1]
    # This score is an exact count only for the external tests checker, never GPT.
    if check_type == 'tests':
        if payload.get('status') == 'success':
            counts = _pair(payload.get('points'), payload.get('max_points'))
            if counts[0] is not None and counts[1] > 0:
                return counts
        if checker_error_type(payload) == 'compilation_error' and tests is not None:
            return 0, len(tests)
    # Old persisted GeekPaste comments contain the original total, even when
    # the teacher has edited the task since the submission was checked.
    comment = payload.get('comment')
    match = re.fullmatch(r'(\d+) из (\d+) тестов пройдено', comment) if isinstance(comment, str) else None
    return _pair(*map(int, match.groups())) if match else (None, None)


def submission_test_counts(submission):
    payload = feedback_payload(submission.checker_comment_raw)
    counts = checker_test_counts(payload)
    if counts[0] is None:
        counts = checker_test_counts({key: getattr(submission, key, None) for key in (
            'visible_tests_passed', 'visible_tests_total', 'hidden_tests_passed', 'hidden_tests_total')})
    return {'tests_passed': counts[0], 'tests_total': counts[1]}


def submission_verdict(submission):
    if submission.verdict in {'accepted', 'queued', 'surrendered'}:
        return submission.verdict
    payload = feedback_payload(submission.checker_comment_raw)
    payload['status'] = getattr(submission, 'checker_status_raw', None)
    return checker_error_type(payload) or submission.verdict


def diagnostic_text(payload):
    """Called only where all test data are public (including practice runs)."""
    details = payload.get('details')
    errors = []
    for detail in details if isinstance(details, list) else []:
        if isinstance(detail, dict):
            error = detail.get('error') or detail.get('stderr')
            if isinstance(error, str) and error.strip():
                errors.append(error.strip())
    return '\n\n'.join(errors[:3])[:4000] or None

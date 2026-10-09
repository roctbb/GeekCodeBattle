"""Visibility belongs to Battle; the checker still receives every test in order."""


def task_tests(task):
    config = task.config_json if task else None
    tests = config.get("tests", []) if isinstance(config, dict) else []
    return tests if isinstance(tests, list) else []


def is_hidden(test):
    return isinstance(test, dict) and bool(test.get("hidden", False))


def has_hidden_tests(task):
    return any(is_hidden(test) for test in task_tests(task))


def public_test(test):
    return {"input": str(test.get("input", "")), "expected": str(test.get("expected", ""))}


def _test_key(test):
    return str(test.get("input", "")), str(test.get("expected", ""))


def public_snapshot(snapshot, task):
    # Old snapshots can contain tests that were made hidden after the round began.
    # Match by content rather than index: the task may have been reordered since.
    hidden = {_test_key(test) for test in task_tests(task) if is_hidden(test)}
    tests = snapshot.get("public_tests", [])
    return {
        **snapshot,
        "public_tests": [public_test(test) for test in tests
                         if isinstance(test, dict) and not is_hidden(test)
                         and _test_key(test) not in hidden]
        if isinstance(tests, list) else [],
    }


def hidden_test_feedback(submission):
    # Checker comments/errors can echo hidden inputs, expected or actual output.
    # Only aggregate verdicts are safe to show for tasks with hidden tests.
    if submission is None:
        return None
    return {
        "accepted": "Все тесты пройдены.",
        "wrong_answer": "Не все тесты пройдены.",
        "internal_error": "Ошибка проверки решения.",
    }.get(submission.verdict)

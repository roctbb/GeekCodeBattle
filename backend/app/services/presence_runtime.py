from threading import Lock


_lock = Lock()
_online_users = set()


def set_online(user_id: str):
    if not user_id:
        return
    with _lock:
        _online_users.add(str(user_id))


def set_offline(user_id: str):
    if not user_id:
        return
    with _lock:
        _online_users.discard(str(user_id))


def is_online(user_id: str) -> bool:
    if not user_id:
        return False
    with _lock:
        return str(user_id) in _online_users

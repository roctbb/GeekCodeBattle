from celery import Celery


celery = Celery("geekcodebattle")


def init_celery(app):
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        timezone="UTC",
        enable_utc=True,
    )
    poll_seconds = max(1, int(app.config.get("ROUND_TIMEOUT_POLL_SECONDS", 2)))
    celery.conf.beat_schedule = {
        "tick-round-timeouts": {
            "task": "app.celery_tasks.tick_all_battles_timeouts_task",
            "schedule": poll_seconds,
        }
    }
    celery.conf.imports = ("app.celery_tasks",)

    class AppContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = AppContextTask
    return celery

from app import create_app
from app.celery_app import celery


app = create_app()


if __name__ == "__main__":
    celery.worker_main(["worker", "--loglevel=INFO"])

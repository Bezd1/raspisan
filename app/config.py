import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DATABASE = os.path.join(BASE_DIR, "instance", "schedule.db")

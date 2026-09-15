import os
class Config:
    SECRET_KEY=os.getenv("SECRET_KEY","dev-secret-change-me")
    DATABASE=os.path.join(os.path.dirname(os.path.dirname(__file__)),"instance","schedule.db")

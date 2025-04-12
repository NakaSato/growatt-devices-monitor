import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 's123o8uoipjhf89')
    DEBUG = os.getenv('DEBUG', True)
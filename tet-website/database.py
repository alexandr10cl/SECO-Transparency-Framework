from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')

# Fix #33: Add charset=utf8mb4 for emoji support (🚀💻🎉)
SQLALCHEMY_DATABASE_URI = \
    '{SGBD}://{user}:{passw}@{server}/{database}?charset=utf8mb4'.format(
        SGBD = os.getenv('SGBD'),
        user = os.getenv('USER'),
        passw = os.getenv('PASSW'),
        server = os.getenv('SERVER'),
        database = os.getenv('DATABASE')
    )

SQLALCHEMY_TRACK_MODIFICATIONS = False
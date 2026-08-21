from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')

# The DB user is read from DB_USER, not USER: on Linux/Mac the shell always
# exports USER (the OS login name), and load_dotenv() does not override vars
# that already exist in the environment - so USER=seco_dev in .env was silently
# ignored there, causing "Access denied for user '<login>'@'...' (1045)".
# The USER fallback keeps older .env files working; drop it once everyone has
# renamed the key.
# Fix #33: Add charset=utf8mb4 for emoji support (🚀💻🎉)
SQLALCHEMY_DATABASE_URI = \
    '{SGBD}://{user}:{passw}@{server}/{database}?charset=utf8mb4'.format(
        SGBD = os.getenv('SGBD'),
        user = os.getenv('DB_USER') or os.getenv('USER'),
        passw = os.getenv('PASSW'),
        server = os.getenv('SERVER'),
        database = os.getenv('DATABASE')
    )

SQLALCHEMY_TRACK_MODIFICATIONS = False
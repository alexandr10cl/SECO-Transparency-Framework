from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

# Load environment variables from .env file
load_dotenv()

# index.py reads this file with from_pyfile, which only imports UPPERCASE names -
# lowercase helpers below stay out of app.config. SECRET_KEY is deliberately NOT
# defined here: from_pyfile runs after app.config["SECRET_KEY"] is set, so a
# SECRET_KEY here would overwrite it (with None when the env var is missing).

# The DB user is read from DB_USER, not USER: on Linux/Mac the shell always
# exports USER (the OS login name), and load_dotenv() does not override vars
# that already exist in the environment - so USER=seco_dev in .env was silently
# ignored there, causing "Access denied for user '<login>'@'...' (1045)".
# The USER fallback keeps older .env files working; drop it once everyone has
# renamed the key.
_db_user = os.getenv('DB_USER') or os.getenv('USER') or ''
_db_passw = os.getenv('PASSW') or ''

# quote_plus on user and password only: SERVER carries "host:port" and DATABASE a
# bare name, both of which quoting would corrupt. A managed password can contain
# @, / or :, which break the SQLAlchemy URL parser.
# Fix #33: Add charset=utf8mb4 for emoji support (🚀💻🎉)
SQLALCHEMY_DATABASE_URI = \
    '{SGBD}://{user}:{passw}@{server}/{database}?charset=utf8mb4'.format(
        SGBD = os.getenv('SGBD'),
        user = quote_plus(_db_user),
        passw = quote_plus(_db_passw),
        server = os.getenv('SERVER'),
        database = os.getenv('DATABASE')
    )

SQLALCHEMY_TRACK_MODIFICATIONS = False

# pool_pre_ping discards connections the server closed on its wait_timeout. Without
# it those come back as error 2006, which the handlers in index.py turn into a 503
# the user sees. pool_recycle stays under the usual 300s idle window.
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 240,
    'pool_size': 5,
    'max_overflow': 10,
}

# Off by default: on Railway the app and the database talk over a private network
# already encrypted by WireGuard. The flag is here for an external database.
if (os.getenv('DB_SSL_REQUIRED') or 'false').strip().lower() in ('1', 'true', 'yes', 'on'):
    SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {
        'ssl_disabled': False,
        'ssl_verify_cert': True,
    }

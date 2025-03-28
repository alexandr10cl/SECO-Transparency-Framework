from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize the Flask app
app = Flask(__name__)
app.config.from_pyfile('database.py')

# Initialize the database
db = SQLAlchemy(app)

# Initialize the migration
migrate = Migrate(app, db) 

# Importing views
from views.index import *
from views.pages import *
from views.auth import *
from views.admin import *
from external.tasks import *

# Importing models
from models import *

# Importing func to init db
from models.database import init_db
init_db()

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
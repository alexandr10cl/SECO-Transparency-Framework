from app import app, db

def init_db():
    with app.app_context():
        db.create_all() 

init_db()
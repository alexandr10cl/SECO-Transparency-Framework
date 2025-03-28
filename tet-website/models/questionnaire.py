from app import db

class DeveloperQuestionnaire(db.Model):
    __tablename__ = 'developer_questionnaire'

    # Main Rows
    developer_questionnaire_id = db.Column(db.Integer, primary_key=True)
    academic_level = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(100), nullable=False)
    seco = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.String(1000), nullable=False)
    emotion = db.Column(db.Integer, nullable=False)

    # Foreign key to the user table
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    # Foreign key to the collection data table
    collected_data_id = db.Column(db.Integer, db.ForeignKey('collected_data.collected_data_id'), nullable=False, unique=True)

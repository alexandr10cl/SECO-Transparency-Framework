from app import db
from models.enums import AcademicLevel, PreviousExperience, SegmentType

class DeveloperQuestionnaire(db.Model):
    __tablename__ = 'developer_questionnaire'

    # Main Rows
    developer_questionnaire_id = db.Column(db.Integer, primary_key=True)
    academic_level = db.Column(db.Enum(AcademicLevel), nullable=False)
    previus_xp = db.Column(db.Enum(PreviousExperience), nullable=False)
    emotion = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.String(500), nullable=False)
    segment = db.Column(db.Enum(SegmentType), nullable=False)
    experience = db.Column(db.Integer, nullable=False)

    # Foreign key to the collection data table
    collected_data_id = db.Column(db.Integer, db.ForeignKey('collected_data.collected_data_id'), nullable=False, unique=True)

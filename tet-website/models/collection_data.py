from app import db

class CollectedData(db.Model):
    __tablename__ = 'collected_data'
    
    # Main Rows
    collected_data_id = db.Column(db.Integer, primary_key=True)
    seco_portal = db.Column(db.String(500), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    # Relationship with PerformedTask
    performed_tasks = db.relationship('PerformedTask',
                                    backref=db.backref('collected_data', lazy=True))
    
    # Relationship with DeveloperQuestionnaire
    developer_questionnaire = db.relationship('DeveloperQuestionnaire',
                                        backref=db.backref('collected_data', lazy=True, uselist=False),
                                        uselist=False)

    # Foreign key to the evaluation table
    evaluation_id = db.Column(db.BigInteger, db.ForeignKey('evaluation.evaluation_id'), nullable=False) 
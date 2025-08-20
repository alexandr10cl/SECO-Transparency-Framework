from index import db
from models.enums import NavigationType

class CollectedData(db.Model):
    __tablename__ = 'collected_data'
    
    # Main Rows
    collected_data_id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    cod = db.Column(db.String(100), nullable=False)
    sessionId = db.Column(db.Integer, nullable=False)


    # Relationship with PerformedTask
    performed_tasks = db.relationship('PerformedTask',
                                    backref=db.backref('collected_data', lazy=True))
    
    # Relationship with DeveloperQuestionnaire
    developer_questionnaire = db.relationship('DeveloperQuestionnaire',
                                        backref=db.backref('collected_data', lazy=True, uselist=False),
                                        uselist=False)
    
    # Rlationship with Navigation
    navigation = db.relationship('Navigation',
                                backref=db.backref('collected_data', lazy=True))
    
    # Relationship with Answer table
    answers = db.relationship('Answer',
                            backref=db.backref('collected_data', lazy=True))

    # Foreign key to the evaluation table
    evaluation_id = db.Column(db.BigInteger, db.ForeignKey('evaluation.evaluation_id'), nullable=False) 

class Navigation(db.Model):
    __tablename__ = 'navigation'

    # Primary Key
    navigation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Main Rows
    action = db.Column(db.Enum(NavigationType), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    # Foreign key to the task table
    task_id = db.Column(db.Integer, db.ForeignKey('task.task_id'), nullable=False)

    # Foreign key to the collected data table
    collected_data_id = db.Column(db.Integer, db.ForeignKey('collected_data.collected_data_id'), nullable=False)

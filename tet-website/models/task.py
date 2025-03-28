from .enums import PerformedTaskStatus
from app import db

class Task(db.Model):
    __tablename__ = 'task'
    
    # Main Rows
    task_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(1000), nullable=False)

    # Relationship with Question
    questions = db.relationship('Question',
                                backref=db.backref('tasks', lazy=True))

    # Relationship with Guideline
    guidelines = db.relationship('Guideline',
                                secondary='guideline_task',
                                back_populates='related_tasks')

class PerformedTask(db.Model):
    __tablename__ = 'performed_task'
    
    # Main Rows
    performed_task_id = db.Column(db.Integer, primary_key=True)
    initial_timestamp = db.Column(db.DateTime, nullable=False)
    final_timestamp = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(PerformedTaskStatus), nullable=False)

    # Relationship with Answer
    answers = db.relationship('Answer',
                            backref=db.backref('performed_task', lazy=True))

    # Foreign key to the collected data table
    collected_data_id = db.Column(db.Integer, db.ForeignKey('collected_data.collected_data_id'), nullable=False)

class Question(db.Model):
    __tablename__ = 'question'
    
    # Main Rows
    question_id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(1000), nullable=False)

    # Foreign key to the task table
    task_id = db.Column(db.Integer, db.ForeignKey('task.task_id'), nullable=False)

    # Relationship with Answer
    answers = db.relationship('Answer',
                            backref=db.backref('question', lazy=True))

class Answer(db.Model):
    __tablename__ = 'answer'
    
    # Main Rows
    answer_id = db.Column(db.Integer, primary_key=True)
    answer = db.Column(db.String(1000), nullable=False)

    # Foreign key to the performed task table
    performed_task_id = db.Column(db.Integer, db.ForeignKey('performed_task.performed_task_id'), nullable=False)

    # Foreign key to the question table
    question_id = db.Column(db.Integer, db.ForeignKey('question.question_id')) 
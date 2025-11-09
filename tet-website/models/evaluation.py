from index import db
from models import SECOType
from datetime import datetime

# Association Tables
evaluation_SECO_process = db.Table('evaluation_SECO_process',
    db.Column('evaluation_id', db.BigInteger, db.ForeignKey('evaluation.evaluation_id')),
    db.Column('seco_process_id', db.Integer, db.ForeignKey('seco_process.seco_process_id'))
)

class Evaluation(db.Model):
    __tablename__ = 'evaluation'
    __table_args__ = (
        db.UniqueConstraint(
            'name',
            'seco_portal',
            'seco_portal_url',
            'user_id',
            name='uq_evaluation_details'
        ),
    )

    # Main Rows
    evaluation_id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    seco_portal = db.Column(db.String(100), nullable=False)
    seco_portal_url = db.Column(db.String(500), nullable=False)
    seco_type = db.Column(db.Enum(SECOType, name="seco_type_enum"), nullable=False, index=True)
    manager_objective = db.Column(db.Text, nullable=True)  # Manager's main objective for this evaluation
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True, index=True)  # Timestamp for sorting
    
    # Foreign key to the user table
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    # Relationship with CollectedData
    collected_data = db.relationship('CollectedData',
                                    backref=db.backref('evaluation', lazy=True)) 
    
    # Relationship with SECO_process
    seco_processes = db.relationship('SECO_process',
                                    secondary=evaluation_SECO_process,
                                    back_populates='evaluations',
                                    overlaps='evaluation_seco_processes')

class EvaluationCriterionWheight(db.Model):
    __tablename__ = 'evaluation_ksc_weight'

    # Main Rows
    id = db.Column(db.BigInteger, primary_key=True)
    weight = db.Column(db.Integer, nullable=False)
    
    # Foregin key
    ksc_id = db.Column(db.Integer, db.ForeignKey('key_success_criterion.key_success_criterion_id'), nullable=False)
    evaluation_id = db.Column(db.BigInteger, db.ForeignKey('evaluation.evaluation_id'), nullable=False)

    # Relationship
    evaluation = db.relationship('Evaluation', backref=db.backref('ksc_weights', lazy=True))
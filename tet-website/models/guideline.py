from app import db
from models.evaluation import evaluation_SECO_process

# Association Tables
guideline_conditioning_factor = db.Table('guideline_conditioning_factor',
    db.Column('guideline_id', db.Integer, db.ForeignKey('guideline.guidelineID')),
    db.Column('conditioning_factor_transp_id', db.Integer, db.ForeignKey('conditioning_factor_transp.conditioning_factor_transp_id'))
)

guideline_dx_factor = db.Table('guideline_dx_factor',
    db.Column('guideline_id', db.Integer, db.ForeignKey('guideline.guidelineID')),
    db.Column('dx_factor_id', db.Integer, db.ForeignKey('dx_factor.dx_factor_id'))
)

guideline_seco_process = db.Table('guideline_seco_process',
    db.Column('guideline_id', db.Integer, db.ForeignKey('guideline.guidelineID')),
    db.Column('seco_process_id', db.Integer, db.ForeignKey('seco_process.seco_process_id'))
)

guideline_seco_dimension = db.Table('guideline_seco_dimension',
    db.Column('guideline_id', db.Integer, db.ForeignKey('guideline.guidelineID')),
    db.Column('seco_dimension_id', db.Integer, db.ForeignKey('seco_dimension.seco_dimension_id'))
)

guideline_task = db.Table('guideline_task',
    db.Column('guideline_id', db.Integer, db.ForeignKey('guideline.guidelineID')),
    db.Column('task_id', db.Integer, db.ForeignKey('task.task_id'))
)

class Guideline(db.Model):
    __tablename__ = 'guideline'
    
    # Main Rows
    guidelineID = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    
    # Relationship with Key_success_criterion
    key_success_criteria = db.relationship('Key_success_criterion', 
                                        backref=db.backref('guideline', lazy=True))
    
    # Relationship with Conditioning_factor_transp
    conditioning_factors = db.relationship('Conditioning_factor_transp',
                                        secondary=guideline_conditioning_factor,
                                        backref=db.backref('guidelines', lazy=True))
    
    # Relationship with DX_factor
    dx_factors = db.relationship('DX_factor',
                                secondary=guideline_dx_factor,
                                backref=db.backref('guidelines', lazy=True))
    
    # Relationship with SECO_process
    seco_processes = db.relationship('SECO_process',
                                    secondary=guideline_seco_process,
                                    backref=db.backref('guidelines', lazy=True))
    
    # Relationship with SECO_dimension
    seco_dimensions = db.relationship('SECO_dimension',
                                    secondary=guideline_seco_dimension,
                                    backref=db.backref('guidelines', lazy=True))
    
    # Relationship with Task
    related_tasks = db.relationship('Task',
                                    secondary=guideline_task,
                                    back_populates='guidelines')

class Conditioning_factor_transp(db.Model):
    __tablename__ = 'conditioning_factor_transp'

    # Main Rows
    conditioning_factor_transp_id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)

class DX_factor(db.Model):
    __tablename__ = 'dx_factor'

    # Main Rows
    dx_factor_id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False) 

class SECO_process(db.Model):
    __tablename__ = 'seco_process'

    # Main Rows
    seco_process_id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)

    # Relationship with Evaluation
    evaluations = db.relationship('Evaluation',
                                secondary=evaluation_SECO_process,
                                backref=db.backref('evaluation_seco_processes', lazy=True))

class SECO_dimension(db.Model):
    __tablename__ = 'seco_dimension'

    # Main Rows
    seco_dimension_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) 

class Key_success_criterion(db.Model):
    __tablename__ = 'key_success_criterion'

    # Main Rows
    key_success_criterion_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)

    # Relationship with Example
    examples = db.relationship('Example',
                            backref=db.backref('key_success_criteria', lazy=True))

    # Foreign key to the guideline table
    guideline_id = db.Column(db.Integer, db.ForeignKey('guideline.guidelineID'), nullable=False)

class Example(db.Model):
    __tablename__ = 'example'

    # Main Rows
    example_id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)

    # Foreign key to the key_success_criterion table
    key_success_criterion_id = db.Column(db.Integer, db.ForeignKey('key_success_criterion.key_success_criterion_id'), nullable=False)
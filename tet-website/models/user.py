from .enums import UserType
from app import db

class User(db.Model):
    __tablename__ = 'user'
    
    # Main Rows
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    passw = db.Column(db.String(100), nullable=False)

    # Discriminator to identify the user type
    type = db.Column(db.Enum(UserType), nullable=False)

    # Polymorphic identity for User
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': UserType.USER
    }

class Admin(User):
    # Polymorphic identity for Admin
    __mapper_args__ = {
        'polymorphic_identity': UserType.ADMIN
    }

class SECO_MANAGER(User):
    # Polymorphic identity for SECO_MANAGER
    __mapper_args__ = {
        'polymorphic_identity': UserType.SECO_MANAGER
    }
    
    # Relationship with Evaluation
    evaluations = db.relationship('Evaluation',
                                backref=db.backref('seco_manager', lazy=True))

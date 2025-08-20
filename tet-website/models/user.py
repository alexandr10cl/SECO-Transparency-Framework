from .enums import UserType
from index import db
import bcrypt

class User(db.Model):
    __tablename__ = 'user'
    
    # Main Rows
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    passw = db.Column(db.LargeBinary(60), nullable=False) # Password hash

    # Discriminator to identify the user type
    type = db.Column(db.Enum(UserType), nullable=False)
    
    # Email verification fields
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(255), nullable=True)
    
    # Creates password hash
    def set_password(self, password):
        self.passw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
    # Checks if the password is correct
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.passw)

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

from db import db
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import random

def save_profile_picture(file):
    upload_folder = os.path.join(os.getcwd(), 'Uploads')
    
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    filename = secure_filename(file.filename)
    
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    return file_path

def generate_unique_user_id():
    """Generate a unique 6-digit user ID."""
    while True:
        new_id = random.randint(100000, 999999)  
        if not User.query.filter_by(id=new_id).first():
            return new_id

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)  
    profession = db.Column(db.String(100), nullable=True) 
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, server_default=db.func.now())
    profile_picture = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)  
    last_login = db.Column(db.DateTime, nullable=True)  
    is_banned = db.Column(db.Boolean, default=False, nullable=False) 
    savings_goals = db.relationship('SavingsGoal', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def __init__(self, name, email, profession, password, profile_picture=None, is_admin=False, is_banned=False):
        self.id = generate_unique_user_id()  
        self.name = name
        self.email = email
        self.profession = profession  
        self.password = self._generate_password_hash(password)
        self.profile_picture = profile_picture
        self.is_admin = is_admin
        self.last_login = None  
        self.is_banned = is_banned  

    def _generate_password_hash(self, password):
        return generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "profession": self.profession,  
            "profilePicture": self.profile_picture,
            "isAdmin": self.is_admin,
            "last_login": self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None,
            "isBanned": self.is_banned
        }
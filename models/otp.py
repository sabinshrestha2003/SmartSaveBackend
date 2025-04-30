from db import db
import datetime
import random

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, email):
        self.email = email
        self.code = str(random.randint(100000, 999999))  
        self.created_at = datetime.datetime.utcnow()
        self.expires_at = self.created_at + datetime.timedelta(minutes=10) 

    def is_expired(self):
        return datetime.datetime.utcnow() > self.expires_at

    def is_valid(self, code):
        return not self.is_expired() and self.code == code
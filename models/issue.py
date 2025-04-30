from db import db
import datetime

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False) 
    description = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "date": self.date.strftime('%Y-%m-%d %H:%M:%S'),
            "user_id": self.user_id
        }
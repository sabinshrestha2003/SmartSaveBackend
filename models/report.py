from db import db
import datetime

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "date": self.date.strftime('%Y-%m-%d %H:%M:%S'),
            "user_id": self.user_id
        }
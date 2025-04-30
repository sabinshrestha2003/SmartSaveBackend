from db import db
from datetime import datetime

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='Custom')  
    currency = db.Column(db.String(10), default='INR')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    icon_url = db.Column(db.String(255))

    members = db.relationship('GroupMember', backref='group', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'creator_id': self.creator_id,
            'type': self.type,
            'currency': self.currency,
            'created_at': self.created_at.isoformat(),
            'icon_url': self.icon_url,
            'members': [m.user_id for m in self.members]
        }
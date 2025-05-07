from db import db
from datetime import datetime

class Group(db.Model):
    __tablename__ = 'groups'

    my_row_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    id = db.Column(db.Integer, nullable=False)  
    name = db.Column(db.String(100), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='Custom')
    currency = db.Column(db.String(10), nullable=True, default='INR')
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    icon_url = db.Column(db.String(255), nullable=True)

    members = db.relationship('GroupMember', backref='group', lazy=True, cascade='all, delete')

    def __init__(self, id, name, creator_id, type='Custom', currency='USD', created_at=None, icon_url=None):
        self.id = id
        self.name = name
        self.creator_id = creator_id
        self.type = type
        self.currency = currency
        self.created_at = created_at or datetime.utcnow()
        self.icon_url = icon_url

    def to_dict(self):
        return {
            'my_row_id': self.my_row_id, 
            'id': self.id,
            'name': self.name,
            'creator_id': self.creator_id,
            'type': self.type,
            'currency': self.currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'icon_url': self.icon_url,
            'members': [m.user_id for m in self.members]
        }
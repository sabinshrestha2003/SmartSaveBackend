from db import db
from datetime import datetime

class BillSplit(db.Model):
    __tablename__ = 'bill_splits'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    category = db.Column(db.String(50))
    photo_url = db.Column(db.String(255))
    notes = db.Column(db.Text)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    flagged = db.Column(db.Boolean, default=False)  
    
    participants = db.relationship('SplitParticipant', backref='bill_split', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'total_amount': float(self.total_amount),
            'creator_id': self.creator_id,
            'group_id': self.group_id,
            'category': self.category,
            'photo_url': self.photo_url,
            'notes': self.notes,
            'is_recurring': self.is_recurring,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'flagged': self.flagged,
            'participants': [p.to_dict() for p in self.participants]
        }
from db import db
from datetime import datetime

class BillSplit(db.Model):
    __tablename__ = 'bill_splits'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    currency = db.Column(db.String(10), nullable=True, default='INR')
    status = db.Column(db.String(20), nullable=True, default='active')
    photo_url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_recurring = db.Column(db.Boolean, default=False, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    flagged = db.Column(db.Boolean, default=False, nullable=False)
    
    participants = db.relationship('SplitParticipant', backref='bill_split', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'total_amount': float(self.total_amount),
            'creator_id': self.creator_id,
            'group_id': self.group_id,
            'category': self.category,
            'currency': self.currency,
            'status': self.status,
            'photo_url': self.photo_url,
            'notes': self.notes,
            'is_recurring': self.is_recurring,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'flagged': self.flagged,
            'participants': [p.to_dict() for p in self.participants]
        }
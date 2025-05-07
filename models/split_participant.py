from db import db

class SplitParticipant(db.Model):
    __tablename__ = 'split_participants'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bill_split_id = db.Column(db.Integer, db.ForeignKey('bill_splits.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    share_amount = db.Column(db.Float, default=0, nullable=True)
    paid_amount = db.Column(db.Float, default=0, nullable=True)
    split_method = db.Column(db.String(20), default='equal', nullable=True)
    split_value = db.Column(db.Float, default=1, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'bill_split_id': self.bill_split_id,
            'user_id': self.user_id,
            'share_amount': float(self.share_amount) if self.share_amount is not None else 0,
            'paid_amount': float(self.paid_amount) if self.paid_amount is not None else 0,
            'split_method': self.split_method,
            'split_value': float(self.split_value) if self.split_value is not None else 1,
            'status': self.status
        }
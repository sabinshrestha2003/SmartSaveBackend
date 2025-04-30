from db import db

class SplitParticipant(db.Model):
    __tablename__ = 'split_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_split_id = db.Column(db.Integer, db.ForeignKey('bill_splits.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    share_amount = db.Column(db.Float, default=0.0)
    split_method = db.Column(db.String(20), default='equal')  
    split_value = db.Column(db.Float, default=1.0)  

    def to_dict(self):
        return {
            'id': self.id,
            'bill_split_id': self.bill_split_id,
            'user_id': self.user_id,
            'paid_amount': self.paid_amount,
            'share_amount': self.share_amount,
            'split_method': self.split_method,
            'split_value': self.split_value
        }
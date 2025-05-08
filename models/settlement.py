from datetime import datetime
from db import db
from models.bill_split import BillSplit

class Settlement(db.Model):
    __tablename__ = 'settlements'

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    bill_split_id = db.Column(db.Integer, db.ForeignKey('bill_splits.id'), nullable=True)
    method = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    settled_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, from_user_id: int, to_user_id: int, amount: float, bill_split_id: int = None,
                 method: str = None, notes: str = None):
        self.validate_inputs(from_user_id, to_user_id, amount, bill_split_id)
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.amount = amount
        self.bill_split_id = bill_split_id
        self.method = method
        self.notes = notes

    def validate_inputs(self, from_user_id, to_user_id, amount, bill_split_id):
        if not isinstance(from_user_id, int) or from_user_id <= 0:
            raise ValueError("From user ID must be a positive integer.")
        if not isinstance(to_user_id, int) or to_user_id <= 0:
            raise ValueError("To user ID must be a positive integer.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Amount must be a positive number.")
        if bill_split_id is not None:
            if not isinstance(bill_split_id, int) or bill_split_id <= 0:
                raise ValueError("Bill split ID must be a positive integer.")
            bill_split = BillSplit.query.get(bill_split_id)
            if not bill_split:
                raise ValueError(f"Bill split with ID {bill_split_id} does not exist.")

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'from_user_id': self.from_user_id,
            'to_user_id': self.to_user_id,
            'amount': float(self.amount),
            'bill_split_id': self.bill_split_id,
            'method': self.method,
            'notes': self.notes,
            'settled_at': self.settled_at.strftime('%Y-%m-%d %H:%M:%S') if self.settled_at else None
        }
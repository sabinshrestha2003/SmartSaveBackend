from db import db
import datetime

class Transaction(db.Model):
    __tablename__ = 'transactions'

    my_row_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    id = db.Column(db.Integer, nullable=False)  # Required, not primary key
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    account = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text, nullable=True)
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flagged = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, id, amount, category, account, note, date, type, user_id, flagged=False):
        self.id = id  # Include id in initialization
        self.amount = amount
        self.category = category
        self.account = account
        self.note = note
        self.date = date
        self.type = type
        self.user_id = user_id
        self.flagged = flagged

    def to_dict(self):
        return {
            "my_row_id": self.my_row_id,  
            "id": self.id,
            "amount": self.amount,
            "category": self.category,
            "account": self.account,
            "note": self.note,
            "date": self.date.strftime('%Y-%m-%d'),
            "type": self.type,
            "user_id": self.user_id,
            "flagged": self.flagged
        }
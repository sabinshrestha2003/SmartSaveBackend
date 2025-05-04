from datetime import date
from db import db

class SavingsGoal(db.Model):
    __tablename__ = 'savings_goals'

    my_row_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    id = db.Column(db.Integer, nullable=False)  
    name = db.Column(db.String(100), nullable=False)
    target = db.Column(db.Float, nullable=False)
    progress = db.Column(db.Float, default=0.0, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable per schema

    def __init__(self, id: int, name: str, target: float, deadline: date, user_id: int, progress: float = 0.0):
        self.validate_inputs(name, target, deadline, progress)
        self.id = id
        self.name = name
        self.target = target
        self.progress = progress
        self.deadline = deadline
        self.user_id = user_id

    def validate_inputs(self, name, target, deadline, progress):
        if not name or not isinstance(name, str) or len(name.strip()) == 0:
            raise ValueError("Name must be a non-empty string.")
        if not isinstance(target, (int, float)) or target <= 0:
            raise ValueError("Target must be a positive number.")
        if not isinstance(progress, (int, float)) or progress < 0:
            raise ValueError("Progress must be a non-negative number.")
        if not isinstance(deadline, date) or deadline < date.today():
            raise ValueError("Deadline cannot be in the past.")

    def to_dict(self) -> dict:
        return {
            "my_row_id": self.my_row_id,  
            "id": self.id,
            "name": self.name,
            "target": self.target,
            "progress": self.progress,
            "deadline": self.deadline.strftime('%Y-%m-%d'),
            "user_id": self.user_id
        }
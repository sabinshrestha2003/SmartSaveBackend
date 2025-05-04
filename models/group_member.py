from db import db

class GroupMember(db.Model):
    __tablename__ = 'group_members'

    my_row_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    id = db.Column(db.Integer, nullable=False)  # NOT NULL
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __init__(self, id: int, group_id: int, user_id: int):
        self.validate_inputs(group_id, user_id)
        self.id = id
        self.group_id = group_id
        self.user_id = user_id

    def validate_inputs(self, group_id, user_id):
        if not isinstance(group_id, int) or group_id <= 0:
            raise ValueError("Group ID must be a positive integer.")
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("User ID must be a positive integer.")

    def to_dict(self) -> dict:
        return {
            'my_row_id': self.my_row_id,  # Optional
            'id': self.id,
            'group_id': self.group_id,
            'user_id': self.user_id
        }
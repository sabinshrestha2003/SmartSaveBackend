from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import db
from models.group import Group
from models.group_member import GroupMember
from models.bill_split import BillSplit
from models.split_participant import SplitParticipant
from models.settlement import Settlement
from models.user import User
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bill_split_bp = Blueprint('bill_split', __name__)

def user_required():
    def wrapper(fn):
        @jwt_required()
        def decorator(*args, **kwargs):
            user_id = get_jwt_identity()
            logger.debug(f"Extracted user_id from JWT: {user_id} (type: {type(user_id)})")
            return fn(user_id, *args, **kwargs)
        return decorator
    return wrapper

def get_next_group_id():
    """Generate a unique group ID by incrementing the max id."""
    max_id = db.session.query(db.func.max(Group.id)).scalar()
    return (max_id or 0) + 1

@bill_split_bp.route('/groups', methods=['POST'], endpoint='create_group')
@user_required()
def create_group(current_user_id):
    try:
        data = request.get_json()
        name = data.get('name')
        if not name:
            raise ValueError("Group name is required")
        type_ = data.get('type', 'Custom')
        if type_ not in ['Trip', 'Home', 'Event', 'Custom']:
            raise ValueError("Invalid group type. Use: Trip, Home, Event, Custom")
        currency = data.get('currency', 'USD')
        icon_url = data.get('icon_url')
        members = data.get('members', [])

        for member_id in members:
            if not User.query.get(int(member_id)):
                raise ValueError(f"User with ID {member_id} does not exist")

        group = Group(
            id=get_next_group_id(),
            name=name,
            creator_id=current_user_id,
            type=type_,
            currency=currency,
            icon_url=icon_url
        )
        db.session.add(group)
        db.session.flush()

        creator_member = GroupMember(
            group_id=group.id,
            user_id=current_user_id
        )
        db.session.add(creator_member)

        for member_id in members:
            if int(member_id) != current_user_id:
                member = GroupMember(
                    group_id=group.id,
                    user_id=int(member_id)
                )
                db.session.add(member)

        db.session.commit()
        logger.info(f"Group created: id={group.id}, name={name}, creator_id={current_user_id}")
        return jsonify({"message": "Group created", "group": group.to_dict()}), 201
    except ValueError as ve:
        db.session.rollback()
        logger.error(f"ValueError in create_group: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Exception in create_group: {str(e)}")
        return jsonify({"error": f"Failed to create group: {str(e)}"}), 500

@bill_split_bp.route('/users/search', methods=['GET'], endpoint='search_users')
@user_required()
def search_users(current_user_id):
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"users": []}), 200

        users = []
        if '@' in query and '.' in query:
            user = User.query.filter_by(email=query.lower()).first()
            if user and user.id != current_user_id:
                users = [user]
        else:
            try:
                query_id = int(query)
                user = User.query.filter_by(id=query_id).first()
                if user and user.id != current_user_id:
                    users = [user]
            except ValueError:
                users = User.query.filter(
                    User.name.ilike(f'%{query}%')
                ).limit(10).all()

        user_list = [
            {
                "id": str(u.id),
                "name": u.name,
                "email": u.email,
                "profilePicture": u.profile_picture
            }
            for u in users if u.id != current_user_id
        ]
        logger.debug(f"Search users query: {query}, found: {len(user_list)} users")
        return jsonify({"users": user_list}), 200
    except Exception as e:
        logger.error(f"Exception in search_users: {str(e)}")
        return jsonify({"error": f"Failed to search users: {str(e)}"}), 500

@bill_split_bp.route('/bill_splits/<int:bill_split_id>', methods=['DELETE'], endpoint='delete_bill_split')
@user_required()
def delete_bill_split(current_user_id, bill_split_id):
    try:
        bill_split = BillSplit.query.get_or_404(bill_split_id)
        if bill_split.creator_id != current_user_id:
            return jsonify({"error": "Only the creator can delete this bill split"}), 403

        SplitParticipant.query.filter_by(bill_split_id=bill_split_id).delete()
        Settlement.query.filter_by(bill_split_id=bill_split_id).delete()
        db.session.delete(bill_split)
        db.session.commit()

        logger.info(f"Bill split deleted: id={bill_split_id}, user_id={current_user_id}")
        return jsonify({"message": "Bill split deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Exception in delete_bill_split: {str(e)}")
        return jsonify({"error": f"Failed to delete bill split: {str(e)}"}), 500

@bill_split_bp.route('/groups', methods=['GET'], endpoint='get_user_groups')
@user_required()
def get_user_groups(current_user_id):
    try:
        groups = Group.query.join(GroupMember).filter(
            GroupMember.user_id == current_user_id,
            Group.deleted_at.is_(None)
        ).all()
        group_ids = [group.id for group in groups]
        logger.debug(f"Fetched {len(groups)} groups for user_id: {current_user_id}, group_ids: {group_ids}")
        return jsonify({"groups": [group.to_dict() for group in groups]}), 200
    except Exception as e:
        logger.error(f"Exception in get_user_groups: {str(e)}")
        return jsonify({"error": f"Failed to fetch groups: {str(e)}"}), 500

@bill_split_bp.route('/bill_splits', methods=['POST'], endpoint='create_bill_split')
@user_required()
def create_bill_split(current_user_id):
    try:
        data = request.get_json()
        name = data.get('name')
        if not name:
            raise ValueError("Bill name is required")
        total_amount = data.get('total_amount')
        if total_amount is None or total_amount <= 0:
            raise ValueError("Total amount must be a positive number")

        creator = User.query.get(current_user_id)
        if not creator:
            raise ValueError(f"Creator with ID {current_user_id} does not exist")

        group_id = data.get('group_id')
        category = data.get('category')
        currency = data.get('currency', 'INR')
        status = data.get('status', 'active')
        photo_url = data.get('photo_url')
        notes = data.get('notes')
        is_recurring = data.get('is_recurring', False)
        participants = data.get('participants')

        if not participants or not isinstance(participants, list):
            raise ValueError("Participants must be a non-empty list")

        num_participants = len(participants)
        default_share_amount = float(total_amount) / num_participants

        total_percentage = 0
        for participant in participants:
            user_id = participant.get('user_id')
            if not user_id:
                raise ValueError("Each participant must have a user_id")

            if 'paid_amount' not in participant:
                participant['paid_amount'] = float(total_amount) if int(user_id) == current_user_id else 0.0
            elif participant['paid_amount'] < 0:
                raise ValueError(f"Paid amount for user {user_id} cannot be negative")

            if 'share_amount' not in participant:
                participant['share_amount'] = default_share_amount
            elif participant['share_amount'] < 0:
                raise ValueError(f"Share amount for user {user_id} cannot be negative")

            split_method = participant.get('split_method', 'equal')
            if split_method not in ['equal', 'exact', 'percentage']:
                raise ValueError(f"Invalid split method for user {user_id}: {split_method}")

            if 'split_value' not in participant:
                participant['split_value'] = 1.0
            elif participant['split_value'] < 0:
                raise ValueError(f"Split value for user {user_id} cannot be negative")

            if split_method == 'percentage':
                total_percentage += float(participant['split_value'])

        if total_percentage > 0 and abs(total_percentage - 100.0) > 0.01:
            raise ValueError(f"Total percentage split values must sum to 100%, got {total_percentage}%")

        total_paid = sum(float(p.get('paid_amount', 0)) for p in participants)
        if abs(total_paid - float(total_amount)) > 0.01:
            raise ValueError(f"Sum of amounts paid ({total_paid:.2f}) does not match total amount ({total_amount:.2f})")

        total_owed = sum(float(p.get('share_amount', 0)) for p in participants)
        if abs(total_owed - float(total_amount)) > 0.01:
            raise ValueError(f"Sum of amounts owed ({total_owed:.2f}) does not match total amount ({total_amount:.2f})")

        bill_split = BillSplit(
            name=name,
            total_amount=float(total_amount),
            creator_id=current_user_id,
            group_id=group_id,
            category=category,
            currency=currency,
            status=status,
            photo_url=photo_url,
            notes=notes,
            is_recurring=is_recurring
        )
        db.session.add(bill_split)
        db.session.flush()

        with db.session.no_autoflush:
            for participant in participants:
                user_id = participant.get('user_id')
                paid_amount = float(participant.get('paid_amount', 0))
                share_amount = float(participant.get('share_amount', 0))
                split_method = participant.get('split_method', 'equal')
                split_value = float(participant.get('split_value', 1))

                if not User.query.get(int(user_id)):
                    raise ValueError(f"User with ID {user_id} does not exist")

                split_participant = SplitParticipant(
                    bill_split_id=bill_split.id,
                    user_id=int(user_id),
                    paid_amount=paid_amount,
                    share_amount=share_amount,
                    split_method=split_method,
                    split_value=split_value,
                    status='pending'
                )
                db.session.add(split_participant)

            if group_id:
                group = Group.query.get(group_id)
                if not group:
                    raise ValueError(f"Group with ID {group_id} does not exist")
                group_members = {gm.user_id for gm in GroupMember.query.filter_by(group_id=group_id).all()}
                participant_ids = {int(p['user_id']) for p in participants}
                if not participant_ids.issubset(group_members):
                    raise ValueError("All participants must be members of the selected group")

        db.session.commit()

        bill_split_dict = bill_split.to_dict()
        bill_split_dict['participants'] = [
            {
                'user_id': p.user_id,
                'name': User.query.get(p.user_id).name,
                'share_amount': p.share_amount,
                'paid_amount': p.paid_amount,
                'split_method': p.split_method,
                'split_value': p.split_value,
                'status': p.status
            } for p in bill_split.participants
        ]
        bill_split_dict['group_name'] = group.name if group_id and group else None
        bill_split_dict['creator_name'] = creator.name
        logger.info(f"Bill split created: id={bill_split.id}, user_id={current_user_id}")
        return jsonify({"message": "Bill split created", "bill_split": bill_split_dict}), 201
    except ValueError as ve:
        db.session.rollback()
        logger.error(f"ValueError in create_bill_split: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Exception in create_bill_split: {str(e)}")
        return jsonify({"error": f"Failed to create bill split: {str(e)}"}), 500

@bill_split_bp.route('/bill_splits', methods=['GET'], endpoint='get_user_bill_splits')
@user_required()
def get_user_bill_splits(current_user_id):
    try:
        bill_splits = BillSplit.query.join(SplitParticipant).filter(
            SplitParticipant.user_id == current_user_id
        ).all()
        logger.debug(f"Fetched {len(bill_splits)} bill splits for user_id: {current_user_id}")
        return jsonify({"bill_splits": [bs.to_dict() for bs in bill_splits]}), 200
    except Exception as e:
        logger.error(f"Exception in get_user_bill_splits: {str(e)}")
        return jsonify({"error": f"Failed to fetch bill splits: {str(e)}"}), 500

@bill_split_bp.route('/bill_splits/<int:bill_split_id>', methods=['PUT'], endpoint='update_bill_split')
@user_required()
def update_bill_split(current_user_id, bill_split_id):
    try:
        bill_split = BillSplit.query.get_or_404(bill_split_id)

        participant = SplitParticipant.query.filter_by(
            bill_split_id=bill_split_id, user_id=current_user_id
        ).first()
        if not participant:
            return jsonify({"error": "You are not a participant in this bill split"}), 403

        data = request.get_json()
        participants = data.get('participants')
        if not participants or not isinstance(participants, list):
            raise ValueError("Participants must be a non-empty list")

        for participant_data in participants:
            user_id = participant_data.get('user_id')
            if not user_id:
                raise ValueError("Each participant must have a user_id")

            split_participant = SplitParticipant.query.filter_by(
                bill_split_id=bill_split_id, user_id=int(user_id)
            ).first()
            if not split_participant:
                raise ValueError(f"Participant with user_id {user_id} not found in this bill split")

            if 'paid_amount' in participant_data:
                split_participant.paid_amount = float(participant_data['paid_amount'])
            if 'share_amount' in participant_data:
                split_participant.share_amount = float(participant_data['share_amount'])
            if 'status' in participant_data:
                split_participant.status = participant_data['status']

        if 'name' in data:
            bill_split.name = data['name']
        if 'total_amount' in data:
            bill_split.total_amount = float(data['total_amount'])
        if 'group_id' in data:
            bill_split.group_id = data['group_id']
        if 'category' in data:
            bill_split.category = data['category']
        if 'currency' in data:
            bill_split.currency = data['currency']
        if 'status' in data:
            bill_split.status = data['status']
        if 'photo_url' in data:
            bill_split.photo_url = data['photo_url']
        if 'notes' in data:
            bill_split.notes = data['notes']
        if 'is_recurring' in data:
            bill_split.is_recurring = data['is_recurring']

        db.session.commit()
        logger.info(f"Bill split updated: id={bill_split_id}, user_id={current_user_id}")
        return jsonify({"message": "Bill split updated", "bill_split": bill_split.to_dict()}), 200
    except ValueError as ve:
        db.session.rollback()
        logger.error(f"ValueError in update_bill_split: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Exception in update_bill_split: {str(e)}")
        return jsonify({"error": f"Failed to update bill split: {str(e)}"}), 500

@bill_split_bp.route('/settlements', methods=['GET'], endpoint='get_user_settlements')
@user_required()
def get_user_settlements(current_user_id):
    try:
        settlements = Settlement.query.filter(
            (Settlement.from_user_id == current_user_id) | (Settlement.to_user_id == current_user_id)
        ).all()
        formatted_settlements = []
        for s in settlements:
            s_dict = s.to_dict()
            s_dict['split_id'] = s_dict.pop('bill_split_id')
            s_dict['payer_id'] = s_dict.pop('from_user_id')
            s_dict['payee_id'] = s_dict.pop('to_user_id')
            formatted_settlements.append(s_dict)
        logger.debug(f"Fetched {len(formatted_settlements)} settlements for user_id: {current_user_id}")
        return jsonify({"settlements": formatted_settlements}), 200
    except Exception as e:
        logger.error(f"Exception in get_user_settlements: {str(e)}")
        return jsonify({"error": f"Failed to fetch settlements: {str(e)}"}), 500

@bill_split_bp.route('/settlements', methods=['POST'], endpoint='create_settlement')
@user_required()
def create_settlement(current_user_id):
    try:
        data = request.get_json()
        payer_id = data.get('payer_id')
        payee_id = data.get('payee_id')
        amount = data.get('amount')
        split_id = data.get('split_id')
        split_name = data.get('split_name')
        timestamp = data.get('timestamp')

        if not payer_id or not payee_id:
            raise ValueError("Payer and payee user IDs are required")
        if amount is None or amount <= 0:
            raise ValueError("Amount must be a positive number")
        if str(payer_id) != str(current_user_id):
            raise ValueError("You can only create settlements as the payer")

        if not User.query.get(int(payer_id)):
            raise ValueError(f"Payer user with ID {payer_id} does not exist")
        if not User.query.get(int(payee_id)):
            raise ValueError(f"Payee user with ID {payee_id} does not exist")

        if split_id:
            bill_split = BillSplit.query.get(int(split_id))
            if not bill_split:
                raise ValueError(f"Bill split with ID {split_id} does not exist")

        settlement = Settlement(
            from_user_id=int(payer_id),
            to_user_id=int(payee_id),
            amount=float(amount),
            bill_split_id=int(split_id) if split_id else None,
            method=data.get('method'),
            notes=data.get('notes')
        )
        db.session.add(settlement)
        db.session.commit()

        settlement_dict = settlement.to_dict()
        settlement_dict['split_id'] = settlement_dict.pop('bill_split_id')
        settlement_dict['payer_id'] = settlement_dict.pop('from_user_id')
        settlement_dict['payee_id'] = settlement_dict.pop('to_user_id')
        settlement_dict['timestamp'] = timestamp
        logger.info(f"Settlement created: id={settlement.id}, user_id={current_user_id}")
        return jsonify({"message": "Settlement created", "settlement": settlement_dict}), 201
    except ValueError as ve:
        db.session.rollback()
        logger.error(f"ValueError in create_settlement: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Exception in create_settlement: {str(e)}")
        return jsonify({"error": f"Failed to create settlement: {str(e)}"}), 500

@bill_split_bp.route('/groups/<int:group_id>', methods=['DELETE'], endpoint='delete_group')
@user_required()
def delete_group(current_user_id, group_id):
    try:
        group = Group.query.filter_by(id=group_id).first()
        if not group:
            logger.warning(f"Group {group_id} not found")
            return jsonify({"error": "Group not found"}), 404
        logger.debug(f"Deleting group {group_id}, creator_id: {group.creator_id} (type: {type(group.creator_id)}), user_id: {current_user_id} (type: {type(current_user_id)})")
        if int(group.creator_id) != int(current_user_id):
            logger.warning(f"User {current_user_id} is not creator of group {group_id}, creator_id: {group.creator_id}")
            return jsonify({"error": "Only the group creator can delete the group"}), 403

        bill_splits = BillSplit.query.filter_by(group_id=group_id).all()
        for bill_split in bill_splits:
            SplitParticipant.query.filter_by(bill_split_id=bill_split.id).delete()
            Settlement.query.filter_by(bill_split_id=bill_split.id).delete()
            db.session.delete(bill_split)

        GroupMember.query.filter_by(group_id=group_id).delete()
        group.deleted_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Group soft-deleted: id={group_id}, user_id={current_user_id}, deleted_at={group.deleted_at}")
        return jsonify({"message": "Group deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Exception in delete_group: {str(e)}")
        return jsonify({"error": f"Failed to delete group: {str(e)}"}), 500

@bill_split_bp.route('/groups/<int:group_id>', methods=['GET'], endpoint='get_group')
@user_required()
def get_group(current_user_id, group_id):
    try:
        group = Group.query.filter_by(id=group_id).first()
        if not group or group.deleted_at is not None:
            logger.warning(f"Group {group_id} not found or soft-deleted")
            return jsonify({"error": "Group not found"}), 404

        is_member = GroupMember.query.filter_by(group_id=group_id, user_id=current_user_id).first()
        if not is_member and group.creator_id != current_user_id:
            logger.warning(f"User {current_user_id} is not a member of group {group_id}")
            return jsonify({"error": "You are not a member of this group"}), 403

        members = [gm.user_id for gm in GroupMember.query.filter_by(group_id=group_id).all()]
        
        group_dict = group.to_dict()
        group_dict['members'] = members
        logger.debug(f"Fetched group {group_id} for user_id: {current_user_id}, group_dict: {group_dict}")
        return jsonify({"group": group_dict}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Exception in get_group: {str(e)}")
        return jsonify({"error": f"Failed to fetch group: {str(e)}"}), 500

@bill_split_bp.route('/groups/<int:group_id>', methods=['PUT'], endpoint='update_group')
@user_required()
def update_group(current_user_id, group_id):
    try:
        group = Group.query.filter_by(id=group_id).first()
        if not group or group.deleted_at is not None:
            logger.warning(f"Group {group_id} not found or soft-deleted")
            return jsonify({"error": "Group not found"}), 404
        if group.creator_id != current_user_id:
            logger.warning(f"User {current_user_id} is not creator of group {group_id}")
            return jsonify({"error": "Only the group creator can edit the group"}), 403

        data = request.get_json()
        name = data.get('name')
        if not name:
            raise ValueError("Group name is required")

        type_ = data.get('type', group.type)
        if type_ not in ['Trip', 'Home', 'Event', 'Custom']:
            raise ValueError("Invalid group type. Use: Trip, Home, Event, Custom")

        members = data.get('members', [])

        for member_id in members:
            if not User.query.get(int(member_id)):
                raise ValueError(f"User with ID {member_id} does not exist")

        group.name = name
        group.type = type_

        current_members = GroupMember.query.filter_by(group_id=group.id).all()
        current_member_ids = {m.user_id for m in current_members}
        new_member_ids = set(map(int, members))

        for member_id in new_member_ids - current_member_ids:
            if member_id != current_user_id:
                new_member = GroupMember(
                    group_id=group.id,
                    user_id=member_id
                )
                db.session.add(new_member)

        for member in current_members:
            if member.user_id not in new_member_ids and member.user_id != current_user_id:
                db.session.delete(member)

        db.session.commit()
        logger.info(f"Group updated: id={group_id}, user_id={current_user_id}")
        return jsonify({"message": "Group updated", "group": group.to_dict()}), 201
    except ValueError as ve:
        db.session.rollback()
        logger.error(f"ValueError in update_group: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Exception in update_group: {str(e)}")
        return jsonify({"error": f"Failed to update group: {str(e)}"}), 500
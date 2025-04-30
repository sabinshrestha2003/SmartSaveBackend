from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from models.issue import Issue
from models.bill_split import BillSplit
from models.split_participant import SplitParticipant
from models.group import Group
from models.group_member import GroupMember
from db import db
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os

admin_bp = Blueprint('admin', __name__)

def admin_required():
    def wrapper(fn):
        @jwt_required()
        def decorator(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or not user.is_admin:
                return jsonify({"error": "Admin access required"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def send_email(to_email, subject, body):
    """Send an email using Gmail SMTP."""
    gmail_address = os.getenv('GMAIL_ADDRESS')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = gmail_address
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error for {to_email}: {e}")
        return False
    
@admin_bp.route('/users/count', methods=['GET'], endpoint='get_user_count')
@admin_required()
def get_user_count():
    try:
        count = User.query.filter(
            User.email.isnot(None),
            User.is_banned == False
        ).count()
        print(f"User count fetched: {count}")  
        return jsonify({"count": count}), 200
    except Exception as e:
        print(f"Error fetching user count: {str(e)}") 
        return jsonify({"error": f"Failed to fetch user count: {str(e)}"}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'], endpoint='get_user')
@admin_required()
def get_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        user_dict = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "isAdmin": user.is_admin,
            "isBanned": user.is_banned,
            "joinedDate": user.created_at.strftime('%Y-%m-%d') if user.created_at else None,
            "last_login": user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            "isActive": (datetime.utcnow() - user.last_login).days <= 30 if user.last_login else False,
            "profilePicture": user.profile_picture
        }
        return jsonify(user_dict), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch user: {str(e)}"}), 500

@admin_bp.route('/users', methods=['GET'], endpoint='get_all_users')
@admin_required()
def get_all_users():
    try:
        current_date = datetime.utcnow()
        users = User.query.all()
        active_users = 0
        inactive_users = 0
        banned_users = 0
        user_list = []
        for user in users:
            days_since_last_login = (current_date - user.last_login).days if user.last_login else float('inf')
            is_active = days_since_last_login <= 30 if user.last_login else False
            is_banned = user.is_banned
            
            if is_active:
                active_users += 1
            else:
                inactive_users += 1
            if is_banned:
                banned_users += 1
            
            user_dict = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "isAdmin": user.is_admin,
                "isBanned": is_banned,
                "joinedDate": user.created_at.strftime('%Y-%m-%d') if user.created_at else None,
                "last_login": user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
                "isActive": is_active,
            }
            user_list.append(user_dict)
        
        return jsonify({
            "users": user_list,
            "totalActiveUsers": active_users,
            "totalInactiveUsers": inactive_users,
            "totalBannedUsers": banned_users
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch users: {str(e)}"}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'], endpoint='update_user')
@admin_required()
def update_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        data = request.get_json()
        user.name = data.get('name', user.name)
        user.email = data.get('email', user.email).strip().lower()
        user.is_admin = data.get('isAdmin', user.is_admin)
        user.is_banned = data.get('isBanned', user.is_banned)
        if 'last_login' in data:
            user.last_login = datetime.strptime(data['last_login'], '%Y-%m-%d %H:%M:%S') if data['last_login'] else None
        db.session.commit()
        return jsonify({"message": "User updated", "user": user.to_dict()}), 200
    except ValueError as ve:
        db.session.rollback()
        return jsonify({"error": f"Invalid date format: {str(ve)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update user: {str(e)}"}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'], endpoint='delete_user')
@admin_required()
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500

@admin_bp.route('/issues', methods=['GET'], endpoint='get_pending_issues')
@admin_required()
def get_pending_issues():
    try:
        issues = Issue.query.all()
        disputes = [issue.to_dict() for issue in issues if issue.type == 'dispute']
        complaints = [issue.to_dict() for issue in issues if issue.type == 'complaint']
        return jsonify({
            "disputes": disputes,
            "complaints": complaints
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch issues: {str(e)}"}), 500

@admin_bp.route('/bill_splits', methods=['GET'], endpoint='get_all_bill_splits')
@admin_required()
def get_all_bill_splits():
    try:
        bill_splits = BillSplit.query.all()
        bill_split_list = []
        for split in bill_splits:
            split_dict = split.to_dict()
            participants = SplitParticipant.query.filter_by(bill_split_id=split.id).all()
            split_dict['participants'] = [
                {
                    'user_id': p.user_id,
                    'name': User.query.get(p.user_id).name if User.query.get(p.user_id) else 'Unknown',
                    'share_amount': float(p.share_amount),
                    'paid_amount': float(p.paid_amount),
                    'split_method': p.split_method,
                    'split_value': float(p.split_value)
                } for p in participants
            ]
            split_dict['flagged'] = split.flagged or False
            bill_split_list.append(split_dict)
        return jsonify({"bill_splits": bill_split_list}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch bill splits: {str(e)}"}), 500

@admin_bp.route('/bill_splits/<int:bill_split_id>/flag', methods=['PATCH'], endpoint='flag_bill_split')
@admin_required()
def flag_bill_split(bill_split_id):
    try:
        bill_split = BillSplit.query.get_or_404(bill_split_id)
        data = request.get_json()
        flagged = data.get('flagged')
        if flagged is None:
            return jsonify({"error": "Flagged status is required"}), 400
        bill_split.flagged = bool(flagged)
        db.session.commit()
        return jsonify({"message": "Bill split flag status updated", "bill_split": bill_split.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update bill split flag status: {str(e)}"}), 500

@admin_bp.route('/groups', methods=['GET'], endpoint='get_all_groups')
@admin_required()
def get_all_groups():
    try:
        groups = Group.query.all()
        group_list = []
        for group in groups:
            group_dict = group.to_dict()
            group_dict['member_count'] = len(group.members)
            creator = User.query.get(group.creator_id)
            group_dict['creator_name'] = creator.name if creator else 'Unknown'
            group_list.append(group_dict)
        return jsonify({"groups": group_list}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch groups: {str(e)}"}), 500

@admin_bp.route('/groups/<int:group_id>', methods=['GET'], endpoint='get_group_details')
@admin_required()
def get_group_details(group_id):
    try:
        group = Group.query.get_or_404(group_id)
        group_dict = group.to_dict()
        members = [
            {
                'user_id': m.user_id,
                'name': User.query.get(m.user_id).name if User.query.get(m.user_id) else 'Unknown'
            } for m in group.members
        ]
        bill_splits = BillSplit.query.filter_by(group_id=group_id).all()
        bill_split_list = []
        for split in bill_splits:
            split_dict = split.to_dict()
            participants = SplitParticipant.query.filter_by(bill_split_id=split.id).all()
            split_dict['participants'] = [
                {
                    'user_id': p.user_id,
                    'name': User.query.get(p.user_id).name if User.query.get(p.user_id) else 'Unknown',
                    'share_amount': float(p.share_amount),
                    'paid_amount': float(p.paid_amount),
                    'split_method': p.split_method,
                    'split_value': float(p.split_value)
                } for p in participants
            ]
            split_dict['flagged'] = split.flagged or False
            bill_split_list.append(split_dict)
        group_dict['members'] = members
        group_dict['bill_splits'] = bill_split_list
        return jsonify({"group": group_dict}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch group details: {str(e)}"}), 500

@admin_bp.route('/send-message', methods=['POST'])
@admin_required()
def send_message_to_all_users():
    try:
        data = request.get_json()
        subject = data.get('subject')
        message = data.get('message')

        if not subject or not message:
            return jsonify({"error": "Subject and message are required"}), 400

        if len(message) > 10000:
            return jsonify({"error": "Message too long (max 10,000 characters)"}), 400

        users = User.query.filter(
            User.email.isnot(None),
            User.is_banned == False
        ).all()

        if not users:
            return jsonify({"error": "No eligible users found"}), 404

        failed_emails = []
        success_count = 0
        
        for user in users:
            try:
                success = send_email(
                    user.email, 
                    f"SmartSave: {subject}", 
                    f"Dear {user.name},\n\n{message}\n\n- SmartSave Team"
                )
                if success:
                    success_count += 1
                else:
                    failed_emails.append(user.email)
            except Exception as e:
                print(f"Error sending to {user.email}: {str(e)}")
                failed_emails.append(user.email)

        response = {
            "success_count": success_count,
            "failed_count": len(failed_emails),
            "total_attempted": len(users)
        }
        
        if failed_emails:
            response["failed_emails"] = failed_emails
            return jsonify(response), 207
            
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to send message: {str(e)}"}), 500
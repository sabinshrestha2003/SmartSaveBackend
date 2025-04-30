from flask import Blueprint, request, jsonify, current_app
from models.user import User, save_profile_picture
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import db
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from helpers.utils import is_strong_password

user_bp = Blueprint('user', __name__)

@user_bp.route('', methods=['GET'])
@jwt_required()
def get_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    return jsonify({"success": True, "user": user.to_dict()}), 200

@user_bp.route('/upload-profile-picture', methods=['POST'])
@jwt_required()
def upload_profile_picture():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if 'profilePicture' not in request.files:
        return jsonify({"success": False, "message": "No file part."}), 400

    file = request.files['profilePicture']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file."}), 400

    file_path = save_profile_picture(file)
    if not file_path:
        return jsonify({"success": False, "message": "Failed to save file."}), 500

    file_url = f"{request.host_url}uploads/{os.path.basename(file_path)}"
    
    user.profile_picture = file_url
    db.session.commit()

    return jsonify({"success": True, "url": file_url}), 200

@user_bp.route('', methods=['PUT'])
@jwt_required()
def update_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        user.email = data['email'].strip().lower()
    if 'profession' in data:  
        user.profession = data['profession']

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated successfully."}), 200

@user_bp.route('/search', methods=['GET'])
@jwt_required()
def search_users():
    query_id = request.args.get('id', type=str)
    if not query_id:
        return jsonify({'success': False, 'message': 'User ID is required'}), 400

    try:
        # Search for users whose ID starts with the query string
        users = User.query.filter(User.id.like(f'{query_id}%')).all()
        if not users:
            return jsonify({'success': True, 'users': []}), 200

        user_data = [{'id': user.id, 'name': user.name} for user in users]
        return jsonify({'success': True, 'users': user_data}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error searching users: {str(e)}'}), 500

@user_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({"success": False, "message": "Current and new passwords are required."}), 400

    if not check_password_hash(user.password, current_password):
        return jsonify({"success": False, "message": "Incorrect current password."}), 401

    if not is_strong_password(new_password):
        return jsonify({
            "success": False,
            "message": "New password must be at least 8 characters long, contain an uppercase letter, and a number."
        }), 400

    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()

    return jsonify({"success": True, "message": "Password changed successfully."}), 200
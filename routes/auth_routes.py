from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models.user import User
from models.otp import OTP
from db import db
from datetime import datetime
from helpers.utils import is_valid_email, is_strong_password
import os
import smtplib
from email.mime.text import MIMEText

auth_bp = Blueprint('auth', __name__)

def send_otp(email, otp_code):
    """Send OTP to the given email using Gmail SMTP."""
    gmail_address = os.getenv('GMAIL_ADDRESS')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
    
    msg = MIMEText(f"Your SmartSave verification code is {otp_code}")
    msg['Subject'] = 'SmartSave OTP Verification'
    msg['From'] = gmail_address
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp_route():
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email is required."}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email format."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered."}), 409

    OTP.query.filter_by(email=email).delete()
    db.session.commit()

    otp = OTP(email=email)
    db.session.add(otp)
    db.session.commit()

    if send_otp(email, otp.code):
        return jsonify({"success": True, "message": "OTP sent successfully."}), 200
    else:
        db.session.delete(otp)
        db.session.commit()
        return jsonify({"success": False, "message": "Failed to send OTP."}), 500

@auth_bp.route('/send-reset-otp', methods=['POST'])
def send_reset_otp():
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email is required."}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email format."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"success": False, "message": "Email not found."}), 404

    OTP.query.filter_by(email=email).delete()
    db.session.commit()

    otp = OTP(email=email)
    db.session.add(otp)
    db.session.commit()

    if send_otp(email, otp.code):
        return jsonify({"success": True, "message": "OTP sent successfully."}), 200
    else:
        db.session.delete(otp)
        db.session.commit()
        return jsonify({"success": False, "message": "Failed to send OTP."}), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()

    if not email or not code:
        return jsonify({"success": False, "message": "Email and OTP code are required."}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email format."}), 400

    otp = OTP.query.filter_by(email=email).order_by(OTP.created_at.desc()).first()
    if not otp:
        return jsonify({"success": False, "message": "No OTP found for this email."}), 404

    if otp.is_valid(code):
        db.session.delete(otp)
        db.session.commit()
        return jsonify({"success": True, "message": "OTP verified successfully."}), 200
    else:
        return jsonify({"success": False, "message": "Invalid or expired OTP."}), 400

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '')

    if not email or not code or not new_password:
        return jsonify({"success": False, "message": "Email, OTP code, and new password are required."}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email format."}), 400

    if not is_strong_password(new_password):
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters long, contain an uppercase letter, and a number."
        }), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"success": False, "message": "Email not found."}), 404

    otp = OTP.query.filter_by(email=email).order_by(OTP.created_at.desc()).first()
    if not otp or not otp.is_valid(code):
        return jsonify({"success": False, "message": "Invalid or expired OTP."}), 400

    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.delete(otp)
    db.session.commit()

    return jsonify({"success": True, "message": "Password reset successfully."}), 200

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email format."}), 400

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        user.last_login = datetime.utcnow()
        db.session.commit()
        token = create_access_token(identity=user.id)
        return jsonify({"success": True, "token": token}), 200

    return jsonify({"success": False, "message": "Invalid credentials."}), 401

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    profession = data.get('profession', '').strip()
    password = data.get('password', '')
    otp_code = data.get('otp_code', '').strip()

    if not name or not email or not profession or not password or not otp_code:
        return jsonify({"success": False, "message": "All fields and OTP code are required."}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email format."}), 400
    if not is_strong_password(password):
        return jsonify({"success": False, "message": "Password must be at least 8 characters long, contain an uppercase letter, and a number."}), 400
    if len(profession) > 100:
        return jsonify({"success": False, "message": "Profession must be less than 100 characters."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already exists."}), 409

    otp = OTP.query.filter_by(email=email).order_by(OTP.created_at.desc()).first()
    if not otp or not otp.is_valid(otp_code):
        return jsonify({"success": False, "message": "Invalid or expired OTP."}), 400

    new_user = User(name=name, email=email, profession=profession, password=password)
    db.session.delete(otp)
    db.session.add(new_user)
    db.session.commit()

    token = create_access_token(identity=new_user.id)
    return jsonify({"success": True, "token": token, "user": new_user.to_dict()}), 201

@auth_bp.route('/logout', methods=['POST'])
@jwt_required(optional=True)
def logout():
    user_id = get_jwt_identity()
    if user_id:
        print(f"User {user_id} logged out on server")
    return jsonify({"success": True, "message": "Logged out successfully."}), 200
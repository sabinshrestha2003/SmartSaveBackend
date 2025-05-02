import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from db import db
from routes import register_routes
from config import Config
from models.user import User
from models.savings_goal import SavingsGoal
from models.group import Group
from models.group_member import GroupMember
from models.bill_split import BillSplit
from models.split_participant import SplitParticipant
from models.settlement import Settlement
from models.otp import OTP
from dotenv import load_dotenv

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = app.config['TOKEN_EXPIRY_DAYS'] * 86400

    UPLOAD_FOLDER = os.path.join('/tmp', 'Uploads')  # Use /tmp for containers
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    app.config['GMAIL_ADDRESS'] = os.getenv('GMAIL_ADDRESS')
    app.config['GMAIL_APP_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD')

    db.init_app(app)
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.route('/api/ping', methods=['GET'])
    def ping():
        return jsonify({'message': 'pong'}), 200

    register_routes(app)

    @app.route('/Uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Database initialization failed: {e}")
            # Optionally, continue without crashing
            # raise e  # Uncomment to crash for debugging

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8000))
    app.run(host="0.0.0.0", port=port)
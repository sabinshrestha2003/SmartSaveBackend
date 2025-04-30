import os
from flask import Flask, send_from_directory
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

    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'Uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    app.config['GMAIL_ADDRESS'] = os.getenv('GMAIL_ADDRESS')
    app.config['GMAIL_APP_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD')

    db.init_app(app)
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    register_routes(app)

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
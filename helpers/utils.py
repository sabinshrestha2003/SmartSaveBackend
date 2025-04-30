import re
import jwt
from datetime import datetime, timedelta
from flask import current_app

def is_valid_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(regex, email))

def is_strong_password(password):
    return (
        len(password) >= 8 and 
        re.search(r'[A-Z]', password) and 
        re.search(r'[a-z]', password) and 
        re.search(r'[0-9]', password)
    )

def generate_token(user_id):
    expiry = datetime.utcnow() + timedelta(days=7)  # Token will expire in 7 days
    payload = {'user_id': user_id, 'exp': expiry}
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def decode_token(token):
    try:
        # Decode the token and check its validity.
        decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        print("Decoded Token:", decoded)  # Debugging step to see the decoded payload
        return decoded
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired."}
    except jwt.InvalidTokenError as e:
        print("Invalid Token Error:", e)  # Log the error for debugging
        return {"error": "Invalid token."}

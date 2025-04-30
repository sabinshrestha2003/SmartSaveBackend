from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.transaction import Transaction
from models.user import User
from db import db
from routes.admin_routes import admin_required
from datetime import datetime, timedelta

transaction_bp = Blueprint('transaction', __name__)

@transaction_bp.route('/income', methods=['POST'])
@jwt_required()
def add_income():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        amount = data.get('amount')
        category = data.get('category')
        account = data.get('account')
        note = data.get('note', '')
        date = data.get('date')

        if not all([amount, category, account, date]):
            return jsonify({"error": "Missing required fields: amount, category, account, and date are mandatory"}), 400

        new_transaction = Transaction(
            amount=amount,
            category=category,
            account=account,
            note=note,
            date=date,
            type='income',
            user_id=user_id,
            flagged=data.get('flagged', False)  
        )
        db.session.add(new_transaction)
        db.session.commit()

        return jsonify({"message": "Income transaction added successfully", "transaction": new_transaction.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to add income transaction: {str(e)}"}), 500

@transaction_bp.route('/expense', methods=['POST'])
@jwt_required()
def add_expense():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        amount = data.get('amount')
        category = data.get('category')
        account = data.get('account')
        note = data.get('note', '')
        date = data.get('date')

        if not all([amount, category, account, date]):
            return jsonify({"error": "Missing required fields: amount, category, account, and date are mandatory"}), 400

        new_transaction = Transaction(
            amount=amount,
            category=category,
            account=account,
            note=note,
            date=date,
            type='expense',
            user_id=user_id,
            flagged=data.get('flagged', False)  
        )
        db.session.add(new_transaction)
        db.session.commit()

        return jsonify({"message": "Expense transaction added successfully", "transaction": new_transaction.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to add expense transaction: {str(e)}"}), 500

@transaction_bp.route('', methods=['GET'])
@jwt_required()
def get_all_transactions():
    try:
        user_id = get_jwt_identity()
        transactions = Transaction.query.filter_by(user_id=user_id).all()
        transaction_list = [txn.to_dict() for txn in transactions]  
        return jsonify(transaction_list), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch transactions: {str(e)}"}), 500

@transaction_bp.route('/<int:transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id):
    try:
        user_id = get_jwt_identity()
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        return jsonify(transaction.to_dict()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch transaction: {str(e)}"}), 500

@transaction_bp.route('/<int:transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        if 'amount' in data:
            transaction.amount = data['amount']
        if 'category' in data:
            transaction.category = data['category']
        if 'account' in data:
            transaction.account = data['account']
        if 'note' in data:
            transaction.note = data['note']
        if 'date' in data:
            transaction.date = data['date']
        if 'type' in data:
            transaction.type = data['type']
        if 'flagged' in data:
            transaction.flagged = data.get('flagged', False)  

        db.session.commit()

        return jsonify({"message": "Transaction updated", "transaction": transaction.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update transaction: {str(e)}"}), 500

@transaction_bp.route('/<int:transaction_id>', methods=['DELETE']) 
@jwt_required()
def delete_transaction(transaction_id):
    try:
        user_id = get_jwt_identity()
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        db.session.delete(transaction)
        db.session.commit()

        return jsonify({"message": "Transaction deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete transaction: {str(e)}"}), 500

@transaction_bp.route('/all', methods=['GET'], endpoint='get_all_admin_transactions')  
@admin_required()
def get_all_admin_transactions():
    try:
        transactions = Transaction.query.all()
        transaction_list = [txn.to_dict() for txn in transactions]  
        return jsonify(transaction_list), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch all transactions: {str(e)}"}), 500

@transaction_bp.route('/summary', methods=['GET'], endpoint='get_transaction_summary')
@admin_required()
def get_transaction_summary():
    try:
        transactions = Transaction.query.all()
        current_date = datetime.utcnow()

        daily_transactions = len([t for t in transactions if t.date.date() == current_date.date()])
        weekly_transactions = len([t for t in transactions if (current_date - datetime.combine(t.date, datetime.min.time())).days <= 7])
        monthly_transactions = len([t for t in transactions if (current_date - datetime.combine(t.date, datetime.min.time())).days <= 30])

        return jsonify({
            "dailyTransactions": daily_transactions,
            "weeklyTransactions": weekly_transactions,
            "monthlyTransactions": monthly_transactions
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@transaction_bp.route('/overview', methods=['GET'], endpoint='get_transaction_overview')
@admin_required()
def get_transaction_overview():
    try:
        total_transactions = Transaction.query.count()
        savings = Transaction.query.filter_by(type='income').with_entities(db.func.sum(Transaction.amount)).scalar() or 0
        expenses = Transaction.query.filter_by(type='expense').with_entities(db.func.sum(Transaction.amount)).scalar() or 0

        return jsonify({
            "totalTransactions": total_transactions,
            "totalSavings": float(savings),  
            "totalExpenses": float(expenses)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@transaction_bp.route('/recent', methods=['GET'], endpoint='get_recent_activities')
@admin_required()
def get_recent_activities():
    try:
        recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(10).all()
        transactions_list = [t.to_dict() for t in recent_transactions]  

        new_users = User.query.order_by(User.created_at.desc()).limit(10).all()
        users_list = [{
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "joinedDate": u.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "last_login": u.last_login.strftime('%Y-%m-%d %H:%M:%S') if u.last_login else None,
            "isBanned": u.is_banned  
        } for u in new_users]

        flagged_transactions = Transaction.query.filter_by(flagged=True).order_by(Transaction.date.desc()).limit(5).all()
        flagged_list = [t.to_dict() for t in flagged_transactions]  

        return jsonify({
            "recentTransactions": transactions_list,
            "newUserSignups": users_list,
            "flaggedTransactions": flagged_list
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
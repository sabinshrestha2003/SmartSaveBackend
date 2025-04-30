from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required
from routes.admin_routes import admin_required
from models.transaction import Transaction
from models.user import User
from models.savings_goal import SavingsGoal
from db import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import csv
from io import StringIO, BytesIO
from openpyxl import Workbook

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/financial', methods=['GET'], endpoint='get_financial_reports')
@jwt_required()
@admin_required()
def get_financial_reports():
    try:
        report_type = request.args.get('type', 'spendingTrends')
        six_months_ago = datetime.now() - timedelta(days=180)

        if report_type == 'spendingTrends':
            # Category-based spending trends
            data = db.session.query(
                Transaction.category,
                func.sum(Transaction.amount).label('total_amount')  
            ).filter(
                Transaction.type == 'expense',
                Transaction.date >= six_months_ago
            ).group_by(
                Transaction.category
            ).all()
            result = [{"category": cat, "amount": float(amt)} for cat, amt in data]

        elif report_type == 'savings':
            data = db.session.query(
                User.profession,
                func.sum(SavingsGoal.progress).label('total_savings')
            ).join(
                SavingsGoal, User.id == SavingsGoal.user_id
            ).filter(
                SavingsGoal.deadline >= six_months_ago
            ).group_by(
                User.profession
            ).all()
            result = [{"profession": prof if prof else "Unknown", "amount": float(sav)} for prof, sav in data]

        elif report_type == 'transactionVolume':
            data = db.session.query(
                Transaction.category,
                func.count(Transaction.id).label('count')
            ).filter(
                Transaction.date >= six_months_ago
            ).group_by(
                Transaction.category
            ).all()
            result = [{"category": cat, "count": int(cnt)} for cat, cnt in data]

        elif report_type == 'professionSpending':
            data = db.session.query(
                User.profession,
                func.sum(Transaction.amount).label('total_spent')
            ).join(
                Transaction, User.id == Transaction.user_id
            ).filter(
                Transaction.type == 'expense',
                Transaction.date >= six_months_ago
            ).group_by(
                User.profession
            ).all()
            result = [{"profession": prof if prof else "Unknown", "amount": float(spent)} for prof, spent in data]

        else:
            return jsonify({"error": "Invalid report type"}), 400

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch financial reports: {str(e)}"}), 500

@analytics_bp.route('/engagement', methods=['GET'], endpoint='get_user_engagement')
@jwt_required()
@admin_required()
def get_user_engagement():
    try:
        total_users = User.query.count()
        active_users = User.query.filter(
            User.last_login >= (datetime.utcnow() - timedelta(days=30))
        ).count()
        new_signups = User.query.filter(
            User.created_at >= (datetime.utcnow() - timedelta(days=30))
        ).count()
        retention_rate = f"{(active_users / total_users * 100):.1f}%" if total_users > 0 else "0%"

        engagement_data = [
            {"metric": "Total Users", "value": total_users},
            {"metric": "Active Users", "value": active_users},
            {"metric": "New Signups (Last 30 Days)", "value": new_signups},
            {"metric": "Retention Rate", "value": retention_rate},
        ]
        return jsonify(engagement_data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch engagement data: {str(e)}"}), 500

@analytics_bp.route('/export', methods=['POST'], endpoint='export_data')
@jwt_required()
@admin_required()
def export_data():
    try:
        data = request.get_json()
        export_type = data.get('type')
        format = data.get('format')
        report_type = data.get('report_type', 'spendingTrends') if export_type == 'financial' else None

        if export_type not in ['financial', 'engagement'] or format not in ['csv', 'excel']:
            return jsonify({"error": "Invalid type or format"}), 400

        if export_type == 'financial':
            if report_type == 'spendingTrends':
                transactions = db.session.query(Transaction).filter(
                    Transaction.type == 'expense',
                    Transaction.date >= datetime.now() - timedelta(days=180)
                ).all()
                export_data = [{"category": t.category, "amount": float(t.amount)} for t in transactions]
            elif report_type == 'savings':
                savings = db.session.query(User, SavingsGoal).join(
                    SavingsGoal, User.id == SavingsGoal.user_id
                ).filter(
                    SavingsGoal.deadline >= datetime.now() - timedelta(days=180)
                ).all()
                export_data = [{"profession": u.profession if u.profession else "Unknown", "amount": float(s.progress)} for u, s in savings]
            elif report_type == 'transactionVolume':
                transactions = db.session.query(Transaction).filter(
                    Transaction.date >= datetime.now() - timedelta(days=180)
                ).all()
                export_data = [{"category": t.category, "count": 1} for t in transactions]
            elif report_type == 'professionSpending':
                transactions = db.session.query(User, Transaction).join(
                    Transaction, User.id == Transaction.user_id
                ).filter(
                    Transaction.type == 'expense',
                    Transaction.date >= datetime.now() - timedelta(days=180)
                ).all()
                export_data = [{"profession": u.profession if u.profession else "Unknown", "amount": float(t.amount)} for u, t in transactions]
            else:
                return jsonify({"error": "Invalid financial report type"}), 400

        else:  # engagement
            total_users = User.query.count()
            active_users = User.query.filter(
                User.last_login >= (datetime.utcnow() - timedelta(days=30))
            ).count()
            new_signups = User.query.filter(
                User.created_at >= (datetime.utcnow() - timedelta(days=30))
            ).count()
            retention_rate = f"{(active_users / total_users * 100):.1f}%" if total_users > 0 else "0%"
            export_data = [
                {"metric": "Total Users", "value": total_users},
                {"metric": "Active Users", "value": active_users},
                {"metric": "New Signups", "value": new_signups},
                {"metric": "Retention Rate", "value": retention_rate},
            ]

        if format == 'csv':
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
            output.seek(0)
            return send_file(
                BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f"{export_type}_{report_type if export_type == 'financial' else ''}_report.csv"
            )

        elif format == 'excel':
            wb = Workbook()
            ws = wb.active
            ws.title = f"{export_type}_{report_type}" if export_type == 'financial' else export_type
            headers = list(export_data[0].keys())
            ws.append(headers)
            for row in export_data:
                ws.append(list(row.values()))
            excel_io = BytesIO()
            wb.save(excel_io)
            excel_io.seek(0)
            return send_file(
                excel_io,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f"{export_type}_{report_type if export_type == 'financial' else ''}_report.xlsx"
            )

    except Exception as e:
        return jsonify({"error": f"Failed to export data: {str(e)}"}), 500
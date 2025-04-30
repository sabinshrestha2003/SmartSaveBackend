from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.savings_goal import SavingsGoal
from db import db
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
import calendar

savings_goal_bp = Blueprint('savings_goal', __name__)

@savings_goal_bp.route('/goals', methods=['POST'])
@jwt_required()
def add_savings_goal():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        name = data.get('name')
        target = data.get('target')
        deadline = data.get('deadline')
        progress = data.get('progress', 0.0)

        if not all([name, target, deadline]):
            return jsonify({"error": "Missing required fields"}), 400

        target = float(target)
        if target < 0:
            return jsonify({"error": "Target must be non-negative"}), 400

        deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
        if deadline_date < date.today():
            return jsonify({"error": "Deadline cannot be in the past"}), 400

        progress = float(progress)
        if progress < 0:
            return jsonify({"error": "Progress must be non-negative"}), 400

        new_goal = SavingsGoal(name=name, target=target, deadline=deadline_date, progress=progress, user_id=user_id)
        db.session.add(new_goal)
        db.session.commit()

        return jsonify({"message": "Savings goal added", "goal": new_goal.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to add savings goal: {str(e)}"}), 500

@savings_goal_bp.route('/goals', methods=['GET'])
@jwt_required()
def get_all_savings_goals():
    try:
        user_id = get_jwt_identity()
        query_user_id = request.args.get('user_id', user_id, type=int)
        goals = SavingsGoal.query.filter_by(user_id=query_user_id).all()
        return jsonify([goal.to_dict() for goal in goals]), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch savings goals: {str(e)}"}), 500

@savings_goal_bp.route('/goals/<int:goal_id>', methods=['PUT'])
@jwt_required()
def update_savings_goal(goal_id):
    try:
        user_id = get_jwt_identity()
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            return jsonify({"error": "Goal not found or unauthorized"}), 404

        data = request.get_json()
        goal.name = data.get('name', goal.name)
        goal.target = float(data.get('target', goal.target))
        goal.progress = float(data.get('progress', goal.progress))

        deadline = data.get('deadline')
        if deadline:
            goal.deadline = datetime.strptime(deadline, '%Y-%m-%d').date()

        db.session.commit()
        return jsonify({"message": "Goal updated", "goal": goal.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update goal: {str(e)}"}), 500

@savings_goal_bp.route('/goals/<int:goal_id>', methods=['DELETE'])
@jwt_required()
def delete_savings_goal(goal_id):
    try:
        user_id = get_jwt_identity()
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            return jsonify({"error": "Goal not found or unauthorized"}), 404

        db.session.delete(goal)
        db.session.commit()
        return jsonify({"message": "Goal deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete goal: {str(e)}"}), 500

@savings_goal_bp.route('/goals/trends', methods=['GET'])
@jwt_required()
def get_savings_trends():
    try:
        user_id = get_jwt_identity()
        period = request.args.get('period', 'monthly')

        six_months_ago = datetime.now() - timedelta(days=180)

        if period == 'weekly':
            trends_data = db.session.query(
                extract('year', SavingsGoal.deadline).label('year'),
                extract('week', SavingsGoal.deadline).label('week'),
                func.sum(SavingsGoal.progress).label('total_savings')
            ).filter(
                SavingsGoal.deadline >= six_months_ago,
                SavingsGoal.user_id == user_id
            ).group_by(
                'year', 'week'
            ).order_by(
                'year', 'week'
            ).all()
            labels = [f'Week {week}' for year, week, _ in trends_data]
            monthly_savings = [float(total) for _, _, total in trends_data]

        elif period == 'yearly':
            trends_data = db.session.query(
                extract('year', SavingsGoal.deadline).label('year'),
                func.sum(SavingsGoal.progress).label('total_savings')
            ).filter(
                SavingsGoal.user_id == user_id
            ).group_by(
                'year'
            ).order_by(
                'year'
            ).all()
            labels = [f'Year {year}' for year, _ in trends_data]
            monthly_savings = [float(total) for _, total in trends_data]

        else:  # Monthly
            trends_data = db.session.query(
                extract('year', SavingsGoal.deadline).label('year'),
                extract('month', SavingsGoal.deadline).label('month'),
                func.sum(SavingsGoal.progress).label('total_savings')
            ).filter(
                SavingsGoal.deadline >= six_months_ago,
                SavingsGoal.user_id == user_id
            ).group_by(
                'year', 'month'
            ).order_by(
                'year', 'month'
            ).all()
            labels = [f"{calendar.month_abbr[month]} {year}" for year, month, _ in trends_data]
            monthly_savings = [float(total) for _, _, total in trends_data]

        total_savings = sum(monthly_savings)
        monthly_avg = total_savings / len(monthly_savings) if monthly_savings else 0
        highest_month = labels[monthly_savings.index(max(monthly_savings))] if monthly_savings else ''

        trends_data = {
            "total_savings": total_savings,
            "monthly_avg": monthly_avg,
            "highest_month": highest_month,
            "monthly_data": monthly_savings,
            "labels": labels
        }

        return jsonify(trends_data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch trends: {str(e)}"}), 500

@savings_goal_bp.route('/goals/total-target', methods=['GET'])
@jwt_required()
def get_total_target():
    try:
        user_id = get_jwt_identity()
        total_target = db.session.query(func.sum(SavingsGoal.target)).filter(SavingsGoal.user_id == user_id).scalar() or 0.0
        return jsonify({"total_target": float(total_target)}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch total target: {str(e)}"}), 500

@savings_goal_bp.route('/goals/streak', methods=['GET'])
@jwt_required()
def get_savings_streak():
    try:
        user_id = get_jwt_identity()
        goals = SavingsGoal.query.filter_by(user_id=user_id).order_by(SavingsGoal.deadline).all()

        streak = 0
        current_streak = 0
        previous_month = None

        for goal in goals:
            goal_month = goal.deadline.strftime('%Y-%m')
            if goal.progress > 0:
                if goal_month != previous_month:
                    current_streak += 1
                    previous_month = goal_month
                streak = max(streak, current_streak)
            else:
                current_streak = 0
                previous_month = None

        return jsonify({"streak": streak}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch streak: {str(e)}"}), 500
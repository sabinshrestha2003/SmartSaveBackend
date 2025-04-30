from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.transaction_routes import transaction_bp
from routes.savings_goal_routes import savings_goal_bp
from routes.admin_routes import admin_bp 
from routes.analytics_routes import analytics_bp  
from routes.bill_split_routes import bill_split_bp  

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(transaction_bp, url_prefix='/api/transactions')
    app.register_blueprint(savings_goal_bp, url_prefix='/api')  
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(bill_split_bp, url_prefix='/api/splits')  
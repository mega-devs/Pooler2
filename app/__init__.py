from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_config import Config
from flask_swagger_ui import get_swaggerui_blueprint

# Initialize SQLAlchemy and Flask-Migrate
db = SQLAlchemy()
migrate = Migrate()

# Configure Swagger UI
SWAGGER_URL = '/api/docs'
API_URL = '/static/json/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "app"
    }
)


def create_app(config_class=Config):
    # Create Flask app instance
    app = Flask(__name__)


    @app.route('/async')
    async def async_route():
        return jsonify(message="This is an async route")
    # Load configuration from Config class
    app.config.from_object(config_class)


    # Import and register API blueprint
    from .routes import api as api_blueprint
    app.register_blueprint(api_blueprint)

    # Register Swagger UI blueprint
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    return app

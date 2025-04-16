from flask import Flask
from flask_bootstrap import Bootstrap5
from app.config import Config

bootstrap = Bootstrap5()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    bootstrap.init_app(app)
    
    # Register blueprints by importing the routes module
    from app.main import routes as main_routes
    app.register_blueprint(main_routes.bp)
    
    from app.content import routes as content_routes
    app.register_blueprint(content_routes.bp, url_prefix='/content')
    
    from app.comics import routes as comics_routes
    app.register_blueprint(comics_routes.bp, url_prefix='/comics')
    
    @app.route('/test')
    def test_page():
        return 'The app is working!'
    
    return app 
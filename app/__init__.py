from flask import Flask
from flask_bootstrap import Bootstrap5
from app.config import Config

bootstrap = Bootstrap5()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    bootstrap.init_app(app)
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.content import bp as content_bp
    app.register_blueprint(content_bp, url_prefix='/content')
    
    from app.comics import bp as comics_bp
    app.register_blueprint(comics_bp, url_prefix='/comics')
    
    @app.route('/test')
    def test_page():
        return 'The app is working!'
    
    return app 
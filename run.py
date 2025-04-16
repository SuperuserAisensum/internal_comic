from app import create_app
from datetime import datetime
import os

app = create_app()

# Add template context processor to make 'now' available in templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

if __name__ == '__main__':
    # Get port from environment variable or use 8080 as default
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
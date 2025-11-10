import os
import logging
from flask import Flask
from config import DEBUG, SECRET_KEY
from routes import bp

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['DEBUG'] = DEBUG
    
    # Registrar blueprint de rotas
    app.register_blueprint(bp)
    
    logger.info("Aplicação inicializada com sucesso")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
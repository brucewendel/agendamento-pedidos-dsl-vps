from flask import Flask
from config import FLASK_SECRET_KEY, FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from routes import main_routes

# Cria a aplicação Flask
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Registra o blueprint com todas as rotas
app.register_blueprint(main_routes)

# Filtro personalizado para converter None em traço
@app.template_filter('none_to_dash')
def none_to_dash(value):
    """Converte valores None, vazios ou 'None' em traço (-)"""
    if value is None or value == 'None' or str(value).strip() == '':
        return '-'
    return value

if __name__ == '__main__':
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )
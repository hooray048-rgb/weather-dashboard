from flask import Flask, jsonify, send_from_directory
from config import get_config
from api.weather import weather_bp


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config['JSON_AS_ASCII'] = False

    config = get_config()
    app.config.from_object(config)

    app.register_blueprint(weather_bp)

    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')

    @app.route('/health')
    def health():
        return jsonify({"status": "healthy"}), 200

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

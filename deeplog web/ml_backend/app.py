# ml_backend/app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from model_runtime import DualModelRuntime

load_dotenv()
APP_PORT = int(os.getenv('APP_PORT', '8000'))
CORS_ORIG = os.getenv('CORS_ORIGINS', '*')
API_TOKEN = os.getenv('API_TOKEN', '')
MODELS_DIR = os.getenv('MODELS_BASE', os.path.join(os.getcwd(), 'models', 'xgboost'))

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": CORS_ORIG, "supports_credentials": True}})

runtime = DualModelRuntime(MODELS_DIR)
runtime.load()


def authed(req):
    return (not API_TOKEN) or (req.headers.get('X-API-TOKEN') == API_TOKEN)


@app.get('/health')
def health():
    if not authed(request): return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    return jsonify({'ok': True, 'ready': True, 'models': {'base': MODELS_DIR}})


@app.post('/predict')
def predict():
    if not authed(request): return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    try:
        payload = request.get_json(force=True) or {}
        rows = payload.get('rows', [])
        if not isinstance(rows, list) or not rows:
            return jsonify({'ok': False, 'error': 'empty rows'}), 400
        entries, sums = runtime.predict(rows)
        return jsonify({'ok': True, 'entries': entries, 'summaries': sums})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=APP_PORT, debug=False)

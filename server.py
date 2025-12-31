"""
Servidor Flask minimalista para a interface do MonitCam.
"""

from flask import Flask, jsonify, request, send_file
import json
import os
import sys
import subprocess
import threading
import webbrowser
import time

# Importa funções de monitoramento
import main

app = Flask(__name__)

# Desabilita logs do Flask para console mais limpo
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


@app.route('/')
def index():
    """Serve o index.html"""
    return send_file('index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos (CSS, JS)"""
    return send_file(filename)


@app.route('/get_config')
def get_config():
    """Retorna a configuração do config.json"""
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            # Retorna configuração padrão
            default_config = {
                "CAPTURE_IMG": [320, 75, 730, 412],
                "COMPARE_IMG": [600, 75, 150, 250],
                "SENSIBILIDADE": 1000,
                "INTERVAL": 0.32,
                "DELAY_SELECAO": 3,
                "BLUR_KERNEL_SIZE": [5, 5],
                "DIFF_THRESHOLD": 25,
                "MORPH_KERNEL": [3, 3],
                "CAPTURE_DIR": "captures",
                "FILENAME_PREFIX": "suspeito",
                "SAVE_COMPARE_IMG": False,
                "SAVE_LOGS": False,
                "LOG_FILE": "monitcam.log",
                "ERROR_LOG_FILE": "monitcam_error.log",
                "RESTART_BASE_DELAY": 5,
                "RESTART_MAX_DELAY": 300
            }
            return jsonify(default_config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/save_config', methods=['POST'])
def save_config():
    """Salva a configuração no config.json"""
    try:
        data = request.get_json()
        
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atualiza configuração no main.py
        main.APP_CONFIG = data
        
        return jsonify({"success": True, "message": "Configuração salva com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/get_status')
def get_status():
    """Retorna o status atual do monitoramento"""
    return jsonify(main.get_monitor_status())


@app.route('/start_monitor', methods=['POST'])
def start_monitor():
    """Inicia o monitoramento"""
    # Carrega configuração antes de iniciar
    if os.path.exists('config.json'):
        main.load_settings()
    
    result = main.start_monitoring()
    return jsonify(result)


@app.route('/stop_monitor', methods=['POST'])
def stop_monitor():
    """Para o monitoramento"""
    result = main.stop_monitoring()
    return jsonify(result)


@app.route('/select_area')
def select_area():
    """Abre o seletor de área e retorna as coordenadas"""
    try:
        # Determina o caminho do Python (pode ser python ou python3 dependendo do SO)
        python_cmd = sys.executable
        
        # Executa o selector.py
        result = subprocess.run(
            [python_cmd, 'selector.py'],
            capture_output=True,
            text=True,
            timeout=60  # Timeout de 60 segundos
        )
        
        if result.returncode == 0:
            # Sucesso - parse das coordenadas
            coords_str = result.stdout.strip()
            coords = [int(x) for x in coords_str.split(',')]
            
            if len(coords) == 4:
                return jsonify({
                    "success": True,
                    "coordinates": coords,
                    "message": "Área selecionada com sucesso!"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Formato de coordenadas inválido."
                }), 400
        elif result.returncode == 1:
            # Cancelado pelo usuário
            return jsonify({
                "success": False,
                "message": "Seleção cancelada."
            }), 400
        else:
            # Erro
            error_msg = result.stderr.strip() if result.stderr else "Erro desconhecido"
            return jsonify({
                "success": False,
                "message": f"Erro no seletor: {error_msg}"
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "message": "Tempo limite excedido. Seleção cancelada."
        }), 408
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erro ao executar seletor: {str(e)}"
        }), 500


def open_browser():
    """Abre o navegador após um pequeno delay"""
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')


def run_server():
    """Inicia o servidor Flask"""
    # Abre o navegador em uma thread separada
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Inicia o servidor Flask
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)


if __name__ == '__main__':
    run_server()

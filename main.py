import cv2
import numpy as np
import pyautogui
import time
from datetime import datetime
import os
import sys
import logging
import traceback
import json
import threading

# --- Tente usar o backend mss, se disponível ---
try:
    import mss
    import mss.tools
except ImportError:
    mss = None

# --- Configuração do Logging ---
# (A configuração do arquivo de log será ajustada após carregar o config.json)
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler()])

# --- Variáveis Globais de Estado ---
APP_CONFIG = {}
monitor_thread = None
monitor_stop_event = threading.Event()
monitor_status = "stopped"  # Pode ser 'stopped', 'running', 'stopping', 'error'

# --- Carregamento da Configuração ---
def load_settings():
    """
    Carrega as configurações do arquivo config.json.
    Esta função substitui o antigo import config.
    """
    global APP_CONFIG, logging
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            APP_CONFIG = json.load(f)
        # Reconfigura o logger para usar o arquivo de log do config
        log_file = APP_CONFIG.get("LOG_FILE", "monitcam.log")
        if APP_CONFIG.get("SAVE_LOGS", False):
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            logging.getLogger().addHandler(file_handler)
        logging.info("Configuração carregada de config.json")
    except FileNotFoundError:
        logging.error("ERRO: O arquivo config.json não foi encontrado. A aplicação não pode iniciar.")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error("ERRO: O arquivo config.json está mal formatado.")
        sys.exit(1)

# Mantém a função load_config para compatibilidade interna
def load_config():
    """Alias para load_settings() - mantém compatibilidade."""
    load_settings()

def calculate_pixel_threshold(compare_region, sensitivity_percent):
    """
    Calcula o limiar de pixels baseado na área da região de comparação e no percentual de sensibilidade.
    
    Args:
        compare_region: Tupla (x, y, w, h) da região de comparação
        sensitivity_percent: Valor de 1 a 100, onde:
            - 100% = detecta qualquer mudança (limiar próximo a 0)
            - 1% = detecta apenas mudanças muito grandes (limiar próximo à área total)
    
    Returns:
        int: Limiar de pixels para detecção
    
    Fórmula: T = A × (1 - (sensibilidade / 100))
    """
    _, _, w, h = compare_region
    area = w * h
    
    # Garante que o percentual está entre 1 e 100
    sensitivity_percent = max(1, min(100, sensitivity_percent))
    
    # Calcula o limiar: quanto maior a sensibilidade, menor o limiar
    threshold = int(area * (1 - (sensitivity_percent / 100)))
    
    # Garante um mínimo de 1 pixel para evitar detecções espúrias em 100%
    threshold = max(1, threshold)
    
    logging.info(f"Área da região: {area} pixels | Sensibilidade: {sensitivity_percent}% | Limiar calculado: {threshold} pixels")
    
    return threshold

def save_config(new_config):
    """Salva a nova configuração no arquivo config.json."""
    global APP_CONFIG
    try:
        with open("config.json", "w") as f:
            json.dump(new_config, f, indent=2)
        APP_CONFIG = new_config
        logging.info("Configuração salva em config.json")
        return True
    except Exception as e:
        logging.error(f"Falha ao salvar a configuração: {e}")
        return False

# --- Lógica de Captura e Monitoramento (Adaptada do original) ---

def choose_backend():
    if mss is not None:
        logging.info("Backend escolhido: mss")
        return "mss"
    logging.info("Backend escolhido: pyautogui")
    return "pyautogui"

def clamp_region_to_screen(region):
    screen_w, screen_h = pyautogui.size()
    left, top, w, h = region
    left = max(0, int(left))
    top = max(0, int(top))
    w = max(1, int(min(w, screen_w - left)))
    h = max(1, int(min(h, screen_h - top)))
    return (left, top, w, h)

def capture_frame(region, backend):
    left, top, w, h = clamp_region_to_screen(region)
    try:
        if backend == "mss" and mss is not None:
            with mss.mss() as sct:
                monitor = {"left": left, "top": top, "width": w, "height": h}
                img = sct.grab(monitor)
                frame = np.array(img)
                return cv2.cvtColor(frame[..., :3], cv2.COLOR_BGR2GRAY)
        else:
            shot = pyautogui.screenshot(region=(left, top, w, h))
            frame = np.array(shot)
            return cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    except Exception as e:
        logging.error(f"Falha ao capturar frame com backend '{backend}': {e}")
    return np.zeros((h, w), dtype=np.uint8)

def run_monitor(config, stop_event):
    """
    Função principal de monitoramento, projetada para rodar em uma thread.
    
    Configurações técnicas fixas otimizadas:
    - DIFF_THRESHOLD: 25 (sensibilidade de diferença de pixel)
    - BLUR_KERNEL_SIZE: (5, 5) (redução de ruído)
    - MORPH_KERNEL: (3, 3) (remoção de falsos positivos)
    """
    global monitor_status
    monitor_status = "running"
    logging.info("Thread de monitoramento iniciada.")
    
    # Configurações técnicas fixas otimizadas para a maioria dos cenários
    DIFF_THRESHOLD = 25
    BLUR_KERNEL_SIZE = (5, 5)
    MORPH_KERNEL = (3, 3)

    try:
        backend = choose_backend()
        cap_region = clamp_region_to_screen(config["CAPTURE_IMG"])
        cmp_region = clamp_region_to_screen(config["COMPARE_IMG"])
        
        # Calcula o limiar de pixels baseado no percentual de sensibilidade
        pixel_threshold = calculate_pixel_threshold(cmp_region, config["SENSIBILIDADE"])
        
        logging.info("Usando CAPTURE_IMG=%s COMPARE_IMG=%s sensitivity=%d%% (limiar=%d pixels) interval=%.3f",
                     cap_region, cmp_region, config["SENSIBILIDADE"], pixel_threshold, config["INTERVAL"])

        ultimo_cmp = capture_frame(cmp_region, backend)
        
        while not stop_event.is_set():
            frame_A = capture_frame(cap_region, backend)
            frame_B = capture_frame(cmp_region, backend)

            diferenca = cv2.absdiff(ultimo_cmp, frame_B)
            diferenca_blur = cv2.GaussianBlur(diferenca, BLUR_KERNEL_SIZE, 0)
            _, diferenca_thresh = cv2.threshold(diferenca_blur, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
            
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_KERNEL)
            diferenca_thresh = cv2.morphologyEx(diferenca_thresh, cv2.MORPH_OPEN, kernel)
            score = int(cv2.countNonZero(diferenca_thresh))

            if score > pixel_threshold:
                horario = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                logging.info(f"Movimento detectado! score={score} -> salvando...")
                
                os.makedirs(config["CAPTURE_DIR"], exist_ok=True)
                arquivoA = os.path.join(config["CAPTURE_DIR"], f"{config['FILENAME_PREFIX']}_{horario}_A.png")
                cv2.imwrite(arquivoA, frame_A)

                if config["SAVE_COMPARE_IMG"]:
                    arquivoB = os.path.join(config["CAPTURE_DIR"], f"{config['FILENAME_PREFIX']}_{horario}_B.png")
                    cv2.imwrite(arquivoB, frame_B)

                ultimo_cmp = frame_B
                stop_event.wait(config["INTERVAL"] * 2)
            else:
                ultimo_cmp = frame_B
                stop_event.wait(config["INTERVAL"])

    except Exception as e:
        monitor_status = "error"
        logging.error(f"Erro fatal na thread de monitoramento: {e}")
        with open(APP_CONFIG.get("ERROR_LOG_FILE", "monitcam_error.log"), "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - Exception:\n")
            traceback.print_exc(file=f)
            f.write("\n")
    finally:
        if monitor_status != "error":
            monitor_status = "stopped"
        logging.info("Thread de monitoramento finalizada.")

# --- Funções de Controle de Monitoramento ---
def start_monitoring():
    """Inicia o monitoramento."""
    global monitor_thread, monitor_stop_event, monitor_status
    
    if monitor_thread is not None and monitor_thread.is_alive():
        logging.warning("O monitoramento já está em execução.")
        return {"success": False, "message": "O monitoramento já está em execução."}

    monitor_stop_event.clear()
    monitor_thread = threading.Thread(target=run_monitor, args=(APP_CONFIG, monitor_stop_event))
    monitor_thread.start()
    logging.info("Monitoramento iniciado.")
    return {"success": True, "message": "Monitoramento iniciado."}

def stop_monitoring():
    """Para o monitoramento."""
    global monitor_thread, monitor_status
    
    if monitor_thread is None or not monitor_thread.is_alive():
        monitor_status = "stopped"
        logging.warning("O monitoramento não está em execução.")
        return {"success": False, "message": "O monitoramento não está em execução."}

    logging.info("Parando o monitoramento...")
    monitor_status = "stopping"
    monitor_stop_event.set()
    
    # Aguarda a thread terminar
    monitor_thread.join(timeout=APP_CONFIG.get("INTERVAL", 1) * 3) 
    
    if monitor_thread.is_alive():
        logging.warning("A thread de monitoramento não parou a tempo.")
        monitor_status = "stopped"  # Marca como parado mesmo assim
        monitor_thread = None
        return {"success": False, "message": "A thread não respondeu ao comando de parada."}

    monitor_thread = None
    monitor_status = "stopped"
    logging.info("Monitoramento parado com sucesso.")
    return {"success": True, "message": "Monitoramento parado."}

def get_monitor_status():
    """Retorna o status atual do monitoramento."""
    return {"status": monitor_status}

def get_config():
    """Retorna a configuração atual."""
    return APP_CONFIG

def update_config(new_config):
    """Atualiza a configuração."""
    if monitor_status == 'running':
        return {"success": False, "message": "Pare o monitoramento antes de alterar a configuração."}
    
    if save_config(new_config):
        return {"success": True, "message": "Configuração salva."}
    else:
        return {"success": False, "message": "Falha ao salvar a configuração."}
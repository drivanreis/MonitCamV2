import cv2
import numpy as np
import pyautogui

# Optional faster, lower-memory screenshot backend (install via `pip install mss`).
try:
    import mss
    import mss.tools
except Exception:
    mss = None

import time
from datetime import datetime
import os
import sys

import logging
import traceback

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(config.LOG_FILE, encoding="utf-8")])



def choose_backend():
    """Prefer mss (se disponível), fallback para pyautogui."""
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
    """Captura uma região da tela de forma robusta, com fallbacks.
    Retorna um frame em escala de cinza (numpy array).
    """
    left, top, w, h = clamp_region_to_screen(region)

    try:
        # Tenta o backend principal (mss é mais rápido)
        if backend == "mss" and mss is not None:
            with mss.mss() as sct:
                monitor = {"left": left, "top": top, "width": w, "height": h}
                img = sct.grab(monitor)
                frame = np.array(img)
                gray = cv2.cvtColor(frame[..., :3], cv2.COLOR_BGR2GRAY)
                return ensure_frame_size(gray, w, h)
        
        # Fallback ou escolha principal: pyautogui
        shot = pyautogui.screenshot(region=(left, top, w, h))
        frame = np.array(shot)
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        return ensure_frame_size(gray, w, h)

    except Exception as e:
        logging.warning("Falha ao capturar com backend '%s': %s. Tentando fallback.", backend, e)
        # Tenta o backend alternativo
        try:
            if backend != "mss" and mss is not None: # Se o principal não era mss, tenta mss
                with mss.mss() as sct:
                    monitor = {"left": left, "top": top, "width": w, "height": h}
                    img = sct.grab(monitor)
                    frame = np.array(img)
                    gray = cv2.cvtColor(frame[..., :3], cv2.COLOR_BGR2GRAY)
                    return ensure_frame_size(gray, w, h)
            else: # Se o principal era mss (ou mss não existe), tenta pyautogui
                shot = pyautogui.screenshot(region=(left, top, w, h))
                frame = np.array(shot)
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                return ensure_frame_size(gray, w, h)
        except Exception as fallback_e:
            logging.error("Fallback de captura também falhou: %s", fallback_e)

    # Se tudo falhar, retorna um frame preto para não quebrar o loop.
    logging.error("Todas as tentativas de captura falharam. Retornando frame preto.")
    return np.zeros((h, w), dtype=np.uint8)

def ensure_frame_size(img, target_w, target_h):
    """Garante que `img` seja uma imagem em escala de cinza com tamanho (target_h, target_w)."""
    if img is None:
        return np.zeros((target_h, target_w), dtype=np.uint8)
    # converte BGR->GRAY ou pega canal se BGRA
    if img.ndim == 3:
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            # reduz para um canal (ex: BGRA)
            img = img[..., 0]
    # agora img é 2D
    img = img.astype(np.uint8)
    h, w = img.shape
    if (w, h) == (target_w, target_h):
        return img
    # crop central se maior
    if h > target_h or w > target_w:
        y0 = max(0, (h - target_h) // 2)
        x0 = max(0, (w - target_w) // 2)
        cropped = img[y0:y0+target_h, x0:x0+target_w]
        # garante tamanho após crop
        if cropped.shape == (target_h, target_w):
            return cropped
        # fallback para padding se necessário
        img = cropped
        h, w = img.shape
    # pad central se menor
    out = np.zeros((target_h, target_w), dtype=np.uint8)
    y0 = (target_h - h) // 2
    x0 = (target_w - w) // 2
    out[y0:y0+h, x0:x0+w] = img
    return out


print("Iniciando monitoramento... Pressione Ctrl+C para parar.")

def run_monitor():
    backend = choose_backend()

    # Regiões de captura e comparação
    cap_region = clamp_region_to_screen(config.CAPTURE_IMG)
    cmp_region = clamp_region_to_screen(config.COMPARE_IMG)
    
    logging.info("Usando CAPTURE_IMG=%s COMPARE_IMG=%s sensitivity=%d interval=%.3f",
                 cap_region, cmp_region, config.SENSIBILIDADE, config.INTERVAL)

    # Captura inicial para estabelecer uma referência
    ultimo_cmp = capture_frame(cmp_region, backend)
    
    while True:
        # Captura a imagem de contexto (A) e a imagem de comparação (B)
        frame_A = capture_frame(cap_region, backend)
        frame_B = capture_frame(cmp_region, backend)

        # Compara a imagem de comparação atual com a anterior
        diferenca = cv2.absdiff(ultimo_cmp, frame_B)
        diferenca_blur = cv2.GaussianBlur(diferenca, config.BLUR_KERNEL_SIZE, 0)
        _, diferenca_thresh = cv2.threshold(diferenca_blur, config.DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, config.MORPH_KERNEL)
        diferenca_thresh = cv2.morphologyEx(diferenca_thresh, cv2.MORPH_OPEN, kernel)
        score = int(cv2.countNonZero(diferenca_thresh))

        if score > config.SENSIBILIDADE:
            horario = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            logging.info("Movimento detectado na COMPARE_IMG! score=%d -> salvando...", score)
            
            os.makedirs(config.CAPTURE_DIR, exist_ok=True)
            
            arquivoA = os.path.join(config.CAPTURE_DIR, f"{config.FILENAME_PREFIX}_{horario}_A.png")
            cv2.imwrite(arquivoA, frame_A)
            logging.info("Salvo: %s", arquivoA)

            if config.SAVE_COMPARE_IMG:
                arquivoB = os.path.join(config.CAPTURE_DIR, f"{config.FILENAME_PREFIX}_{horario}_B.png")
                cv2.imwrite(arquivoB, frame_B)
                logging.info("Salvo: %s", arquivoB)

            # Atualiza referência e aguarda para evitar ruído repetido
            ultimo_cmp = frame_B
            time.sleep(config.INTERVAL * 2)
            continue

        ultimo_cmp = frame_B
        time.sleep(config.INTERVAL)


def main():
    delay = config.RESTART_BASE_DELAY
    while True:
        try:
            run_monitor()
        except KeyboardInterrupt:
            logging.info("Monitor interrompido pelo usuário.")
            break
        except Exception as e:
            logging.error("Erro fatal no monitor: %s", e)
            with open(config.ERROR_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} - Exception:\n")
                traceback.print_exc(file=f)
                f.write("\n")
            logging.info("Reiniciando em %d segundos...", delay)
            time.sleep(delay)
            delay = min(delay * 2, config.RESTART_MAX_DELAY)

if __name__ == "__main__":
    main()
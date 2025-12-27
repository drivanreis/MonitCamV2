"""
Arquivo de configuração para o MonitCam.
Centraliza todas as variáveis ajustáveis para facilitar a manutenção.
"""

# --- CONFIGURAÇÕES DE CAPTURA E DETECÇÃO ---

# Região a capturar da tela (x, y, w, h).
# Esta é a região total que será salva quando um movimento for detectado.
CAPTURE_IMG = (320, 75, 730, 412)

# Região fixa usada para detectar mudanças (x, y, w, h).
# Esta é uma sub-região (idealmente dentro da CAPTURE_IMG) onde a detecção de
# movimento realmente acontece. Usar uma região menor e focada otimiza a performance.
COMPARE_IMG = (600, 75, 150, 250)

# Sensibilidade da detecção na COMPARE_IMG (número de pixels diferentes).
# Um valor maior significa que mais pixels precisam mudar para acionar a detecção.
SENSIBILIDADE = 1000

# Intervalo entre capturas em segundos.
# Valores menores (ex: 0.1) aumentam a responsividade, mas também o uso de CPU.
INTERVAL = 0.32

# --- CONFIGURAÇÕES DE PROCESSAMENTO DE IMAGEM ---

# Tamanho do kernel para o desfoque Gaussiano (GaussianBlur). Ajuda a reduzir ruído.
# Deve ser uma tupla de dois números ímpares, ex: (5, 5).
BLUR_KERNEL_SIZE = (5, 5)

# Limiar (threshold) para a binarização da imagem de diferença.
# Pixels com diferença de cor acima deste valor serão considerados "movimento".
# Valores entre 20 e 40 são geralmente um bom ponto de partida.
DIFF_THRESHOLD = 25

# Kernel usado em operações morfológicas (cv2.MORPH_OPEN) para remover ruído
# da imagem de diferença. Ajuda a eliminar pequenos "falsos positivos" de movimento.
# Formato: (largura, altura).
MORPH_KERNEL = (3, 3)

# --- CONFIGURAÇÕES DE SAÍDA E COMPORTAMENTO ---

# Diretório onde as imagens capturadas serão salvas.
CAPTURE_DIR = "captures"

# Prefixo do nome do arquivo para as imagens salvas.
FILENAME_PREFIX = "suspeito"

# [NOVO] Se True, salva a imagem da área de comparação (COMPARE_IMG) junto com a
# imagem de captura principal (CAPTURE_IMG). Se False, salva apenas a principal.
SAVE_COMPARE_IMG = False

# Devo criar e salvar o arquivo de Logs?
SAVE_LOGS = False

# Nome do arquivo de log principal.
LOG_FILE = "monitcam.log"

# Nome do arquivo para registrar erros fatais antes de um reinício.
ERROR_LOG_FILE = "monitcam_error.log"

# Configuração para reinício automático em caso de erro fatal.
RESTART_BASE_DELAY = 5  # Atraso inicial em segundos.
RESTART_MAX_DELAY = 300 # Atraso máximo em segundos (para evitar loops rápidos de erro).

"""
Arquivo de configuração para o MonitCam.
Centraliza todas as variáveis ajustáveis para facilitar a manutenção.
"""

# --- CONFIGURAÇÕES DE CAPTURA E DETECÇÃO ---

# Região padrão a capturar da tela (x, y, w, h).
# Esta é a região total que será salva quando um movimento for detectado.
# O valor padrão pode ser sobrescrito pelo argumento --region na linha de comando.
CAPTURE_IMG = (320, 75, 730, 412)

# Região fixa usada para detectar mudanças (x, y, w, h).
# Esta é uma sub-região (idealmente dentro da CAPTURE_IMG) onde a detecção de
# movimento realmente acontece. Usar uma região menor e focada otimiza a performance.
COMPARE_IMG = (600, 75, 150, 250)

# Sensibilidade da detecção na COMPARE_IMG (número de pixels diferentes).
# Um valor maior significa que mais pixels precisam mudar para acionar a detecção.
# Ajuste este valor com base na sua cena e no nível de ruído.
SENSIBILIDADE = 1000

# Intervalo padrão entre capturas em segundos.
# Valores menores (ex: 0.1) aumentam a responsividade, mas também o uso de CPU.
# Valores maiores (ex: 1.0) são mais leves para o sistema.
INTERVAL = 0.32

# Kernel usado em operações morfológicas (cv2.MORPH_OPEN) para remover ruído
# da imagem de diferença. Ajuda a eliminar pequenos "falsos positivos" de movimento.
# Formato: (largura, altura).
MORPH_KERNEL = (3, 3)

# --- CONFIGURAÇÕES DE COMPORTAMENTO DO SCRIPT ---

# Configuração para reinício automático em caso de erro fatal.
RESTART_BASE_DELAY = 5  # Atraso inicial em segundos.
RESTART_MAX_DELAY = 300 # Atraso máximo em segundos (para evitar loops rápidos de erro).
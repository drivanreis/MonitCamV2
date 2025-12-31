document.addEventListener('DOMContentLoaded', () => {
    // --- Elementos da UI ---
    const statusIndicator = document.getElementById('status-indicator');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const saveBtn = document.getElementById('save-btn');
    const configForm = document.getElementById('config-form');
    const saveStatus = document.getElementById('save-status');
    const loadingOverlay = document.getElementById('loading-overlay');
    const mainContainer = document.getElementById('main-container');

    // --- Estado da Aplicação ---
    let currentConfig = {};
    let initialConfig = {};
    let isDirty = false;
    let monitorStatus = 'stopped';
    let isLoaded = false;
    const STATUS_POLL_INTERVAL = 2000; // ms

    // --- API Flask ---
    const api = {
        getConfig: () => fetch('/get_config').then(r => r.json()),
        saveConfig: (data) => fetch('/save_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).then(r => r.json()),
        getStatus: () => fetch('/get_status').then(r => r.json()),
        startMonitor: () => fetch('/start_monitor', { method: 'POST' }).then(r => r.json()),
        stopMonitor: () => fetch('/stop_monitor', { method: 'POST' }).then(r => r.json()),
        selectArea: () => fetch('/select_area').then(r => r.json())
    };

    // --- Funções Principais ---

    function updateStatusIndicator() {
        statusIndicator.className = '';
        statusIndicator.classList.add(`status-${monitorStatus}`);
        let statusText = 'Desconhecido';
        switch (monitorStatus) {
            case 'running': statusText = 'Em Execução'; break;
            case 'stopped': statusText = 'Parado'; break;
            case 'stopping': statusText = 'Parando...'; break;
            case 'error': statusText = 'Erro'; break;
        }
        statusIndicator.textContent = statusText;

        startBtn.disabled = !isLoaded || monitorStatus === 'running' || monitorStatus === 'stopping';
        stopBtn.disabled = !isLoaded || monitorStatus !== 'running';
        saveBtn.disabled = !isLoaded || !isDirty || monitorStatus === 'running';
    }

    async function fetchStatus() {
        try {
            const data = await api.getStatus();
            if (data.status !== monitorStatus) {
                monitorStatus = data.status;
                updateStatusIndicator();
            }
        } catch (error) {
            console.error('Erro ao buscar status:', error);
        }
    }

    function populateForm(config) {
        Object.keys(config).forEach(key => {
            const input = document.getElementById(key);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = config[key];
                } else if (Array.isArray(config[key])) {
                    input.value = config[key].join(', ');
                } else {
                    input.value = config[key];
                }
            }
        });
    }

    function readForm() {
        const newConfig = {};
        for (const element of configForm.elements) {
            if (element.id) {
                if (element.type === 'checkbox') {
                    newConfig[element.id] = element.checked;
                } else if (element.type === 'number') {
                    newConfig[element.id] = parseFloat(element.value);
                } else if (element.type === 'text') {
                    if (['CAPTURE_IMG', 'COMPARE_IMG', 'BLUR_KERNEL_SIZE', 'MORPH_KERNEL'].includes(element.id)) {
                        newConfig[element.id] = element.value.split(',').map(item => parseInt(item.trim(), 10));
                    } else {
                        newConfig[element.id] = element.value;
                    }
                }
            }
        }
        return newConfig;
    }

    function checkFormDirty() {
        const newConfig = readForm();
        isDirty = JSON.stringify(newConfig) !== JSON.stringify(currentConfig);
        updateStatusIndicator();
    }

    async function initialize() {
        try {
            currentConfig = await api.getConfig();
            initialConfig = JSON.parse(JSON.stringify(currentConfig));
            populateForm(currentConfig);
            
            await fetchStatus();
            setInterval(fetchStatus, STATUS_POLL_INTERVAL);

            configForm.addEventListener('input', checkFormDirty);
            configForm.addEventListener('change', checkFormDirty);
            
            isLoaded = true;
            updateStatusIndicator();
            hideLoadingOverlay();
        } catch (error) {
            console.error('Erro ao inicializar:', error);
            hideLoadingOverlay(true);
        }
    }

    function hideLoadingOverlay(immediate = false) {
        if (immediate) {
            loadingOverlay.style.display = 'none';
            mainContainer.style.opacity = '1';
            mainContainer.classList.add('loaded');
        } else {
            setTimeout(() => {
                loadingOverlay.classList.add('hidden');
                mainContainer.classList.add('loaded');
            }, 300);
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 600);
        }
    }

    // --- Event Handlers ---

    // Botões de seleção de área
    const pegaAreaTotalBtn = document.getElementById('pega-area-total-btn');
    const pegaAreaDetecBtn = document.getElementById('pega-area-detec-btn');
    const countdownOverlay = document.getElementById('countdown-overlay');
    const countdownNumber = document.getElementById('countdown-number');
    const countdownSeconds = document.getElementById('countdown-seconds');

    async function selectScreenArea(targetInputId) {
        const targetInput = document.getElementById(targetInputId);
        
        // Lê o valor de DELAY_SELECAO da configuração atual
        const delaySelecao = currentConfig.DELAY_SELECAO || 3;
        
        // Mostra aviso inicial
        saveStatus.textContent = 'Iniciando seleção de área...';
        saveStatus.style.color = '#2196F3';
        
        // Desabilita todos os botões durante a seleção
        const allButtons = document.querySelectorAll('button');
        allButtons.forEach(btn => btn.disabled = true);
        
        // Mostra o overlay de contagem regressiva
        countdownOverlay.classList.add('show');
        
        // Executa a contagem regressiva
        let timeLeft = delaySelecao;
        
        const updateCountdown = () => {
            countdownNumber.textContent = timeLeft;
            countdownSeconds.textContent = timeLeft;
            
            // Anima o número
            countdownNumber.style.animation = 'none';
            setTimeout(() => {
                countdownNumber.style.animation = 'pulse 1s ease-in-out';
            }, 10);
        };
        
        updateCountdown();
        
        // Aguarda a contagem regressiva
        await new Promise(resolve => {
            const countdownInterval = setInterval(() => {
                timeLeft--;
                
                if (timeLeft > 0) {
                    updateCountdown();
                } else {
                    clearInterval(countdownInterval);
                    resolve();
                }
            }, 1000);
        });
        
        // Esconde o overlay
        countdownOverlay.classList.remove('show');
        
        // Atualiza mensagem
        saveStatus.textContent = 'Selecione a área na tela...';
        
        try {
            const response = await api.selectArea();
            
            if (response.success) {
                // Preenche o input com as coordenadas
                targetInput.value = response.coordinates.join(', ');
                saveStatus.textContent = response.message;
                saveStatus.style.color = '#4CAF50';
                
                // Marca o formulário como alterado
                checkFormDirty();
            } else {
                saveStatus.textContent = response.message;
                saveStatus.style.color = '#f44336';
            }
        } catch (error) {
            console.error('Erro ao selecionar área:', error);
            saveStatus.textContent = 'Erro ao selecionar área.';
            saveStatus.style.color = '#f44336';
        } finally {
            // Reabilita os botões
            allButtons.forEach(btn => {
                if (btn.id === 'start-btn') {
                    btn.disabled = !isLoaded || monitorStatus === 'running' || monitorStatus === 'stopping';
                } else if (btn.id === 'stop-btn') {
                    btn.disabled = !isLoaded || monitorStatus !== 'running';
                } else if (btn.id === 'save-btn') {
                    btn.disabled = !isLoaded || !isDirty || monitorStatus === 'running';
                } else {
                    btn.disabled = false;
                }
            });
            
            // Limpa a mensagem após 3 segundos
            setTimeout(() => {
                saveStatus.textContent = '';
                saveStatus.style.color = '';
            }, 3000);
        }
    }

    pegaAreaTotalBtn.addEventListener('click', (e) => {
        e.preventDefault();
        selectScreenArea('CAPTURE_IMG');
    });

    pegaAreaDetecBtn.addEventListener('click', (e) => {
        e.preventDefault();
        selectScreenArea('COMPARE_IMG');
    });

    startBtn.addEventListener('click', async () => {
        if (!isLoaded) return;
        try {
            const response = await api.startMonitor();
            if (response.success) {
                monitorStatus = 'running';
                updateStatusIndicator();
                saveStatus.textContent = 'Monitoramento iniciado.';
            } else {
                saveStatus.textContent = `Erro: ${response.message}`;
            }
        } catch (error) {
            console.error('Erro:', error);
            saveStatus.textContent = 'Erro ao iniciar.';
        }
    });

    stopBtn.addEventListener('click', async () => {
        if (!isLoaded) return;
        try {
            monitorStatus = 'stopping';
            updateStatusIndicator();
            const response = await api.stopMonitor();
            if (response.success) {
                monitorStatus = 'stopped';
                updateStatusIndicator();
                saveStatus.textContent = 'Monitoramento parado.';
            } else {
                saveStatus.textContent = `Erro: ${response.message}`;
                fetchStatus();
            }
        } catch (error) {
            console.error('Erro:', error);
            saveStatus.textContent = 'Erro ao parar.';
        }
    });

    configForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!isLoaded || !isDirty || monitorStatus === 'running') return;

        const newConfig = readForm();
        saveBtn.classList.add('saving');
        saveBtn.disabled = true;
        saveStatus.textContent = 'Salvando...';

        try {
            const response = await api.saveConfig(newConfig);
            if (response.success) {
                currentConfig = newConfig;
                isDirty = false;
                updateStatusIndicator();
                saveStatus.textContent = 'Configuração salva com sucesso!';
            } else {
                saveStatus.textContent = `Erro: ${response.message}`;
            }
        } catch (error) {
            console.error('Erro:', error);
            saveStatus.textContent = 'Erro ao salvar.';
        } finally {
            saveBtn.classList.remove('saving');
            saveBtn.disabled = false;
        }
        
        setTimeout(() => saveStatus.textContent = '', 3000);
    });

    // --- Inicialização ---
    initialize();
});

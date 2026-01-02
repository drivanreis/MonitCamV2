document.addEventListener('DOMContentLoaded', () => {
    // --- Elementos da UI ---
    const statusIndicator = document.getElementById('status-indicator');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const saveBtn = document.getElementById('save-btn');
    const discardBtn = document.getElementById('discard-btn');
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

    // --- Alertas Educativos Rigorosos ---
    // Impede o fechamento da aba se houver monitoramento ativo ou alterações não salvas
    window.addEventListener('beforeunload', (event) => {
        const isMonitoring = monitorStatus === 'running';
        const hasUnsavedChanges = isDirty;
        
        if (isMonitoring || hasUnsavedChanges) {
            // Monta mensagem específica baseada no estado
            let message = '⚠️ AÇÃO BLOQUEADA! ⚠️\n\n';
            
            if (isMonitoring && hasUnsavedChanges) {
                message += 'Você precisa:\n';
                message += '1. PARAR o monitoramento\n';
                message += '2. SALVAR ou DESCARTAR as alterações\n\n';
                message += 'Depois, para encerrar a aplicação:\n';
                message += 'IMPORTANTE: Clique uma vez dentro da janela preta (CMD) para ativá-la antes de apertar Ctrl+C.\n';
                message += 'Se o primeiro comando não funcionar, tente novamente.';
            } else if (isMonitoring) {
                message += 'O monitoramento está ATIVO!\n\n';
                message += 'Clique em "■ Parar" antes de fechar.\n\n';
                message += 'Depois, para encerrar a aplicação:\n';
                message += 'IMPORTANTE: Clique uma vez dentro da janela preta (CMD) para ativá-la antes de apertar Ctrl+C.\n';
                message += 'Se o primeiro comando não funcionar, tente novamente.';
            } else if (hasUnsavedChanges) {
                message += 'Você tem alterações NÃO SALVAS!\n\n';
                message += 'Clique em "💾 Salvar Configurações" ou "↺ Descartar Alterações" antes de fechar.';
            }
            
            // Define returnValue para ativar o popup padrão do navegador
            event.preventDefault();
            event.returnValue = message;
            
            // Tenta mostrar alert (pode não funcionar em todos os navegadores durante beforeunload)
            // Mas serve como reforço em navegadores que permitem
            setTimeout(() => {
                alert(message);
            }, 10);
            
            return event.returnValue;
        }
    });

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

        // Botão Iniciar: bloqueado se isDirty (alterações pendentes) ou se monitoramento está ativo
        startBtn.disabled = !isLoaded || isDirty || monitorStatus === 'running' || monitorStatus === 'stopping';
        stopBtn.disabled = !isLoaded || monitorStatus !== 'running';
        saveBtn.disabled = !isLoaded || !isDirty || monitorStatus === 'running';
        discardBtn.disabled = !isLoaded || !isDirty || monitorStatus === 'running';
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
                } else if (input.type === 'range') {
                    input.value = config[key];
                    // Atualiza o display do valor ao lado do slider
                    const output = document.getElementById(`${key}-value`);
                    if (output) output.textContent = config[key];
                } else if (input.tagName === 'SELECT' && key === 'INTERVAL') {
                    // Converte segundos para fotos por segundo
                    const fps = Math.round(1 / config[key]);
                    // Garante que o valor está entre 1 e 4
                    input.value = Math.max(1, Math.min(4, fps)).toString();
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
                } else if (element.type === 'number' || element.type === 'range') {
                    let value = parseFloat(element.value);
                    // Validação especial para SENSIBILIDADE
                    if (element.id === 'SENSIBILIDADE') {
                        value = Math.max(1, Math.min(100, value));
                    }
                    newConfig[element.id] = value;
                } else if (element.tagName === 'SELECT' && element.id === 'INTERVAL') {
                    // Converte fotos por segundo para segundos
                    const fps = parseInt(element.value, 10);
                    newConfig[element.id] = parseFloat((1 / fps).toFixed(3));
                } else if (element.type === 'text') {
                    if (['CAPTURE_IMG', 'COMPARE_IMG'].includes(element.id)) {
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

            // Event listeners para mudanças no formulário
            configForm.addEventListener('input', checkFormDirty);
            configForm.addEventListener('change', checkFormDirty);
            
            // Event listener para atualizar o display do slider de sensibilidade
            const sensibilidadeSlider = document.getElementById('SENSIBILIDADE');
            const sensibilidadeOutput = document.getElementById('SENSIBILIDADE-value');
            if (sensibilidadeSlider && sensibilidadeOutput) {
                sensibilidadeSlider.addEventListener('input', (e) => {
                    sensibilidadeOutput.textContent = e.target.value;
                });
            }
            
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
            // Reabilita os botões usando updateStatusIndicator
            allButtons.forEach(btn => btn.disabled = false);
            updateStatusIndicator();
            
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
        
        // Trava de segurança: bloqueia início se há alterações não salvas
        if (isDirty) {
            saveStatus.textContent = '⚠️ Salve ou descarte as alterações antes de iniciar o monitoramento.';
            saveStatus.style.color = '#ffc107';
            setTimeout(() => {
                saveStatus.textContent = '';
                saveStatus.style.color = '';
            }, 4000);
            return;
        }
        
        try {
            const response = await api.startMonitor();
            if (response.success) {
                monitorStatus = 'running';
                updateStatusIndicator();
                saveStatus.textContent = 'Monitoramento iniciado.';
                saveStatus.style.color = '#4CAF50';
            } else {
                saveStatus.textContent = `Erro: ${response.message}`;
                saveStatus.style.color = '#f44336';
            }
        } catch (error) {
            console.error('Erro:', error);
            saveStatus.textContent = 'Erro ao iniciar.';
            saveStatus.style.color = '#f44336';
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
        discardBtn.disabled = true;
        saveStatus.textContent = 'Salvando...';
        saveStatus.style.color = '#2196F3';

        try {
            const response = await api.saveConfig(newConfig);
            if (response.success) {
                currentConfig = newConfig;
                isDirty = false;
                updateStatusIndicator();
                saveStatus.textContent = '✓ Configuração salva com sucesso!';
                saveStatus.style.color = '#4CAF50';
            } else {
                saveStatus.textContent = `Erro: ${response.message}`;
                saveStatus.style.color = '#f44336';
            }
        } catch (error) {
            console.error('Erro:', error);
            saveStatus.textContent = 'Erro ao salvar.';
            saveStatus.style.color = '#f44336';
        } finally {
            saveBtn.classList.remove('saving');
            updateStatusIndicator();
        }
        
        setTimeout(() => {
            saveStatus.textContent = '';
            saveStatus.style.color = '';
        }, 3000);
    });

    // Event handler para Descartar Alterações
    discardBtn.addEventListener('click', async () => {
        if (!isLoaded || !isDirty || monitorStatus === 'running') return;
        
        discardBtn.disabled = true;
        saveBtn.disabled = true;
        saveStatus.textContent = 'Descartando alterações...';
        saveStatus.style.color = '#2196F3';
        
        try {
            // Recarrega configuração do servidor
            const config = await api.getConfig();
            currentConfig = config;
            
            // Preenche o formulário com os valores originais
            populateForm(config);
            
            // Marca como não alterado
            isDirty = false;
            updateStatusIndicator();
            
            saveStatus.textContent = '✓ Alterações descartadas.';
            saveStatus.style.color = '#4CAF50';
        } catch (error) {
            console.error('Erro ao descartar:', error);
            saveStatus.textContent = 'Erro ao descartar alterações.';
            saveStatus.style.color = '#f44336';
        }
        
        setTimeout(() => {
            saveStatus.textContent = '';
            saveStatus.style.color = '';
        }, 3000);
    });

    // --- Inicialização ---
    initialize();

    // --- Alerta Inicial ---
    // Exibe aviso importante após carregar a interface
    setTimeout(() => {
        alert('⚠️ IMPORTANTE ⚠️\n\nNÃO FECHE O CMD!\n\nEle está rodando toda a lógica de captura de tela do MonitCam.\n\nPara encerrar a aplicação corretamente:\n1. Pare o monitoramento nesta interface\n2. Feche esta aba do navegador\n3. Clique uma vez dentro da janela preta (CMD) para ativá-la\n4. Pressione Ctrl+C (pode ser necessário tentar duas vezes para o Windows reconhecer o comando)');
    }, 1000);
});

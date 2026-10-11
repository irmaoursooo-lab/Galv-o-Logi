# 🚛 Galvão Logi — Plataforma Inteligente e Colaborativa de Roteirização de Cargas

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-48%20Passed-30D158?logo=pytest&logoColor=white)](https://pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

O **Galvão Logi** é uma plataforma inteligente e colaborativa (*estilo "Waze para Caminhoneiros e Transportadoras"*) baseada em um sistema multi-agente orquestrado, estética industrial Apple (**Zero IA-Slop**) e arquitetura **Offline-First**.

---

## ✨ Principais Funcionalidades (Versão Final de Produção)

1. **🛣️ Roteamento Viário Real pelas Ruas (OSRM & OR-Tools VRPTW)**:
   - Elimina linhas retas artificiais: o traçado segue rigorosamente a malha viária brasileira (ruas, avenidas, pontes e rodovias).
   - Otimiza a ordem mais eficiente das entregas respeitando janelas de horário e minimizando o tempo total.
2. **📷 Leitura de Notas Fiscais e Itinerários com Sigilo Total (LGPD)**:
   - Permite fotografar notas fiscais (DANFE / NF-e) ou romaneios impressos.
   - Extrai automaticamente apenas os endereços de entrega e descarta da memória dados fiscais sensíveis (**CPF, CNPJ, preços, valores, impostos e itens**). Nenhum dado fiscal sensível é persistido.
3. **✍️ Autocomplete em Tempo Real com Alta Precisão Predial**:
   - Campo de busca estilo Google Maps / Waze com feedback em tempo real.
   - Reconhece nomes de estabelecimentos (ex: *"Hipermercado Bernardão em Patos de Minas"*) e números prediais exatos (ex: *"Rua Padre Américo Ceppi, 806"* no Bairro Brasil), sem centróides genéricos de CEP.
4. **📋 Edição Dinâmica do Itinerário**:
   - Gaveta lateral intuitiva que permite:
     - ✏️ **Editar**: Alterar nome e endereço da parada com re-geocodificação instantânea.
     - ⬆️ / ⬇️ **Reordenar**: Ajustar a ordem manualmente conforme a conveniência da carga.
     - 🗑️ **Excluir**: Remover paradas com recálculo automático da rota pelas ruas.
5. **▶️ Navegação Turn-by-Turn ao Vivo com Barra de Progresso**:
   - Acompanha o caminhão ao vivo ao longo das curvas e vias em tempo real.
   - Barra de progresso Apple HUD exibindo **% concluído**, km restantes e ETA atualizado.
6. **🍽️ Bem-Estar e Paradas Regulamentares**:
   - Pontos de alimentação (café, almoço, descanso) são exibidos como intervalos (`🍽️`) e **não consomem nem inflam a contagem de paradas de entrega**.
7. **🔇 Controle Total de Áudio**:
   - Botão de 1 toque para alternar entre voz do copiloto ativada (🔊) e silêncio absoluto (🔇).
8. **📶 Arquitetura Offline-First (Fila Outbox)**:
   - Continua funcionando e orientando por satélite mesmo em rodovias e serras sem sinal 4G/5G, sincronizando apontamentos em segundo plano quando a internet retornar.

---

## 🏛️ Arquitetura do Sistema Multi-Agente

```
┌────────────────────────────────────────────────────────────────────────┐
│                   🎯 Agente 1: Supervisor / Orquestrador               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
    ┌──────────────┬────────────────┼────────────────┬────────────────┐
    ▼              ▼                ▼                ▼                ▼
┌────────┐   ┌────────────┐   ┌────────────┐   ┌───────────┐   ┌───────────┐
│🚚 OR-  │   │🚧 Monitor  │   │⏱️ Doca     │   │🍽️ Bem-     │   │🧠 Copiloto│
│Tools   │   │de Entraves │   │Profiler    │   │Estar &    │   │de Voz TTS │
│Solver  │   │& Gabaritos │   │Colaborativo│   │Refeições  │   │(Gemini AI)│
└────────┘   └────────────┘   └────────────┘   └───────────┘   └───────────┘
```

---

## 🚀 Como Subir para o GitHub

No terminal (PowerShell ou Git Bash) na pasta do projeto:

```bash
# 1. Inicializar o repositório Git
git init

# 2. Adicionar todos os arquivos do projeto
git add .

# 3. Criar o commit inicial de produção
git commit -m "feat: versão final de produção Galvão Logi pronta para deploy"

# 4. Definir a branch principal como main
git branch -M main

# 5. Conectar ao seu repositório no GitHub (substitua pela sua URL)
git remote add origin https://github.com/SEU_USUARIO/galvao-logi.git

# 6. Enviar para o GitHub
git push -u origin main
```

---

## ☁️ Como Fazer Deploy no Render.com (100% Gratuito)

O repositório já conta com o arquivo `render.yaml` e `Dockerfile` configurados para deploy em nuvem.

### Opção 1: Deploy com 1 Clique via Blueprint (Recomendado)
1. Crie uma conta gratuita em [render.com](https://render.com/).
2. No painel do Render, clique em **New +** e selecione **Blueprint**.
3. Conecte o repositório do GitHub criado no passo anterior.
4. O Render detectará automaticamente o arquivo `render.yaml` e configurará o Web Service em instantes!

### Opção 2: Deploy Manual como Web Service
1. No painel do Render, clique em **New +** > **Web Service**.
2. Conecte seu repositório do GitHub.
3. Preencha as configurações:
   - **Name**: `galvao-logi`
   - **Language / Runtime**: `Python 3`
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Em **Environment Variables**, adicione:
   - `PYTHONPATH`: `.`
   - `DEBUG`: `false`
5. Clique em **Create Web Service**.

Assim que o deploy terminar, o Render fornecerá um link público e seguro (exemplo: `https://galvao-logi.onrender.com`).

---

## 💻 Como Rodar Localmente no Computador

### 1. Iniciar o Servidor
```powershell
# Ativar o ambiente virtual
.\.venv\Scripts\Activate.ps1

# Iniciar o servidor com recarregamento automático
python -m uvicorn backend.app.main:app --port 8000 --reload
```

### 2. Acessar
- **Cockpit Web**: [http://localhost:8000](http://localhost:8000)
- **Documentação Interativa Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Executar os Testes Automatizados
```powershell
pytest backend/tests -v
```
*(48 testes automatizados cobrindo todos os agentes, geocodificação, roteamento pelas ruas, anti-ociosidade e proteção LGPD).*

---

## 📱 Como Usar no Celular sem Computador Ligado

Com o servidor rodando no **Render.com**:
1. Abra o link gerado pelo Render no navegador do celular (Google Chrome no Android ou Safari no iPhone).
2. Toque no menu do navegador e selecione **"Adicionar à tela de início"**.
3. O Galvão Logi será instalado como um aplicativo nativo (**PWA**), rodando em tela cheia com acesso a GPS satelital, voz sintética e câmera para leitura de notas fiscais.

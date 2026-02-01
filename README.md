# HelpHub 4.0 - Sistema de Gestão de Chamados e Assistência Técnica

![HelpHub Banner](https://img.shields.io/badge/HelpHub-4.0-blue?style=for-the-badge&logo=flask)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Flask 3.0.0](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![License Non-Commercial](https://img.shields.io/badge/License-Non--Commercial-orange.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/Tests-25%20Files-success)](tests/)

O **HelpHub 4.0** é uma plataforma corporativa de alto desempenho para gestão de tickets, assistência técnica e planejamento logístico. Projetado com foco em **Segurança**, **Escalabilidade Modular** e **UX Premium**, o sistema oferece controle total sobre o ciclo de vida do atendimento ao cliente.

---

## Arquitetura e Core do Sistema

O sistema utiliza o padrão **Application Factory** com arquitetura baseada em **Blueprints**, garantindo isolamento total entre módulos e facilidade de manutenção.

### Estrutura de Camadas (Blueprint)

| Camada        | Escopo     | Responsabilidade Técnica                                              |
| :------------ | :--------- | :-------------------------------------------------------------------- |
| **01. BOOT**  | `App/`     | Inicialização do Flask, Registro de Blueprints e Engine de Logs.      |
| **02. LOGIC** | `Modulos/` | Core de Negócio: Regras de Chamados, Agendas, Clientes e Auth.        |
| **03. INFRA** | `Engine/`  | Gerenciamento de Uploads, Tarefas Cron (AWS/APScheduler) e Auditoria. |

### Ciclo de Vida de uma Solicitação

Para cada requisição do usuário, o sistema percorre este fluxo de proteção e execução:

1.  **Escudo:** `seguranca.py` (Validação de Rate-Limit e Proteção CSRF).
2.  **Identidade:** `Autenticacao` (Filtro de permissões RBAC e Gestão de Sessão).
3.  **Processamento:** `Chamados` / `Agenda` (Execução da regra de negócio solicitada).
4.  **Auditoria:** `BaseModel` (Registro automático de autor, timestamp e IP Real).
5.  **Persistência:** `SQLAlchemy` (Escrita segura e íntegra na base de dados).

---

## Segurança de Nível Corporativo (Layer Hard)

O HelpHub 4.0 implementa múltiplas camadas de proteção independentes para garantir a integridade e a segurança dos dados em todos os níveis da aplicação:

- **Validação de Integridade Binária:** O `UploadManager` ignora a extensão do arquivo e realiza uma inspeção profunda nos **Magic Numbers** (assinatura real do arquivo via `filetype`). Isso impede que scripts maliciosos sejam camuflados como imagens.
- **Escudo Anti-BruteForce:** Proteção ativa via `Flask-Limiter` com rastreamento de **IP Real** (através de headers de proxy). Limites rigorosos são aplicados em rotas de autenticação e APIs críticas.
- **Ofuscação de Dados (UUIDv4):** IDs sequenciais foram abolidos. O uso de identificadores universais únicos (UUID) impede ataques de enumeração direta e exposição estratégica de volume de dados por URL.
- **Isolamento Físico de Ativos:** Arquivos sensíveis do sistema (Logs e Backups) residem em diretórios fisicamente isolados da pasta de uploads de clientes, impedindo o acesso indevido a arquivos através da exploração de caminhos de diretórios.
- **Autorização Granular (RBAC):** Controle de acesso baseado em funções com decoradores `@admin_required` protegendo todas as endpoints de infraestrutura e governança.

---

## 🛠️ Tecnologias Utilizadas

O HelpHub 4.0 foi construído com ferramentas modernas que garantem rapidez, segurança e um visual profissional:

### ⚙️ Backend (O Coração do Sistema)

- **Flask:** Estrutura principal que sustenta todo o sistema.
- **SQLAlchemy:** Responsável por organizar e salvar todas as informações no banco de dados.
- **Segurança Pró-Ativa:** Ferramentas para controle de acesso, proteção de sessões e limites contra tentativas de invasão.
- **APScheduler:** O "robô" que executa tarefas automáticas, como backups e fechamento de chamados.
- **Arrow & Filetype:** Controle preciso de horários e verificação rigorosa de arquivos enviados.

### 🎨 Frontend (Interface e Visual)

- **Jinja2:** Sistema que organiza as páginas do site de forma eficiente.
- **Alpine.js:** Permite que o sistema responda instantaneamente aos comandos, sem precisar recarregar a página.
- **ApexCharts:** Gera os gráficos interativos para acompanhamento de resultados.
- **FullCalendar:** Calendário completo para organização das visitas técnicas.
- **Design Moderno:** Visual elegante que se adapta a computadores e celulares, com foco na facilidade de uso.

---

## 🤖 Agendador de Tarefas e Automação (Deep Dive)

Seu agendador de tarefas (`APScheduler`), que opera de forma autônoma e resiliente:

### 🕒 Rotinas Automatizadas

- **Backup Diário (03:00 AM):** Geração automática de dump do banco SQLite com rotação inteligente (mantém apenas os últimos 14 backups para economizar disco).
- **Zelador de Chamados (03:05 AM):** Varredura de tickets em status "Pendente". Chamados sem interação por mais de 48 horas são encerrados automaticamente com assinatura de sistema.

### 🛡️ Monitoramento e Resiliência

- **Decorador `@monitorar_tarefa`:** Registra o status de sucesso ou erro, tempo de execução e mensagens de retorno de cada rotina no banco de dados.
- **Detecção de Servidor Offline:** Caso o servidor tenha ficado desligado durante o horário das tarefas (ex: manutenção de infra), o sistema detecta a falha no próximo boot e apresenta um **Alerta Crítico** no Dashboard para o administrador.

---

## 📋 Principais Módulos do Sistema

### 📊 Painel de Controle e Estatísticas

- **Indicadores Instantâneos:** Visualização imediata da quantidade de clientes e do status de todos os chamados (abertos, agendados e pendentes).
- **Histórico de Atendimentos:** Gráfico dinâmico que mostra a evolução dos registros ao longo do tempo, com recursos de zoom e navegação detalhada.
- **Distribuição por Status:** Gráfico de Pizza dinâmico que permite filtrar a listagem de chamados com um clique.
- **Volume por Departamento:** Gráfico de Barras horizontais para identificação de gargalos operacionais.
- **Agenda de Hoje:** Visualização rápida do progresso das visitas técnicas programadas para o dia atual.

### 🎫 Gestão de Atendimentos

- **Linha do Tempo de Interações:** Histórico detalhado que separa mensagens do técnico, do cliente e registros automáticos do sistema.
- **Número de Protocolo:** Gerado automaticamente para facilitar o rastreio (ex: `YYYYMMDD-XXXX`).
- **Transferência entre Níveis:** Permite mover chamados entre diferentes equipes ou níveis de suporte técnico.
- **Impressão de Ordem de Serviço:** Gerador de documento em formato A4 personalizado, com campos para assinatura e anotações de campo.

### 📅 Agenda Técnica

- **Prevenção de Conflitos:** O sistema impede automaticamente que dois serviços sejam agendados para o mesmo técnico no mesmo horário.
- **Avisos de Atraso:** Destaque visual em cores para identificar rapidamente visitas que estão fora do horário previsto.
- **Flexibilidade de Horários:** Facilidade para reorganizar visitas com atualização imediata no histórico do chamado.
- **Ordem de Serviço Pronta para Imprimir:** Documento formatado para impressão rápida com os dados do cliente e do serviço.

### 👥 Perfil 360º de Clientes

- **Repositório Contratual:** Upload e gestão de documentos (PDF/Imagens) com isolamento físico por UUID.
- **Dashboard do Cliente:** Visualização instantânea de métricas de chamados, última visita e histórico financeiro/técnico.
- **Busca Global Cruzada:** Localização ultrarápida por Nome, Fantasia ou CPF/CNPJ parcial.

### ⚙️ Administração do Sistema

- **Auditoria Simplificada:** Ferramenta que lê os registros do sistema e os organiza em uma tabela fácil de consultar, com filtros por tipo de evento.
- **Gestão de Identidade:** Painel central para alterar a logo, o nome da empresa e outros dados que aparecem nos relatórios e nas ordens de serviço.
- **Verificação de Saúde:** Monitoramento automático que garante que o banco de dados e as pastas do sistema estão prontos para o uso.

---

## ✨ Recursos Adicionais

- **Instalação Automática:** No primeiro acesso, o sistema cria sozinho todas as pastas e o banco de dados necessários.
- **Páginas de Erro Personalizadas:** Visual exclusivo para erros de acesso ou páginas não encontradas, mantendo a identidade do sistema.

---

## 🧪 Suite de Testes e QA (Garantia de Estabilidade)

O HelpHub 4.0 conta com uma infraestrutura de testes de última geração, garantindo que cada linha de código seja validada antes do deploy.

<div align="center">
  
  [![Test Suite](https://img.shields.io/badge/Status-100%25%20Passed-success?style=for-the-badge&logo=pytest)](tests/)
  [![Coverage](https://img.shields.io/badge/Coverage-89%25-blue?style=for-the-badge&logo=codecov)](tests/)
  [![Cenários](https://img.shields.io/badge/Cenários-105%20Validados-orange?style=for-the-badge)](tests/)

</div>

### 📊 Desempenho da Última Bateria

O sistema passou por uma bateria exaustiva de testes funcionais, unitários e de integração em ambiente Windows 11.

| Categoria      | Arquivos | Cenários |   Status    |
| :------------- | :------: | :------: | :---------: |
| **Funcionais** |    13    |    64    | ✅ Sucesso  |
| **Unitários**  |    9     |    39    | ✅ Sucesso  |
| **Integração** |    3     |    2     | ✅ Sucesso  |
| **Total**      |  **25**  | **105**  | **100% OK** |

<details>
<summary>📂 <b>CLIQUE PARA VER O RELATÓRIO TÉCNICO COMPLETO (PYTEST)</b></summary>
<br>

```text
============================================================
 INICIANDO BATERIA DE TESTES - HELPHUB 4.0
============================================================
collected 105 items

tests\functional\test_admin_config.py .......                                   [  6%]
tests\functional\test_agenda.py .                                               [  7%]
tests\functional\test_auth.py ..                                                [  9%]
tests\functional\test_busca_global.py ...                                       [ 12%]
tests\functional\test_chamados.py ..........                                    [ 21%]
tests\functional\test_clientes.py ...........                                   [ 32%]
tests\functional\test_dashboard.py .                                            [ 33%]
tests\functional\test_departamentos.py ..........                               [ 42%]
tests\functional\test_impressao_os.py .                                         [ 43%]
tests\functional\test_seguranca.py ...                                          [ 46%]
tests\functional\test_seguranca_autorizacao.py .                                [ 47%]
tests\functional\test_user_management.py ......                                 [ 53%]
tests\functional\test_workflow_chamados.py ...                                  [ 56%]
tests\integration\test_full_lifecycle.py ..                                     [ 58%]
tests\unit\test_adm_servicos.py ..                                              [ 60%]
tests\unit\test_agenda_api.py ..                                                [ 61%]
tests\unit\test_agendador.py ......                                             [ 67%]
tests\unit\test_app_init.py ..                                                  [ 69%]
tests\unit\test_auth_routes.py .........                                        [ 78%]
tests\unit\test_logging.py ..                                                   [ 80%]
tests\unit\test_models.py .......                                               [ 86%]
tests\unit\test_upload_manager.py ...........                                   [ 97%]
tests\unit\test_utils.py ...                                                    [100%]

-------------------------------------------------------------------------------------
TOTAL COBERTURA: 89% (1253 Stmts | 111 Miss)
========================== 105 passed in 34.62s ==========================
```

</details>

<br>

**Para executar o ecossistema de testes localmente:**

```bash
python tests/iniciar_testes.py
```

---

## Instalação e Primeiro Uso

1.  Clone o repositório.
2.  Instale as dependências: `pip install -r requirements.txt`.
3.  Configure o fuso horário em `App/configurar.py` (Default: America/Sao_Paulo).
4.  Rode o sistema: `python debug.py`.
5.  **Acesse:** `http://localhost:5000`. O usuário `admin` e senha `admin123` são criados automaticamente se a base for virgem.

---

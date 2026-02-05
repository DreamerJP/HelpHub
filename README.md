# HelpHub 4.1 - Sistema de Gestão de Chamados e Assistência Técnica

![HelpHub Banner](https://img.shields.io/badge/HelpHub-4.1-blue?style=for-the-badge&logo=flask)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Flask 3.0.0](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![License Non-Commercial](https://img.shields.io/badge/License-Non--Commercial-orange.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/Tests-135%20Passados-success)](tests/)

Plataforma corporativa de alto desempenho para gestão de tickets, assistência técnica e planejamento logístico. Construída com foco em segurança, escalabilidade modular e experiência premium do usuário.

---

## Arquitetura

**Application Factory** com **Screaming Architecture** - Estrutura modular baseada em Blueprints que revela a intenção do sistema e facilita manutenção em larga escala.

### Estrutura de Camadas

| Camada         | Escopo        | Responsabilidade                                                          |
|:---------------|:--------------|:--------------------------------------------------------------------------|
| **BOOT**       | `App/`        | Inicialização do Flask, Registro de Blueprints e Engine de Logs          |
| **LOGIC**      | `Modulos/`    | Core de Negócio: Chamados, Agendas, Clientes e Autenticação (RBAC)       |
| **SERVICE**    | `servicos/`   | Motores de Notificação, Criptografia (AES-256), Segurança e Uploads      |
| **INFRA**      | `Data/`       | Persistência (SQLite/MySQL), Logs de Auditoria e Repositório de Arquivos |

### Ciclo de Vida da Requisição

```
Escudo (Rate-Limit/CSRF) → Autenticação (RBAC) → Processamento (Lógica de Negócio) 
→ Auditoria (Logs com IP Real) → Persistência (SQLAlchemy)
```

### Gestão de Migrations

Sistema de versionamento do banco de dados que permite evoluir a estrutura sem perda de dados:

```bash
# Detectar mudanças
flask db migrate -d App/migrations -m "descrição da mudança"

# Aplicar ao banco
flask db upgrade -d App/migrations
```

---

## Recursos Principais

### HelpHub Live Sync

Sistema de sincronização passiva que mantém dashboards e grids atualizados automaticamente:

- **Backend:** Tabela `SyncControl` com versões incrementais por entidade
- **Frontend:** Heartbeat a cada 30s via AJAX verificando mudanças
- **Dashboard:** Recarregamento automático ao detectar alterações
- **Grids:** Refresh suave com notificação Toast ao usuário

### Central de Integrações (Multi-Canal)

Hub centralizado para comunicação e alertas automáticos com foco em segurança:

- **Canais:** Suporte nativo para Telegram Bot, E-mail (SMTP) e WhatsApp Business (API Evolution)
- **Criptografia AES-256:** Todas as credenciais e tokens são armazenados encriptados no banco de dados
- **Testes em Tempo Real:** Painel administrativo para validação de conectividade antes do deploy
- **Notificações Inteligentes:** Disparo automático de alertas para técnicos e administradores

### Gestão de Tickets

- Linha do tempo separando interações técnico/cliente/sistema
- Protocolos únicos e seguros gerados automaticamente
- Atribuição automática de técnico ao interagir (workflow self-service)
- Transferência entre níveis de suporte
- Impressão de Ordem de Serviço em formato A4
- Sincronização em tempo real entre usuários

### Agenda Técnica

- Prevenção automática de conflitos de horário
- Calendário interativo com drag-and-drop (FullCalendar)
- Avisos visuais para atrasos e prioridades críticas
- Ordem de Serviço pronta para impressão

### Dashboard e Estatísticas

- Indicadores instantâneos com atualização automática via Live Sync
- Gráficos dinâmicos com zoom e navegação detalhada (ApexCharts)
- Distribuição por status com filtro por clique
- Volume por departamento para identificação de gargalos
- Progresso de visitas técnicas do dia

### Perfil 360º de Clientes

- Repositório contratual com isolamento físico por UUID
- Dashboard individual com métricas e histórico
- Busca global cruzada (Nome/Fantasia/CPF/CNPJ)
- Validação de integridade binária em uploads

### Administração

- Auditoria com rastreamento de IP Real
- Gestão de identidade (logo, nome da empresa)
- Configuração segura de integrações (credenciais criptografadas)
- Verificação de saúde do sistema
- Monitor de tarefas agendadas

---

## Segurança Corporativa

### Proteção de Dados

- **Criptografia AES-256 (Fernet):** Credenciais sensíveis (SMTP, Telegram, WhatsApp) armazenadas encriptadas. Arquivo `.db` roubado é inútil sem a chave de criptografia
- **Ofuscação com UUIDv4:** IDs sequenciais abolidos para impedir enumeração e exposição de volume
- **Isolamento Físico:** Logs e backups separados dos uploads de clientes

### Proteção de Arquivos

- **Validação Binária:** Inspeção de Magic Numbers via `filetype`, ignorando extensões falsas
- **Proteção Anti-Freeze:** Interceptador de colagem que trunca textos massivos e previne travamento do navegador

### Proteção de Acesso

- **Anti-BruteForce:** Flask-Limiter com rastreamento de IP Real (bypass de proxy)
- **RBAC Granular:** Controle de acesso baseado em funções com decoradores `@admin_required`
- **Auditoria Completa:** Logs automáticos de autor, timestamp e IP Real em todas as operações

---

## Automação e Resiliência

### Tarefas Agendadas (APScheduler)

- **Backup Diário (03:00):** Dump automático com rotação inteligente (últimos 14 backups)
- **Zelador de Chamados (03:05):** Encerramento automático de tickets pendentes >48h

### Monitoramento

- Decorador `@monitorar_tarefa` registra execução, status e tempo de cada rotina
- Detecção de servidor offline com alerta crítico no Dashboard
- Verificação automática de saúde do sistema

---

## Stack Tecnológica

### Backend

![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red?logo=python)
![APScheduler](https://img.shields.io/badge/APScheduler-Automation-orange)

- **Flask 3.0:** Framework web principal
- **SQLAlchemy:** ORM com suporte a SQLite/MySQL/PostgreSQL
- **Flask-Limiter:** Proteção anti-bruteforce
- **Flask-Migrate:** Sistema de migrations
- **Cryptography (Fernet):** Criptografia industrial AES-256
- **APScheduler:** Agendador de tarefas automáticas
- **Arrow:** Manipulação precisa de datas/horários
- **Filetype:** Validação de integridade binária

### Frontend

![Alpine.js](https://img.shields.io/badge/Alpine.js-Reactive-8BC0D0?logo=alpinedotjs)
![Jinja2](https://img.shields.io/badge/Jinja2-Templates-B41717?logo=jinja)

- **Jinja2:** Template engine
- **Alpine.js:** Reatividade e Live Sync
- **ApexCharts:** Gráficos interativos
- **FullCalendar:** Calendário com drag-and-drop
- **Design System:** CSS moderno responsivo

### Bancos de Dados

![SQLite](https://img.shields.io/badge/SQLite-Dev-003B57?logo=sqlite)
![MySQL](https://img.shields.io/badge/MySQL-Production-4479A1?logo=mysql)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Compatible-4169E1?logo=postgresql)

- **SQLite:** Desenvolvimento e pequenas instalações (zero config)
- **MySQL/MariaDB:** Produção e alta performance
- **PostgreSQL:** Totalmente compatível via SQLAlchemy

Transição entre bancos por simples alteração de URI, sem mudanças no código.

---

## Testes e Qualidade

<div align="center">

[![Test Suite](https://img.shields.io/badge/Status-100%25%20Passed-success?style=for-the-badge&logo=pytest)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-87%25-green?style=for-the-badge&logo=codecov)](tests/)
[![Cenários](https://img.shields.io/badge/Cenários-135%20Validados-orange?style=for-the-badge)](tests/)

</div>

### Cobertura Completa

| Categoria      | Cenários | Status      |
|:---------------|:--------:|:------------|
| Funcionais     | 84       | ✅ Sucesso  |
| Unitários      | 46       | ✅ Sucesso  |
| Integração     | 5        | ✅ Sucesso  |
| **Total**      | **135**  | **100% OK** |

**Executar testes:** `python tests/iniciar_testes.py`

---

## Instalação Rápida

```bash
# 1. Clone o repositório
git clone [url-do-repositorio]

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure fuso horário (opcional)
# Edite App/configurar.py (default: America/Sao_Paulo)

# 4. Execute
python debug.py

# 5. Acesse
http://localhost:5000
# Usuário: admin | Senha: admin123 (criados automaticamente)
```

### Migração para MySQL (Produção)

<details>
<summary>Expandir tutorial de migração</summary>

```sql
-- 1. Crie o database
CREATE DATABASE helphub_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```python
# 2. Configure URI em App/configurar.py
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://usuario:senha@localhost/helphub_prod"
```

```bash
# 3. Aplique migrations
$env:FLASK_APP="debug.py"
flask db upgrade -d App/migrations
```

**Migração de dados:** Use DBeaver ou DB Browser for SQLite (Exportar/Importar)

</details>

---

## Recursos Adicionais

- **Instalação Zero-Config:** Criação automática de pastas e banco de dados no primeiro acesso
- **Páginas de Erro Personalizadas:** Interface consistente mesmo em erros 404/403
- **Proteção DoS via UI:** Prevenção automática contra travamento do navegador
- **Logs Estruturados:** Sistema completo de auditoria com rastreamento de IP Real

---

## Licença

[![License Non-Commercial](https://img.shields.io/badge/License-Non--Commercial-orange.svg)](LICENSE)

Este projeto está sob licença de uso não-comercial. Consulte o arquivo LICENSE para detalhes.

---

<div align="center">

**HelpHub 4.1** - Gestão Profissional de Chamados e Assistência Técnica

![Made with Flask](https://img.shields.io/badge/Made%20with-Flask-black?logo=flask)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![Tested](https://img.shields.io/badge/Tests-135%20Passing-success?logo=pytest)

</div>
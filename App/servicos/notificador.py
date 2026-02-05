import threading
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from App.Modulos.Administracao.modelo import Configuracao


class Notificador:
    """
    Hub Central de Notificações.
    Abstrai o envio para múltiplos canais (Telegram, Email, WhatsApp).
    """

    @staticmethod
    def notify_new_ticket(chamado):
        """
        Gatilho disparado quando um novo chamado é criado.
        Agora executa em SEGUNDO PLANO (Async) para não travar o usuário.
        """
        # Capturamos os dados necessários antes de disparar a thread
        # para evitar problemas de sessão do banco de dados (SQLAlchemy)
        app = current_app._get_current_object()
        data = {
            "protocolo": chamado.protocolo,
            "assunto": chamado.assunto,
            "cliente_nome": chamado.cliente.nome_razao,
            "prioridade": chamado.prioridade,
            "depto_nome": chamado.departamento.nome
            if chamado.departamento
            else "Geral",
            "depto_email": (
                chamado.departamento.email_notificacao if chamado.departamento else None
            ),
            "descricao": chamado.descricao,
        }

        # Dispara a thread de processamento
        thread = threading.Thread(
            target=Notificador._run_notify_async, args=(app, data)
        )
        thread.start()

    @staticmethod
    def _run_notify_async(app, data):
        """Worker que processa todos os envios de forma assíncrona."""
        from App.Modulos.Administracao.modelo import TarefaMonitor

        with app.app_context():
            try:
                config = Configuracao.get_config()
                erros = []

                # 1. Preparar a mensagem
                subject = f"🔔 Novo Chamado: #{data['protocolo']}"
                body = (
                    f"Assunto: {data['assunto']}\n"
                    f"Cliente: {data['cliente_nome']}\n"
                    f"Prioridade: {data['prioridade']}\n"
                    f"Departamento: {data['depto_nome']}\n"
                    f"\nDescrição:\n{data['descricao'][:200]}..."
                )

                # 2. Telegram (Equipe)
                if config.telegram_ativo and config.telegram_token:
                    from App.servicos.criptografia import decriptar

                    token_limpo = decriptar(config.telegram_token)
                    chat_id = config.telegram_chat_id
                    if chat_id:
                        try:
                            Notificador._send_telegram(
                                token_limpo, chat_id, f"{subject}\n\n{body}"
                            )
                            TarefaMonitor.atualizar(
                                "notificacao_telegram",
                                "Telegram",
                                "Sucesso",
                                "Envio OK",
                            )
                        except Exception as e:
                            msg_erro = f"Erro Telegram: {str(e)}"
                            erros.append(msg_erro)
                            TarefaMonitor.atualizar(
                                "notificacao_telegram", "Telegram", "Erro", msg_erro
                            )

                # 3. Email (Notificação de Departamento)
                if config.email_ativo and data["depto_email"]:
                    try:
                        Notificador._send_email(
                            config, data["depto_email"], subject, body
                        )
                        TarefaMonitor.atualizar(
                            "notificacao_email", "E-mail", "Sucesso", "Envio OK"
                        )
                    except Exception as e:
                        msg_erro = f"Erro E-mail: {str(e)}"
                        erros.append(msg_erro)
                        TarefaMonitor.atualizar(
                            "notificacao_email", "E-mail", "Erro", msg_erro
                        )

                # 4. WhatsApp (Equipe/Universal)
                if (
                    config.whatsapp_ativo
                    and config.whatsapp_api_url
                    and config.whatsapp_key
                ):
                    try:
                        wa_message = (
                            f"*🔔 Novo Chamado: #{data['protocolo']}*\n\n{body}"
                        )
                        Notificador._send_whatsapp(config, wa_message)
                        TarefaMonitor.atualizar(
                            "notificacao_whatsapp", "WhatsApp", "Sucesso", "Envio OK"
                        )
                    except Exception as e:
                        msg_erro = f"Erro WhatsApp: {str(e)}"
                        erros.append(msg_erro)
                        TarefaMonitor.atualizar(
                            "notificacao_whatsapp", "WhatsApp", "Erro", msg_erro
                        )

                if erros:
                    app.logger.warning(
                        f"Falha em alguns canais de notificação: {', '.join(erros)}"
                    )

            except Exception as e:
                app.logger.error(f"Erro crítico no Hub de Notificações (Async): {e}")

    @staticmethod
    def _send_whatsapp(config, message, destination=None):
        """
        Envio via API WhatsApp Universal (Evolution API, Z-API, etc).
        Envia para o destino fornecido ou tenta extrair do contexto (ex: grupo da empresa).
        """
        if not config.whatsapp_api_url or not config.whatsapp_key:
            return

        from App.servicos.criptografia import decriptar

        key_limpa = decriptar(config.whatsapp_key)

        try:
            # O padrão da Evolution API e similares costuma ser:
            # POST {URL}/message/sendText
            # Headers: apikey: {KEY}
            url = f"{config.whatsapp_api_url.rstrip('/')}/message/sendText"
            headers = {
                "apikey": key_limpa,
                "Content-Type": "application/json",
            }

            # Nota: O destino aqui é fixo para teste/equipe, expansível no futuro
            # Se não houver destination, poderíamos pegar um ID de grupo padrão
            payload = {
                "number": destination or "SISTEMA",  # ID do Grupo ou Número
                "text": message,
            }

            # Execução Real via API
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            current_app.logger.info(f"WhatsApp enviado para {payload['number']}")

        except Exception as e:
            current_app.logger.error(f"Erro ao disparar WhatsApp: {str(e)}")
            raise e

    @staticmethod
    def _send_telegram(token, chat_ids, message):
        """Envio real via API do Telegram (Suporta múltiplos IDs separados por vírgula ou espaço)"""
        if not chat_ids:
            return

        # Normaliza para lista de IDs
        ids = [i.strip() for i in str(chat_ids).replace(",", " ").split() if i.strip()]

        for cid in ids:
            try:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {"chat_id": cid, "text": message, "parse_mode": "Markdown"}
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
            except Exception as e:
                current_app.logger.error(
                    f"Erro ao enviar Telegram para {cid}: {str(e)}"
                )
                raise e

    @staticmethod
    def _send_email(config, to_email, subject, body):
        """Envio real via SMTP (Semipronto/Protegido)"""
        # Só executa se houver servidor configurado
        if not config.email_smtp_server or not config.email_user:
            return

        from App.servicos.criptografia import decriptar

        password_limpa = decriptar(config.email_password)

        try:
            msg = MIMEMultipart()
            msg["From"] = config.email_user
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            porta = int(config.email_smtp_port)
            # Motor Inteligente: SSL Direto vs STARTTLS
            if porta == 465:
                server = smtplib.SMTP_SSL(config.email_smtp_server, porta, timeout=15)
            else:
                server = smtplib.SMTP(config.email_smtp_server, porta, timeout=15)
                server.starttls()

            with server:
                server.login(config.email_user, password_limpa)
                server.send_message(msg)

            current_app.logger.info(f"Email enviado para {to_email}")
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar Email: {str(e)}")
            raise e

    @staticmethod
    def test_telegram(token, chat_ids):
        """Função para teste rápido nas configurações (Suporta múltiplos IDs)"""
        from App.Modulos.Administracao.modelo import TarefaMonitor

        msg = "*HelpHub 4.1:* Conexão com Telegram estabelecida com sucesso!"

        if not chat_ids:
            return False, "Nenhum Chat ID fornecido."

        ids = [i.strip() for i in str(chat_ids).replace(",", " ").split() if i.strip()]
        erros = []
        sucessos = 0

        for cid in ids:
            try:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {"chat_id": cid, "text": msg, "parse_mode": "Markdown"}
                response = requests.post(url, json=payload, timeout=5)
                if response.ok:
                    sucessos += 1
                else:
                    erros.append(
                        f"ID {cid}: {response.json().get('description', 'Erro desconhecido')}"
                    )
            except Exception as e:
                erros.append(f"ID {cid}: {str(e)}")

        if sucessos == len(ids):
            TarefaMonitor.atualizar(
                "notificacao_telegram", "Telegram", "Sucesso", "Teste OK"
            )
            return True, f"Teste enviado com sucesso para {sucessos} chats!"
        elif sucessos > 0:
            return (
                True,
                f"Enviado para {sucessos}, mas falhou em alguns: {', '.join(erros)}",
            )
        else:
            return False, f"Falha total: {'; '.join(erros)}"

    @staticmethod
    def test_email(host, port, user, password):
        """Função para teste rápido de SMTP nas configurações (Suporta SSL e STARTTLS)"""
        from App.Modulos.Administracao.modelo import TarefaMonitor

        subject = "HelpHub 4.1: Teste de Conexão SMTP"
        body = "Se você está lendo isso, sua configuração de e-mail no HelpHub 4.1 está funcionando perfeitamente!"

        try:
            msg = MIMEMultipart()
            msg["From"] = user
            msg["To"] = user
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            porta = int(port)
            # Inteligência de Conexão: SSL Direto vs STARTTLS
            if porta == 465:
                server = smtplib.SMTP_SSL(host, porta, timeout=10)
            else:
                server = smtplib.SMTP(host, porta, timeout=10)
                server.starttls()

            with server:
                server.login(user, password)
                server.send_message(msg)

            TarefaMonitor.atualizar(
                "notificacao_email", "E-mail", "Sucesso", "Teste OK"
            )
            return True, "E-mail de teste enviado com sucesso!"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def test_whatsapp(url, key, destination):
        """Função para teste rápido de WhatsApp nas configurações"""
        from App.Modulos.Administracao.modelo import TarefaMonitor

        msg = "*HelpHub 4.1:* Conexão com WhatsApp estabelecida com sucesso!"

        try:
            # Reutiliza a lógica interna de envio
            class MockConfig:
                def __init__(self, url, key):
                    self.whatsapp_api_url = url
                    self.whatsapp_key = key

            Notificador._send_whatsapp(MockConfig(url, key), msg, destination)

            TarefaMonitor.atualizar(
                "notificacao_whatsapp", "WhatsApp", "Sucesso", "Teste OK"
            )
            return True, "WhatsApp de teste enviado com sucesso!"
        except Exception as e:
            return False, str(e)

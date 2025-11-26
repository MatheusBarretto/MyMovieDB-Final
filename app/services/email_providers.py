from abc import ABC, abstractmethod
from typing import Any, Dict, List

from flask import current_app

from .email_models import EmailMessage, EmailResult


class EmailProviderError(Exception):
    """    Exceção base para erros de provedores de email.
    """
    pass


class EmailProvider(ABC):
    """Interface abstrata para provedores de email.
    """

    @abstractmethod
    def send(self, message: EmailMessage) -> EmailResult:
        """Envia um email usando o provedor.

        Args:
            message (EmailMessage): Mensagem a ser enviada.

        Returns:
            EmailResult: Resultado do envio com informações do provedor.

        Raises:
            EmailProviderError: Em caso de erro no envio.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna o nome do provedor.

        Returns:
            str: Nome do provedor.
        """
        pass


class PostmarkProvider(EmailProvider):
    """Provedor de email usando o Postmark.
    """

    def __init__(self, api_key: str):
        """Inicializa o provedor Postmark.

        Args:
            api_key (str): Chave da API do Postmark.

        Raises:
            ValueError: Se a chave da API for inválida.
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("A chave da API do Postmark é obrigatória e deve ser uma string.")
        self._api_key = api_key

    def send(self, message: EmailMessage) -> EmailResult:
        """Envia um email usando o Postmark.

        Args:
            message (EmailMessage): Mensagem a ser enviada.

        Returns:
            EmailResult: Resultado do envio com informações do Postmark.

        Raises:
            EmailProviderError: Em caso de erro no envio.
        """
        try:
            from postmarker.core import PostmarkClient

            client = PostmarkClient(server_token=self._api_key)

            # Monta o email para Postmark
            email_data = {
                'From'   : message.from_email,
                'To'     : message.to,
                'Subject': message.subject,
            }

            # Adiciona corpo do email
            if message.text_body:
                email_data['TextBody'] = message.text_body
            if message.html_body:
                email_data['HtmlBody'] = message.html_body

            # Campos opcionais
            if message.reply_to:
                email_data['ReplyTo'] = message.reply_to
            if message.cc:
                email_data['Cc'] = ', '.join(message.cc)
            if message.bcc:
                email_data['Bcc'] = ', '.join(message.bcc)

            email_obj = client.emails.Email(**email_data)
            response = email_obj.send()

            if response.get('ErrorCode', 0) != 0:
                raise EmailProviderError(
                        f"Erro Postmark: {response.get('Message', 'Erro desconhecido')}")

            return EmailResult(
                    success=True,
                    provider='postmark',
                    message_id=response.get('MessageID'),
                    to=response.get('To'),
                    sent_at=response.get('SubmittedAt'),
                    error_code=response.get('ErrorCode', 0),
                    raw_response=response
            )

        except ImportError:
            raise EmailProviderError("Biblioteca postmarker não instalada")
        except Exception as e:
            raise EmailProviderError(f"Erro ao enviar via Postmark: {str(e)}") from e

    def get_provider_name(self) -> str:
        return "Postmark"


class SMTPProvider(EmailProvider):
    """Provedor de email usando SMTP padrão.
    """

    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str,
                 use_tls: bool = True):
        """Inicializa o provedor SMTP.

        Args:
            smtp_server (str): Endereço do servidor SMTP (ex: "smtp.gmail.com").
            smtp_port (int): Porta do servidor SMTP (geralmente 587 para TLS ou 465 para SSL).
            username (str): Nome de usuário para autenticação SMTP.
            password (str): Senha para autenticação SMTP.
            use_tls (bool): Se True, utiliza TLS para conexão segura. Padrão: True.
        """
        self._smtp_server = smtp_server
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._use_tls = use_tls

    def send(self, message: EmailMessage) -> EmailResult:
        """Envia email via SMTP.

        Args:
            message (EmailMessage): Mensagem a ser enviada.

        Returns:
            EmailResult: Resultado do envio.

        Raises:
            EmailProviderError: Em caso de erro no envio.
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders
            import uuid

            # Cria a mensagem
            if message.html_body and message.text_body:
                msg = MIMEMultipart('alternative')
            else:
                msg = MIMEMultipart()

            msg['From'] = message.from_email
            msg['To'] = message.to
            msg['Subject'] = message.subject

            if message.reply_to:
                msg['Reply-To'] = message.reply_to
            if message.cc:
                msg['Cc'] = ', '.join(message.cc)

            # Adiciona corpos
            if message.text_body:
                msg.attach(MIMEText(message.text_body, 'plain', 'utf-8'))
            if message.html_body:
                msg.attach(MIMEText(message.html_body, 'html', 'utf-8'))

            # Conecta ao servidor SMTP
            server = smtplib.SMTP(self._smtp_server, self._smtp_port)

            if self._use_tls:
                server.starttls()

            server.login(self._username, self._password)

            # Lista de destinatários
            recipients = [message.to]
            if message.cc:
                recipients.extend(message.cc)
            if message.bcc:
                recipients.extend(message.bcc)

            # Envia
            result = server.send_message(msg, to_addrs=recipients)
            server.quit()

            message_id = str(uuid.uuid4())

            return EmailResult(
                    success=True,
                    provider='smtp',
                    message_id=message_id,
                    to=message.to,
                    raw_response=result
            )

        except Exception as e:
            raise EmailProviderError(f"Erro ao enviar via SMTP: {str(e)}") from e

    def get_provider_name(self) -> str:
        return f"SMTP ({self._smtp_server})"


class MockProvider(EmailProvider):
    """Provedor mock para desenvolvimento/testes.
    """

    def __init__(self, log_emails: bool = True):
        """Inicializa o provedor mock.

        Args:
            log_emails (bool): Se True, registra emails nos logs da aplicação. Padrão: True.
        """
        self.log_emails = log_emails
        self.sent_emails = []  # Para testes

    def send(self, message: EmailMessage) -> EmailResult:
        """Simula envio de email.

        Args:
            message (EmailMessage): Mensagem a ser enviada.

        Returns:
            EmailResult: Resultado simulado do envio.
        """
        import uuid
        from datetime import datetime

        message_id = str(uuid.uuid4())

        email_info = {
            'message_id': message_id,
            'from'      : message.from_email,
            'to'        : message.to,
            'subject'   : message.subject,
            'text_body' : message.text_body,
            'html_body' : message.html_body,
            'sent_at'   : datetime.now().isoformat(),
        }

        self.sent_emails.append(email_info)

        if self.log_emails:
            current_app.logger.debug("=== EMAIL SIMULADO ===")
            current_app.logger.debug("From: %s" % (message.from_email))
            current_app.logger.debug("To: %s" % (message.to))
            current_app.logger.debug("Subject: %s" % (message.subject))
            current_app.logger.debug("--- Text Body ---")
            current_app.logger.debug(message.text_body or "(vazio)")
            if message.html_body:
                current_app.logger.debug("--- HTML Body ---")
                current_app.logger.debug(message.html_body)
            current_app.logger.debug("===================")

        return EmailResult(
                success=True,
                provider='mock',
                message_id=message_id,
                to=message.to,
                sent_at=email_info['sent_at']
        )

    def get_provider_name(self) -> str:
        return "Mock (Development)"

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """Retorna lista de emails enviados (para testes).

        Returns:
            typing.List[typing.Dict[str, typing.Any]]: Lista de emails enviados.
        """
        return self.sent_emails.copy()

    def clear_sent_emails(self):
        """Limpa lista de emails enviados (útil para testes)."""
        self.sent_emails.clear()

"""Serviço de envio e validação de emails.

Este módulo fornece funcionalidades para envio de emails através de múltiplos provedores
(Postmark, SMTP, Mock) e validação de endereços de email.

Classes principais:
    - EmailService: Serviço principal para envio de emails
    - EmailValidationService: Utilitários para validação e normalização de emails
"""
from typing import Any, Dict, Optional

from flask import current_app

from .email_models import EmailMessage, EmailResult
from .email_providers import EmailProvider, MockProvider, PostmarkProvider, SMTPProvider


class EmailValidationService:
    """Serviço responsável pela validação de um endereco de email.
    """

    @staticmethod
    def is_valid(email: str) -> bool:
        """Valida o formato do endereço de email.

        Args:
            email (str): Endereço de email a ser validado.

        Returns:
            bool: True se o formato do email for válido, False caso contrário.
        """
        from email_validator import validate_email
        from email_validator.exceptions import EmailNotValidError, EmailSyntaxError
        try:
            validado = validate_email(email, check_deliverability=False)
            return validado is not None
        except (EmailNotValidError, EmailSyntaxError, TypeError):
            return False

    @staticmethod
    def normalize(email: str) -> str:
        """Normaliza o endereço de email.

        Args:
            email (str): Endereço de email a ser normalizado.

        Returns:
            str: Endereço de email normalizado.

        Raises:
            ValueError: Se o email for inválido.
        """
        from email_validator import validate_email
        from email_validator.exceptions import EmailNotValidError, EmailSyntaxError
        try:
            validado = validate_email(email, check_deliverability=False)
            return validado.normalized.lower()
        except (EmailNotValidError, EmailSyntaxError, TypeError) as e:
            raise ValueError("Endereço de email inválido.") from e


class EmailService:
    """Serviço principal para envio de emails.
    """

    def __init__(self,
                 provider: EmailProvider,
                 default_from_email: str,
                 default_from_name: str = None):
        """Inicializa o serviço de email.

        Args:
            provider (EmailProvider): Provedor de email a ser utilizado (Postmark, SMTP ou Mock).
            default_from_email (str): Endereço de email remetente padrão.
            default_from_name (str): Nome do remetente padrão. Se None, usa apenas o email.
        """
        self.provider = provider
        self.default_from_email = default_from_email
        self.default_from_name = default_from_name

    @classmethod
    def create_from_config(cls, app_config: Dict[str, Any]) -> 'EmailService':
        """Cria instância do EmailService a partir da configuração da aplicação.

        Args:
            app_config (typing.Dict[str, typing.Any]): Dicionário de configuração da app.

        Returns:
            EmailService: Instância configurada.

        Raises:
            ValueError: Se a configuração for inválida ou campos obrigatórios estiverem faltando.
        """
        send_email = app_config.get('SEND_EMAIL', False)

        if not send_email:
            # Modo desenvolvimento/teste
            provider = MockProvider(log_emails=True)
        else:
            # Configuração de produção
            email_provider = app_config.get('EMAIL_PROVIDER', 'postmark').lower()

            if email_provider == 'postmark':
                server_token = app_config.get('POSTMARK_SERVER_TOKEN')
                if not server_token:
                    raise ValueError(
                            "POSTMARK_SERVER_TOKEN é obrigatório quando EMAIL_PROVIDER=postmark")
                provider = PostmarkProvider(server_token)

            elif email_provider == 'smtp':
                smtp_config = {
                    'smtp_server': app_config.get('SMTP_SERVER'),
                    'smtp_port'  : app_config.get('SMTP_PORT', 587),
                    'username'   : app_config.get('SMTP_USERNAME'),
                    'password'   : app_config.get('SMTP_PASSWORD'),
                    'use_tls'    : app_config.get('SMTP_USE_TLS', True)
                }

                required_fields = ['smtp_server', 'username', 'password']
                missing_fields = [field for field in required_fields if not smtp_config.get(field)]

                if missing_fields:
                    raise ValueError(f"Campos obrigatórios para SMTP: {', '.join(missing_fields)}")

                provider = SMTPProvider(**smtp_config)
            else:
                raise ValueError(f"Provedor de email não suportado: {email_provider}")

        default_from_email = app_config.get('EMAIL_SENDER')
        default_from_name = app_config.get('EMAIL_SENDER_NAME', app_config.get('APP_NAME'))

        if not default_from_email:
            raise ValueError("EMAIL_SENDER é obrigatório")

        return cls(provider, default_from_email, default_from_name)

    def send_email(self,
                   to: str,
                   subject: str,
                   text_body: Optional[str] = None,
                   html_body: Optional[str] = None,
                   from_email: Optional[str] = None,
                   from_name: Optional[str] = None,
                   **kwargs) -> EmailResult:
        """Envia um email.

        Args:
            to (str): Email do destinatário.
            subject (str): Assunto do email.
            text_body (typing.Optional[str]): Corpo em texto plano. Se None, apenas html_body é
            usado.
            html_body (typing.Optional[str]): Corpo em HTML. Se None, apenas text_body é usado.
            from_email (typing.Optional[str]): Email do remetente. Se None, usa padrão configurado.
            from_name (typing.Optional[str]): Nome do remetente. Se None, usa padrão configurado.
            **kwargs: Argumentos adicionais para EmailMessage.

        Returns:
            EmailResult: Resultado do envio.

        Raises:
            EmailProviderError: Em caso de erro no envio.
            ValueError: Para dados inválidos.
        """
        try:
            # Usa valores padrão se não fornecidos
            from_email = from_email or self.default_from_email
            from_name = from_name or self.default_from_name

            # Formata o From com nome se fornecido
            if from_name:
                from_email = f"{from_name} <{from_email}>"

            message = EmailMessage(
                    to=to,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                    from_email=from_email,
                    from_name=from_name,
                    **kwargs
            )

            result = self.provider.send(message)

            current_app.logger.debug(
                    "Email enviado via %s: %s - %s (ID: %s)" % (self.provider.get_provider_name(),
                                                                to,
                                                                subject,
                                                                result.message_id if
                                                                result.message_id else 'N/A'))

            return result

        except Exception as e:
            current_app.logger.error("Erro ao enviar email para %s: %s" % (to, str(e)))
            raise

    def get_provider_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o provedor atual.

        Returns:
            typing.Dict[str, typing.Any]: Informações sobre o provedor.
        """
        return {
            'provider_name'    : self.provider.get_provider_name(),
            'default_from'     : self.default_from_email,
            'default_from_name': self.default_from_name
        }

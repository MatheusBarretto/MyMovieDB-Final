from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class EmailMessage:
    """Representa uma mensagem de email a ser enviada."""
    to: str  # Endereço de email do destinatário
    subject: str  # Assunto do email
    text_body: Optional[str] = None  # Corpo do email em texto plano
    html_body: Optional[str] = None  # Corpo do email em HTML
    from_email: Optional[str] = None  # Endereço de email do remetente (padrão: EMAIL_SENDER)
    from_name: Optional[str] = None  # Nome do remetente (padrão: EMAIL_SENDER_NAME)
    reply_to: Optional[str] = None  # Endereço para respostas (Reply-To header)
    cc: Optional[list[str]] = None  # Lista de endereços em cópia (CC)
    bcc: Optional[list[str]] = None  # Lista de endereços em cópia oculta (BCC)

    def __post_init__(self):
        if not self.text_body and not self.html_body:
            raise ValueError("Email tem que ter text_body ou html_body.")


@dataclass
class EmailResult:
    """Resultado do envio de um email."""
    success: bool  # Indica se o email foi enviado com sucesso
    provider: str = ""  # Nome do provedor utilizado (postmark, smtp, mock)
    message_id: Optional[str] = None  # ID único da mensagem retornado pelo provedor
    to: Optional[str] = None  # Endereço do destinatário (confirmação)
    sent_at: Optional[str] = None  # Data/hora do envio em formato ISO
    error_code: Optional[int] = None  # Código de erro retornado pelo provedor (se houver)
    raw_response: Optional[Any] = None  # Resposta completa do provedor (para debug)

"""Serviço de geração e validação de tokens JWT.

Este módulo fornece funcionalidades para criação e verificação de tokens JWT
usados para validação de email, reset de senha e autenticação temporária.

Classes principais:
    - JWTService: Serviço para criação e validação de tokens JWT
    - JWT_action: Enum com tipos de ações de tokens
    - TokenVerificationResult: Dataclass com resultado de verificação de token
"""
from dataclasses import dataclass
from enum import Enum
from time import time
from typing import Any, Dict, Optional

import jwt
from flask import current_app


class JWT_action(Enum):
    """Enumeração que define as ações possíveis para tokens JWT.
    """
    NO_ACTION = 0
    VALIDAR_EMAIL = 1
    RESET_PASSWORD = 2
    PENDING_2FA = 3
    ACTIVATING_2FA = 4


@dataclass
class TokenVerificationResult:
    """Resultado da verificação de um token JWT."""
    valid: bool  # Indica se o token é válido
    sub: Optional[str] = None  # Subject do token (geralmente email do usuário)
    action: Optional[JWT_action] = None  # Ação para a qual o token foi criado
    age: Optional[int] = None  # Idade do token em segundos (tempo desde criação)
    extra_data: Optional[Dict[Any, Any]] = None  # Dados extras incluídos no payload do token
    reason: Optional[str] = None  # Motivo da falha se inválido ('expired', 'invalid', 'bad_signature', etc.)


class JWTService:
    """Serviço para criação e validação de tokens JWT.
    """

    @staticmethod
    def create(action: JWT_action = JWT_action.NO_ACTION,
               sub: Any = None,
               expires_in: int = 600,
               extra_data: Optional[Dict[Any, Any]] = None) -> str:
        """Cria um token JWT com os parâmetros fornecidos.

        Args:
            action (JWT_action): A ação para a qual o token está sendo usado. Se None,
                usa NO_ACTION.
            sub (Any): O assunto do token (por exemplo, email do usuário). Se None,
                será validado antes do uso.
            expires_in (int): O tempo de expiração do token em segundos. Se for negativo,
                o token não expira. Default de 10 minutos.
            extra_data (Optional[Dict[Any, Any]]): Dicionário com dados adicionais para
                incluir no payload. Se None, nenhum dado extra é incluído.

        Returns:
            str: O token JWT codificado com as reivindicações sub, iat, nbf, action e,
            opcionalmente, exp e extra_data.

        Raises:
            ValueError: Se o objeto 'sub' não puder ser convertido em string.
        """
        if not hasattr(type(sub), '__str__'):  # isinstance(sub, (str, int, float, uuid.UUID)):
            raise ValueError(f"Tipo de objeto 'sub' inválido: {type(sub)}")

        agora = int(time())
        payload: Dict[str, Any] = {
            'sub'   : str(sub),
            'iat'   : agora,
            'nbf'   : agora,
            'action': action.name
        }
        if expires_in > 0:
            payload['exp'] = agora + expires_in
        if extra_data is not None and isinstance(extra_data, dict):
            payload['extra_data'] = extra_data
        return jwt.encode(payload=payload,
                          key=current_app.config.get('SECRET_KEY'),
                          algorithm='HS256')

    @staticmethod
    def verify(token: str) -> TokenVerificationResult:
        """Verifica um token JWT e retorna suas reivindicações.

        Args:
            token (str): O token JWT a ser verificado.

        Returns:
            TokenVerificationResult: Objeto contendo o resultado da verificação.
            Se válido, contém 'sub', 'action', 'age' e 'extra_data' (se presentes).
            Se inválido, contém 'reason' com o motivo da falha.
        """
        try:
            payload = jwt.decode(token,
                                 key=current_app.config.get('SECRET_KEY'),
                                 algorithms=['HS256'])

            if 'sub' not in payload:
                return TokenVerificationResult(valid=False, reason="missing_sub")

            acao = JWT_action[payload.get('action', 'NO_ACTION')]
            age = int(time()) - int(payload['iat']) if 'iat' in payload else None
            extra_data = payload.get('extra_data')

            return TokenVerificationResult(
                valid=True,
                sub=payload.get('sub'),
                action=acao,
                age=age,
                extra_data=extra_data
            )

        except jwt.ExpiredSignatureError as e:
            current_app.logger.error("JWT expirado: %s" % (e,))
            return TokenVerificationResult(valid=False, reason="expired")
        except jwt.InvalidTokenError as e:
            current_app.logger.error("JWT invalido: %s" % (e,))
            return TokenVerificationResult(valid=False, reason="invalid")
        except jwt.InvalidSignatureError as e:
            current_app.logger.error("Assinatura invalida no JWT: %s" % (e,))
            return TokenVerificationResult(valid=False, reason="bad_signature")
        except ValueError as e:
            current_app.logger.error("ValueError: %s" % (e,))
            return TokenVerificationResult(valid=False, reason="valueerror")

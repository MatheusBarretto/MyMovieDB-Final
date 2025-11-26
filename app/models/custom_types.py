import base64
import logging
from typing import Any, Optional

from flask import current_app
from sqlalchemy.types import TypeDecorator, String as SQLString

class EncryptedString(TypeDecorator):
    """
    Tipo de dados do SQLAlchemy para criptografia transparente de colunas.

    Este tipo gerencia automaticamente a criptografia de valores ao serem enviados
    para o banco de dados (bind) e a descriptografia ao serem lidos (result),
    garantindo que os dados sensíveis fiquem sempre em repouso (at-rest) de
    forma segura.

    Atributos:
        impl (TypeEngine): O tipo subjacente do SQLAlchemy a ser usado no banco de dados.
        cache_ok (bool): Permite que o SQLAlchemy armazene em cache instâncias deste tipo.

    Requisitos de Configuração:
        - A extensão 'secrets_manager' deve ser inicializada na instância da
          aplicação Flask e acessível via `current_app.extensions`.
        - O SecretsManager deve possuir os métodos `encrypt(data)` e `decrypt(data, hint)`.

    Formato do Dado Criptografado:
        O dado é armazenado no banco no formato "versao:ciphertext_base64".
        Exemplo: "v1:AbCdEfGhIjKlMnOp..."
    """

    impl = SQLString
    cache_ok = True

    # Constantes para clareza e facilidade de manutenção
    VERSION_SEPARATOR = ':'
    VERSION_PREFIX = 'v'
    


    def __init__(self, length: int = 255, **kwargs):
        """
        Inicializa o tipo criptografado.

        Args:
            length (int): O comprimento máximo da string criptografada no banco de
                          dados. O valor deve ser suficiente para acomodar a versão,
                          o separador e o ciphertext em Base64.
            **kwargs: Argumentos adicionais para o tipo `String` do SQLAlchemy.
        """
        super().__init__(length=length)
        self._sm_cache = None  # Cache para o SecretsManager

    @property
    def sm(self) -> 'SecretsManager':
        """
        Propriedade para obter o SecretsManager de forma "lazy" e com cache.

        Busca o SecretsManager do contexto da aplicação Flask na primeira vez que é
        acessado e o armazena em cache na instância para usos subsequentes dentro
        da mesma transação.

        Returns:
            SecretsManager: A instância do gerenciador de segredos.

        Raises:
            RuntimeError: Se o contexto da aplicação Flask não estiver disponível
                          ou se o SecretsManager não estiver inicializado.
        """
        if self._sm_cache:
            return self._sm_cache

        if not current_app:
            raise RuntimeError("Contexto da aplicação Flask não está disponível.")

        sm_instance = current_app.extensions.get('secrets_manager')
        if not sm_instance:
            raise RuntimeError("SecretsManager não foi inicializado na aplicação Flask.")

        self._sm_cache = sm_instance
        return self._sm_cache

    def _is_encrypted(self, value: str) -> bool:
        """Verifica se uma string parece já estar no formato criptografado."""
        if not isinstance(value, str):
            return False
        parts = value.split(self.VERSION_SEPARATOR, 1)
        return len(parts) == 2 and parts[0].startswith(self.VERSION_PREFIX)
    
    @classmethod
    def check_needs_reencryption(cls, session, model_class, obj, column_name: str, target_version: str) -> bool:
        """
        Verifica se um campo criptografado precisa ser re-criptografado.
        
        Usa uma query raw para obter o valor criptografado do banco,
        depois usa SecretsManager.decrypt() para ver qual versão foi usada.
        
        Args:
            session: Sessão do SQLAlchemy
            model_class: Classe do modelo
            obj: O objeto SQLAlchemy
            column_name: Nome da coluna a verificar
            target_version: Versão alvo desejada
            
        Returns:
            bool: True se precisa re-criptografar, False caso contrário
        """
        try:
            from flask import current_app
            from sqlalchemy import text
            import base64
            
            # Obter o valor criptografado raw do banco usando SQL direto
            pk_name = 'id'  # Assumindo que a PK é sempre 'id'
            pk_val = getattr(obj, pk_name)
            
            # Query SQL simples que funciona com qualquer banco
            raw_query = text(f"SELECT {column_name} FROM {model_class.__tablename__} WHERE {pk_name} = :pk")
            
            # Tratar UUID corretamente para diferentes bancos de dados
            if hasattr(pk_val, 'hex'):
                # Para SQLite, usar formato sem hífens
                pk_param = pk_val.hex
            else:
                # Para outros tipos, usar string direta
                pk_param = str(pk_val)
                
            raw_result = session.execute(raw_query, {"pk": pk_param})
            raw_encrypted_val = raw_result.scalar()
            
            if not raw_encrypted_val:
                return False
            
            # Obter o SecretsManager
            sm = current_app.extensions.get('secrets_manager')
            if not sm:
                return True  # Se não tem SM, assumir que precisa re-criptografar
            
            # Verificar o formato do valor
            if cls.VERSION_SEPARATOR in raw_encrypted_val:
                # Formato com versão: "vX:base64data"
                version_hint, b64_ct = raw_encrypted_val.split(cls.VERSION_SEPARATOR, 1)
                ciphertext = base64.urlsafe_b64decode(b64_ct.encode('ascii'))
            else:
                # Formato legado sem versão
                version_hint = None
                ciphertext = base64.urlsafe_b64decode(raw_encrypted_val.encode('ascii'))
            
            # Usar SecretsManager.decrypt() para ver qual versão foi usada
            version_used, _ = sm.decrypt(ciphertext, version_hint)
            
            # Se a versão usada não é a target, precisa re-criptografar
            return version_used != target_version
            
        except Exception:
            # Em caso de erro, assumir que precisa re-criptografar
            return True

    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """
        Processa o valor ao ser enviado para o banco de dados (criptografa).
        """
        if value is None:
            return None

        # Evita dupla criptografia se o valor já estiver no formato esperado
        if isinstance(value, str) and self._is_encrypted(value):

            return value

        try:
            value_str = str(value)
            version, ciphertext = self.sm.encrypt(value_str.encode('utf-8'))
            b64_ciphertext = base64.urlsafe_b64encode(ciphertext).decode('ascii')
            encrypted_value = f"{version}{self.VERSION_SEPARATOR}{b64_ciphertext}"
            return encrypted_value
            
        except Exception:
            current_app.logger.error("Falha crítica ao criptografar o valor.", exc_info=True)
            raise TypeError("Não foi possível criptografar o valor para armazenamento.")

    def process_result_value(self, value: Any, dialect) -> Optional[str]:
        """
        Processa o valor ao ser lido do banco de dados (descriptografa).
        """
        if value is None:
            return None

        try:
            # Formato novo com versão (ex: "v1:AbCdEf...")
            if self.VERSION_SEPARATOR in value:
                version_hint, b64_ct = value.split(self.VERSION_SEPARATOR, 1)
                ciphertext = base64.urlsafe_b64decode(b64_ct.encode('ascii'))
            # Formato legado sem versão (fallback)
            else:
                version_hint = None
                ciphertext = base64.urlsafe_b64decode(value.encode('ascii'))

            version_used, plaintext = self.sm.decrypt(ciphertext, version_hint)
            return plaintext.decode('utf-8')

        except (TypeError, base64.binascii.Error) as e:
            raise ValueError("O valor do banco não é um Base64 válido ou está corrompido.")
        except Exception:
            raise ValueError("Não foi possível descriptografar o valor do banco de dados.")

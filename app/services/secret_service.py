import base64
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import Flask


@dataclass(frozen=True)
class KeyConfiguration:
    """Configuração imutável e validada de uma versão de chave."""
    version: str
    key: str
    salt: bytes
    salt_hash: Optional[str] = None

    def __post_init__(self):
        """Valida integridade após inicialização."""
        if self.salt_hash:
            computed = hashlib.sha256(self.salt).hexdigest()
            if computed != self.salt_hash:
                raise ValueError(
                        f"Integridade do salt comprometida para versão {self.version}. "
                        f"Hash esperado: {self.salt_hash}, calculado: {computed}"
                )


class SecretsManagerError(Exception):
    """Erro específico do gerenciador de segredos."""
    pass


class SecretsManager:
    def __init__(self,
                 app: Optional[Flask] = None,
                 keys_config_name: str = "ENCRYPTION_KEYS",
                 active_version_name: str = "ACTIVE_ENCRYPTION_VERSION",
                 kdf_iterations: int = 100000,
                 verify_salt_integrity: bool = True,
                 audit_callback: Optional[Callable] = None):
        self.keys_config_name = keys_config_name
        self.active_version_name = active_version_name
        self.kdf_iterations = kdf_iterations
        self.verify_salt_integrity = verify_salt_integrity
        self.audit_callback = audit_callback

        self._config_cache: Dict[str, KeyConfiguration] = {}
        self._fernet_cache: Dict[str, Fernet] = {}
        self._lock = RLock()
        self._app = None
        self._validated = False

        self._stats = {
            'encryptions'     : 0,
            'decryptions'     : 0,
            'cache_hits'      : 0,
            'cache_misses'    : 0,
            'integrity_checks': 0
        }

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """
        Registra o manager na aplicação Flask.

        Este metodo inicializa o SecretsManager com a aplicação Flask fornecida,
        registrando-o nas extensões da aplicação. Em seguida, tenta validar a
        configuração de criptografia. Se a validação falhar, verifica se o comando
        atual é um comando CLI que não requer validação (como 'secrets generate' ou
        'secrets list'). Nesse caso, emite um aviso no log. Caso contrário, lança
        uma exceção SecretsManagerError.

        Args:
            app (Flask): A instância da aplicação Flask a ser registrada.

        Raises:
            SecretsManagerError: Se a validação da configuração falhar e não for
                um comando CLI que permite pular a validação.
        """
        self._app = app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['secrets_manager'] = self

        # Opcional: tentar validar, mas não falhar se for comando CLI
        try:
            self._validate_configuration()
        except SecretsManagerError as e:
            # Detectar se é comando CLI que não precisa de validação
            import sys
            is_cli_generate = (len(sys.argv) > 2 and
                               sys.argv[1] == 'secrets' and
                               sys.argv[2] in ['generate', 'list'])

            if is_cli_generate:
                comandos = f"{' '.join(sys.argv[1:3])}"
                app.logger.warning("Configuração de criptografia não validada "
                                   "(comando CLI: %s)" % (comandos,))
            else:
                # Para comandos que precisam de validação ou app normal
                app.logger.error("Falha na validação de configuração: %s" % (e,))
                raise

    def _validate_configuration(self):
        """Valida que a configuração mínima está presente."""
        if not self._app:
            return

        if self._validated:
            return

        # Tentar carregar configurações
        configs = self._load_all_key_configs()
        if not configs:
            raise SecretsManagerError("Nenhuma chave de criptografia configurada")

        active = self.get_active_version()
        if active not in configs:
            raise SecretsManagerError(
                    f"Versão ativa '{active}' não existe nas chaves configuradas"
            )

        self._validated = True
        self._app.logger.info("Configuração de criptografia validada com sucesso")

    def _ensure_validated(self):
        """Garante que configuração foi validada antes de operações críticas."""
        if not self._validated:
            self._validate_configuration()

    @staticmethod
    def _normalize_salt(salt: Any) -> bytes:
        """Converte salt de diversos formatos para bytes."""
        if isinstance(salt, bytes):
            return salt

        if not isinstance(salt, str):
            raise TypeError(f"Salt deve ser str ou bytes, recebido: {type(salt)}")

        # Tenta hex
        if len(salt) % 2 == 0:
            try:
                return bytes.fromhex(salt)
            except ValueError:
                pass

        # Tenta base64
        try:
            return base64.urlsafe_b64decode(salt.encode('ascii'))
        except Exception:
            pass

        # Fallback: UTF-8 direto
        return salt.encode('utf-8')

    def _load_key_config(self, version: str) -> KeyConfiguration:
        """Carrega e valida configuração de uma versão específica."""
        # Normalizar versão
        version = self._normalize_version(version)

        with self._lock:
            if version in self._config_cache:
                self._stats['cache_hits'] += 1
                return self._config_cache[version]

        self._stats['cache_misses'] += 1

        if not self._app:
            raise SecretsManagerError("Aplicação Flask não inicializada")

        keys_dict = self._app.config.get(self.keys_config_name, {})

        # Normalizar chaves do dicionário
        normalized_keys = {
            self._normalize_version(k): v for k, v in keys_dict.items()
        }

        # Suporte a variáveis de ambiente como fallback
        if version not in normalized_keys:
            # Tentar encontrar com case-insensitive
            for env_key in os.environ:
                if env_key.upper().startswith(f"{self.keys_config_name}__"):
                    env_version = env_key.split("__", 1)[1]
                    normalized_env_version = self._normalize_version(env_version)

                    if normalized_env_version == version:
                        # Encontrou! Buscar salt correspondente
                        salt_key_candidates = [
                            f"ENCRYPTION_SALT__{env_version}",
                            f"ENCRYPTION_SALT__{env_version.upper()}",
                            f"ENCRYPTION_SALT__{env_version.lower()}"
                        ]

                        salt_value = None
                        for salt_key in salt_key_candidates:
                            if salt_key in os.environ:
                                salt_value = os.environ[salt_key]
                                break

                        if salt_value:
                            hash_key_candidates = [
                                f"ENCRYPTION_SALT_HASH__{env_version}",
                                f"ENCRYPTION_SALT_HASH__{env_version.upper()}",
                                f"ENCRYPTION_SALT_HASH__{env_version.lower()}"
                            ]

                            hash_value = None
                            for hash_key in hash_key_candidates:
                                if hash_key in os.environ:
                                    hash_value = os.environ[hash_key]
                                    break

                            normalized_keys[version] = {
                                'key'      : os.environ[env_key],
                                'salt'     : salt_value,
                                'salt_hash': hash_value
                            }
                            break

        if version not in normalized_keys:
            raise SecretsManagerError(
                    f"Versão '{version}' não encontrada. "
                    f"Versões disponíveis: {list(normalized_keys.keys())}"
            )

        config_dict = normalized_keys[version]
        if not isinstance(config_dict, dict) or \
                'key' not in config_dict or \
                'salt' not in config_dict:
            raise SecretsManagerError(
                    f"Configuração inválida para versão '{version}'. "
                    f"Esperado: {{'key': '...', 'salt': '...'}}"
            )

        salt_bytes = self._normalize_salt(config_dict['salt'])
        salt_hash = config_dict.get('salt_hash') if self.verify_salt_integrity else None

        if salt_hash:
            self._stats['integrity_checks'] += 1

        key_config = KeyConfiguration(version=version,
                                      key=config_dict['key'],
                                      salt=salt_bytes,
                                      salt_hash=salt_hash)

        with self._lock:
            self._config_cache[version] = key_config

        return key_config

    def _load_all_key_configs(self) -> Dict[str, KeyConfiguration]:
        """Carrega todas as configurações de chaves disponíveis."""
        if not self._app:
            raise SecretsManagerError("Aplicação Flask não inicializada")

        keys_dict = self._app.config.get(self.keys_config_name, {})

        # Normalizar chaves do dicionário para lowercase
        normalized_keys = {}
        for version, config in keys_dict.items():
            normalized_version = self._normalize_version(version)
            normalized_keys[normalized_version] = config

        # Adicionar chaves de variáveis de ambiente
        for key in os.environ:
            if key.startswith(f"{self.keys_config_name}__"):
                version = key.split("__", 1)[1]
                normalized_version = self._normalize_version(version)

                if normalized_version not in normalized_keys:
                    salt_key = f"ENCRYPTION_SALT__{version}"
                    if salt_key in os.environ:
                        normalized_keys[normalized_version] = {
                            'key'      : os.environ[key],
                            'salt'     : os.environ[salt_key],
                            'salt_hash': os.environ.get(f"ENCRYPTION_SALT_HASH__{version}")
                        }

        # Carregar configs
        result = {}
        for version in normalized_keys.keys():
            result[version] = self._load_key_config(version)

        return result

    @staticmethod
    def _normalize_version(version: str) -> str:
        """Normaliza versão para lowercase para compatibilidade Windows."""
        return version.lower() if version else version

    def _derive_fernet(self, key_config: KeyConfiguration) -> Fernet:
        """Deriva chave Fernet usando PBKDF2."""
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),
                         length=32,
                         salt=key_config.salt,
                         iterations=self.kdf_iterations)
        derived = kdf.derive(key_config.key.encode('utf-8'))
        fernet_key = base64.urlsafe_b64encode(derived)
        return Fernet(fernet_key)

    def get_active_version(self) -> str:
        """
        Retorna a versão de chave ativa (normalizada).

        A versão ativa é determinada pela seguinte prioridade:
        1. Configuração da aplicação Flask (self._app.config).
        2. Variável de ambiente.
        3. Se houver apenas uma versão configurada, usa-a como fallback.

        Returns:
            str: A versão ativa normalizada (em lowercase).

        Raises:
            SecretsManagerError: Se nenhuma versão ativa for encontrada ou configurada.
        """
        if self._app:
            version = self._app.config.get(self.active_version_name)
            if version:
                # Remover aspas se existirem (problema do dotenv)
                version = version.strip('"').strip("'")
                return self._normalize_version(version)

        # Fallback para environment
        version = os.environ.get(self.active_version_name)
        if version:
            version = version.strip('"').strip("'")
            return self._normalize_version(version)

        # Se há apenas uma versão, usa-a
        try:
            configs = self._load_all_key_configs()
            if len(configs) == 1:
                return next(iter(configs.keys()))
        except:
            pass

        raise SecretsManagerError(
                f"Versão ativa não configurada ({self.active_version_name})"
        )

    def get_fernet(self, version: str) -> Fernet:
        """
        Obtém uma instância Fernet para a versão especificada, utilizando cache para otimização.

        Args:
            version (str): A versão da chave de criptografia a ser usada.

        Returns:
            Fernet: Instância Fernet derivada para a versão especificada.

        Raises:
            SecretsManagerError: Se a versão não for encontrada ou se houver erro na configuração.
        """
        self._ensure_validated()

        # Normalizar versão
        version = self._normalize_version(version)

        cache_key = f"{version}:{self.kdf_iterations}"

        with self._lock:
            if cache_key in self._fernet_cache:
                return self._fernet_cache[cache_key]

        key_config = self._load_key_config(version)
        fernet = self._derive_fernet(key_config)

        with self._lock:
            self._fernet_cache[cache_key] = fernet

        return fernet

    def get_all_versions(self) -> List[str]:
        """
        Retorna uma lista de todas as versões de chaves de criptografia disponíveis.

        Esta função carrega todas as configurações de chaves e retorna os nomes
        das versões normalizadas em uma lista.

        Returns:
            List[str]: Lista contendo os nomes das versões disponíveis.
        """
        return list(self._load_all_key_configs().keys())

    def encrypt(self, plaintext: bytes) -> Tuple[str, bytes]:
        """
        Criptografa os dados fornecidos usando a versão ativa de chave de criptografia.

        Esta função utiliza a versão ativa de chave para derivar uma instância Fernet
        e criptografar os dados em texto plano. Retorna a versão usada e os dados
        criptografados.

        Args:
            plaintext (bytes): Os dados em texto plano a serem criptografados.

        Returns:
            Tuple[str, bytes]: Uma tupla contendo a versão da chave usada para
            criptografia e os dados criptografados em bytes.

        Raises:
            SecretsManagerError: Se a configuração não estiver validada ou se houver
            erro na obtenção da versão ativa ou na derivação da chave Fernet.
        """
        self._ensure_validated()

        version = self.get_active_version()
        fernet = self.get_fernet(version)
        ciphertext = fernet.encrypt(plaintext)

        self._stats['encryptions'] += 1
        self._audit('encryption', {'version': version, 'size': len(plaintext)})

        return version, ciphertext

    def decrypt(self,
                ciphertext: bytes,
                version_hint: Optional[str] = None) -> Tuple[str, bytes]:
        """
        Descriptografa os dados criptografados, tentando a versão indicada primeiro, depois a
        versão ativa, e por fim todas as outras versões disponíveis.

        Args:
            ciphertext (bytes): Os dados criptografados a serem descriptografados.
            version_hint (Optional[str]): Versão da chave a tentar primeiro. Se None, começa com
            a versão ativa.

        Returns:
            Tuple[str, bytes]: Uma tupla contendo a versão da chave usada para descriptografia e
            os dados descriptografados em bytes.

        Raises:
            SecretsManagerError: Se falhar ao descriptografar com todas as versões tentadas.
        """
        self._ensure_validated()
        versions_to_try = []

        # Ordem de tentativa: hint, ativa, todas as outras
        if version_hint:
            versions_to_try.append(version_hint)

        active = self.get_active_version()
        if active not in versions_to_try:
            versions_to_try.append(active)

        for v in self.get_all_versions():
            if v not in versions_to_try:
                versions_to_try.append(v)

        last_error = None
        for version in versions_to_try:
            try:
                fernet = self.get_fernet(version)
                plaintext = fernet.decrypt(ciphertext)

                self._stats['decryptions'] += 1
                self._audit('decryption', {
                    'version' : version,
                    'was_hint': version == version_hint
                })

                return version, plaintext
            except InvalidToken as e:
                last_error = e
                continue

        raise SecretsManagerError(
                f"Falha ao descriptografar com todas as versões tentadas. "
                f"Último erro: {last_error}"
        )

    def rotate_to_new_version(self,
                              new_version: str,
                              new_key: str,
                              new_salt: Optional[bytes] = None,
                              persist_to_file: Optional[str] = None):
        """
        Adiciona nova versão e a marca como ativa.

        Args:
            new_version: Nome da nova versão (ex: "v3")
            new_key: Chave de criptografia
            new_salt: Salt (se None, reutiliza o salt existente)
            persist_to_file: Arquivo .env para persistir
        """
        if not self._app:
            raise SecretsManagerError("Aplicação não inicializada")

        # Reutilizar salt se não fornecido
        if new_salt is None:
            existing_configs = self._load_all_key_configs()
            if existing_configs:
                first_config = next(iter(existing_configs.values()))
                new_salt = first_config.salt
            else:
                raise SecretsManagerError(
                        "Nenhuma configuração existente para reutilizar salt. "
                        "Forneça new_salt explicitamente."
                )

        # Atualizar configuração em memória
        keys_dict = self._app.config.get(self.keys_config_name, {})
        keys_dict[new_version] = {
            'key' : new_key,
            'salt': base64.urlsafe_b64encode(new_salt).decode('ascii')
        }
        self._app.config[self.keys_config_name] = keys_dict
        self._app.config[self.active_version_name] = new_version

        # Limpar caches
        with self._lock:
            self._config_cache.clear()
            self._fernet_cache.clear()

        # Persistir se solicitado
        if persist_to_file:
            self._persist_to_env_file(persist_to_file, new_version, new_key, new_salt)

        self._audit('rotation', {'new_version': new_version})

    def _persist_to_env_file(self,
                             filename: str,
                             version: str,
                             key: str,
                             salt: bytes):
        """Atualiza arquivo .env mantendo outras variáveis."""
        data = {}
        env_path = Path(filename)

        # Ler arquivo existente
        if env_path.exists():
            with env_path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        data[k.strip()] = v.strip().strip('"').strip("'")

        # Adicionar/atualizar nova versão
        data[f"{self.keys_config_name}__{version}"] = key
        data[f"ENCRYPTION_SALT__{version}"] = base64.urlsafe_b64encode(salt).decode('ascii')
        data[self.active_version_name] = version

        # Calcular hash do salt para integridade
        salt_hash = hashlib.sha256(salt).hexdigest()
        data[f"ENCRYPTION_SALT_HASH__{version}"] = salt_hash

        # Escrever de volta
        with env_path.open('w', encoding='utf-8') as f:
            f.write(f"# Atualizado em {datetime.now(timezone.utc).isoformat()}Z\n")
            for k, v in sorted(data.items()):
                f.write(f'{k}="{v}"\n')

    def _audit(self, event: str, metadata: Dict[str, Any]):
        """Registra evento de auditoria se callback configurado."""
        if self.audit_callback:
            try:
                self.audit_callback(event, metadata)
            except Exception:
                pass

    def get_statistics(self) -> Dict[str, int]:
        """Retorna estatísticas de uso."""
        return self._stats.copy()

    def clear_cache(self):
        """Limpa todos os caches (útil em testes)."""
        with self._lock:
            self._config_cache.clear()
            self._fernet_cache.clear()


def consolidate_and_remove_keys(app: Flask) -> dict:
    """
    Consolida chaves de criptografia, salts e hashes de salt da configuração do Flask
    e variáveis de ambiente, removendo as chaves originais para aumentar a segurança.

    Esta função itera pela configuração da aplicação Flask e variáveis de ambiente
    para coletar chaves de criptografia, salts e seus hashes baseados em prefixos
    específicos. Também normaliza a versão ativa de criptografia para lowercase e
    remove aspas.

    As chaves individuais (ENCRYPTION_KEYS__vX, ENCRYPTION_SALT__vX, etc.) são removidas
    após consolidação no dicionário ENCRYPTION_KEYS, garantindo uma única fonte de verdade
    e reduzindo a superfície de exposição de dados sensíveis.

    Args:
        app (Flask): A instância da aplicação Flask.

    Returns:
        dict: Um dicionário com versões como chaves e seus respectivos valores
              'key', 'salt' e 'salt_hash'.
              Formato: {'v1': {'key': '...', 'salt': '...', 'salt_hash': '...'}, ...}

    Raises:
        ValueError: Se alguma versão estiver faltando os campos obrigatórios 'key' ou 'salt'.
    """
    encryption_keys: Dict[str, Dict[str, str]] = {}
    keys_to_remove: List[str] = []
    env_keys_to_remove: List[str] = []

    # 1. Processar chaves do app.config primeiro
    for key, value in list(app.config.items()):
        key_upper = key.upper()

        # Verificar o prefixo mais específico primeiro para evitar correspondências parciais
        # ENCRYPTION_SALT_HASH__ deve ser verificado antes de ENCRYPTION_SALT__
        if key_upper.startswith('ENCRYPTION_SALT_HASH__'):
            version = key.split('__', 1)[1].lower()
            encryption_keys.setdefault(version, {})['salt_hash'] = value
            keys_to_remove.append(key)
            app.logger.debug("Hash de salt consolidado para versão '%s' (app.config)" % (version,))

        elif key_upper.startswith('ENCRYPTION_SALT__'):
            version = key.split('__', 1)[1].lower()
            encryption_keys.setdefault(version, {})['salt'] = value
            keys_to_remove.append(key)
            app.logger.debug("Salt consolidado para versão '%s' (app.config)" % (version,))

        elif key_upper.startswith('ENCRYPTION_KEYS__'):
            version = key.split('__', 1)[1].lower()
            encryption_keys.setdefault(version, {})['key'] = value
            keys_to_remove.append(key)
            app.logger.debug("Chave consolidada para versão '%s' (app.config)" % (version,))

    # 2. Processar variáveis de ambiente (fallback e fonte principal)
    for env_key, env_value in list(os.environ.items()):
        env_key_upper = env_key.upper()

        # Verificar o prefixo mais específico primeiro
        if env_key_upper.startswith('ENCRYPTION_SALT_HASH__'):
            version = env_key.split('__', 1)[1].lower()
            # Só adicionar se não foi encontrado no app.config
            if version not in encryption_keys or 'salt_hash' not in encryption_keys[version]:
                encryption_keys.setdefault(version, {})['salt_hash'] = env_value
                env_keys_to_remove.append(env_key)
                app.logger.debug("Hash de salt consolidado para versão '%s' (environ)" % (version,))

        elif env_key_upper.startswith('ENCRYPTION_SALT__'):
            version = env_key.split('__', 1)[1].lower()
            # Só adicionar se não foi encontrado no app.config
            if version not in encryption_keys or 'salt' not in encryption_keys[version]:
                encryption_keys.setdefault(version, {})['salt'] = env_value
                env_keys_to_remove.append(env_key)
                app.logger.debug("Salt consolidado para versão '%s' (environ)" % (version,))

        elif env_key_upper.startswith('ENCRYPTION_KEYS__'):
            version = env_key.split('__', 1)[1].lower()
            # Só adicionar se não foi encontrado no app.config
            if version not in encryption_keys or 'key' not in encryption_keys[version]:
                encryption_keys.setdefault(version, {})['key'] = env_value
                env_keys_to_remove.append(env_key)
                app.logger.debug("Chave consolidada para versão '%s' (environ)" % (version,))

    # 3. Normalizar ACTIVE_ENCRYPTION_VERSION (verificar app.config primeiro, depois environ)
    active_version = app.config.get('ACTIVE_ENCRYPTION_VERSION')
    if not active_version:
        active_version = os.environ.get('ACTIVE_ENCRYPTION_VERSION')
        if active_version:
            # Copiar para app.config para centralizar
            app.config['ACTIVE_ENCRYPTION_VERSION'] = active_version
            env_keys_to_remove.append('ACTIVE_ENCRYPTION_VERSION')
            app.logger.debug("ACTIVE_ENCRYPTION_VERSION copiado do environ para app.config")

    if active_version:
        if not isinstance(active_version, str):
            app.logger.warning("ACTIVE_ENCRYPTION_VERSION tem tipo inesperado: %s. "
                               "Convertendo para string." % (type(active_version),))
            active_version = str(active_version)

        # Remover aspas (simples e duplas) e normalizar para lowercase
        normalized_version = active_version.strip('"\'').lower()
        app.config['ACTIVE_ENCRYPTION_VERSION'] = normalized_version
        app.logger.debug("Versão ativa normalizada: %s" % (normalized_version,))

    # 4. Validar integridade: todas as versões devem ter 'key' e 'salt'
    incomplete_versions = []
    for version, config in encryption_keys.items():
        if 'key' not in config or 'salt' not in config:
            incomplete_versions.append(version)
            app.logger.error("Versão '%s' incompleta. "
                             "Campos presentes: %s. "
                             "Necessário: ['key', 'salt']" %
                             (version, list(config.keys()), ))

    if incomplete_versions:
        raise ValueError("Versões incompletas detectadas: %s."
                         " Cada versão deve ter 'key' e 'salt'." %
                         (incomplete_versions,))

    # 5. Remover com segurança as chaves consolidadas da configuração original
    for key in keys_to_remove:
        del app.config[key]
        app.logger.debug("Chave individual removida do app.config: %s" % (key,))

    # 6. Remover variáveis de ambiente consolidadas (para segurança)
    for env_key in env_keys_to_remove:
        if env_key in os.environ:
            del os.environ[env_key]
            app.logger.debug("Chave individual removida do environ: %s" % (env_key,))

    # Log resumido da operação
    total_removed = len(keys_to_remove) + len(env_keys_to_remove)
    app.logger.info("[OK] Consolidação concluída: %d versões encontradas, "
                    "%d chaves individuais removidas (%d do app.config, %d do environ)" %
                    (len(encryption_keys), total_removed, len(keys_to_remove), len(env_keys_to_remove))
    )

    return encryption_keys

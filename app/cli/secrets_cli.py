import base64
import hashlib
import importlib
import logging
import os
import secrets
import shutil
import sys
import traceback
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set, Optional, TextIO

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import asc, inspect, select, text
from sqlalchemy.orm.attributes import flag_modified

from app.models.servicemodels import ReencryptJob
from app.services.secret_service import SecretsManager


class LogFileManager:
    """Gerenciador de redirecionamento de logs e output para arquivo."""
    
    def __init__(self, logfile: Optional[str] = None):
        self.logfile = logfile
        self.log_handler = None
        self.original_stdout = None
        self.original_stderr = None
        self.file_handle = None
        
    def generate_default_filename(self) -> str:
        """Gera nome de arquivo padrão baseado no timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f'secrets_{timestamp}.log'
    
    def setup_logging(self):
        """Configura redirecionamento de logs e output."""
        if not self.logfile:
            return
        
        try:
            # Abrir arquivo para escrita
            self.file_handle = open(self.logfile, 'w', encoding='utf-8')
            
            # Configurar handler de log para o arquivo
            self.log_handler = logging.FileHandler(self.logfile, mode='a', encoding='utf-8')
            self.log_handler.setLevel(logging.DEBUG)
            
            # Formato detalhado para logs em arquivo
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self.log_handler.setFormatter(formatter)
            
            # Adicionar handler ao logger da aplicação
            if current_app:
                current_app.logger.addHandler(self.log_handler)
            
            # Redirecionar stdout e stderr para o arquivo também
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            
            # Criar um wrapper que escreve tanto no arquivo quanto no terminal
            sys.stdout = TeeOutput(self.original_stdout, self.file_handle)
            sys.stderr = TeeOutput(self.original_stderr, self.file_handle)
            
            # Log inicial
            click.echo(f"[INFO] Logs sendo salvos em: {self.logfile}")
            if current_app:
                current_app.logger.info(f"Sessão de logs iniciada - arquivo: {self.logfile}")
            
        except Exception as e:
            click.echo(f"[ERRO] Não foi possível configurar arquivo de log: {e}")
            self.cleanup()
    
    def cleanup(self):
        """Limpa recursos e restaura configurações originais."""
        try:
            # Restaurar stdout/stderr originais
            if self.original_stdout:
                sys.stdout = self.original_stdout
            if self.original_stderr:
                sys.stderr = self.original_stderr
            
            # Remover handler do logger
            if self.log_handler and current_app:
                current_app.logger.removeHandler(self.log_handler)
                self.log_handler.close()
            
            # Fechar arquivo
            if self.file_handle:
                self.file_handle.close()
                
        except Exception as e:
            # Usar print direto para evitar problemas com redirecionamento
            print(f"[AVISO] Erro ao limpar recursos de log: {e}")


class TeeOutput:
    """Classe que escreve output tanto no terminal quanto em arquivo."""
    
    def __init__(self, terminal: TextIO, file: TextIO):
        self.terminal = terminal
        self.file = file
    
    def write(self, message: str):
        """Escreve mensagem tanto no terminal quanto no arquivo."""
        self.terminal.write(message)
        self.file.write(message)
        self.file.flush()  # Garantir que é escrito imediatamente
    
    def flush(self):
        """Flush tanto terminal quanto arquivo."""
        self.terminal.flush()
        self.file.flush()
    
    def __getattr__(self, name):
        """Delegar outros métodos para o terminal."""
        return getattr(self.terminal, name)


@contextmanager
def log_to_file(logfile: Optional[str] = None):
    """Context manager para redirecionamento de logs."""
    if not logfile:
        yield
        return
    
    manager = LogFileManager(logfile)
    try:
        manager.setup_logging()
        yield manager
    finally:
        manager.cleanup()


def resolve_logfile_path(logfile: Optional[str]) -> Optional[str]:
    """Resolve o caminho do arquivo de log."""
    if logfile is None:
        return None
    
    if logfile == "":
        # Se string vazia, gerar nome padrão
        manager = LogFileManager()
        return manager.generate_default_filename()
    
    return logfile


def with_logfile(func):
    """Decorator para adicionar suporte a logfile em comandos CLI."""
    def wrapper(*args, **kwargs):
        # O último argumento deve ser logfile
        logfile = kwargs.get('logfile') or (args[-1] if args else None)
        logfile_path = resolve_logfile_path(logfile)
        
        with log_to_file(logfile_path):
            return func(*args, **kwargs)
    
    return wrapper


@dataclass
class KeyUsageStats:
    """Estatísticas sobre o uso de versões de chaves em dados criptografados."""
    version: str
    record_count: int
    percentage: float
    is_active: bool
    is_removable: bool


@dataclass
class CleanupOperation:
    """Representa uma operação de limpeza completa com todos os detalhes."""
    operation_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    model_path: str = ""
    column_name: str = ""
    keep_versions: int = 0
    env_file: str = ""
    dry_run: bool = False
    user_confirmed: bool = False
    
    # Análise
    total_records_analyzed: int = 0
    versions_found: List[str] = None
    versions_in_use: List[str] = None
    active_version: str = ""
    
    # Planejamento
    versions_to_keep: List[str] = None
    versions_to_remove: List[str] = None
    
    # Execução
    backup_file: Optional[str] = None
    lines_removed: int = 0
    success: bool = False
    error_message: Optional[str] = None
    rollback_performed: bool = False
    
    def __post_init__(self):
        if self.versions_found is None:
            self.versions_found = []
        if self.versions_in_use is None:
            self.versions_in_use = []
        if self.versions_to_keep is None:
            self.versions_to_keep = []
        if self.versions_to_remove is None:
            self.versions_to_remove = []


class CleanupError(Exception):
    """Exceção específica para erros de limpeza de chaves."""
    
    def __init__(self, message: str, operation: Optional[CleanupOperation] = None, 
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.operation = operation
        self.original_error = original_error


class CleanupAuditLogger:
    """Logger especializado para auditoria de operações de limpeza."""
    
    def __init__(self, operation: CleanupOperation):
        self.operation = operation
        self.logger = current_app.logger
        
    def log_start(self):
        """Registra o início da operação."""
        self.logger.info(
            f"[CLEANUP-AUDIT] Operação iniciada - ID: {self.operation.operation_id}, "
            f"Modelo: {self.operation.model_path}, Coluna: {self.operation.column_name}, "
            f"Manter: {self.operation.keep_versions} versões, Dry-run: {self.operation.dry_run}"
        )
    
    def log_analysis_complete(self):
        """Registra a conclusão da análise."""
        self.logger.info(
            f"[CLEANUP-AUDIT] Análise concluída - ID: {self.operation.operation_id}, "
            f"Registros analisados: {self.operation.total_records_analyzed}, "
            f"Versões encontradas: {len(self.operation.versions_found)}, "
            f"Versões em uso: {len(self.operation.versions_in_use)}"
        )
    
    def log_planning_complete(self):
        """Registra a conclusão do planejamento."""
        self.logger.info(
            f"[CLEANUP-AUDIT] Planejamento concluído - ID: {self.operation.operation_id}, "
            f"Versões a manter: {self.operation.versions_to_keep}, "
            f"Versões a remover: {self.operation.versions_to_remove}"
        )
    
    def log_backup_created(self):
        """Registra a criação do backup."""
        self.logger.info(
            f"[CLEANUP-AUDIT] Backup criado - ID: {self.operation.operation_id}, "
            f"Arquivo: {self.operation.backup_file}"
        )
    
    def log_execution_complete(self):
        """Registra a conclusão da execução."""
        self.logger.info(
            f"[CLEANUP-AUDIT] Execução concluída - ID: {self.operation.operation_id}, "
            f"Linhas removidas: {self.operation.lines_removed}, "
            f"Sucesso: {self.operation.success}"
        )
    
    def log_rollback(self, reason: str):
        """Registra uma operação de rollback."""
        self.logger.warning(
            f"[CLEANUP-AUDIT] Rollback executado - ID: {self.operation.operation_id}, "
            f"Motivo: {reason}, Backup: {self.operation.backup_file}"
        )
    
    def log_error(self, error: Exception):
        """Registra um erro durante a operação."""
        self.logger.error(
            f"[CLEANUP-AUDIT] Erro na operação - ID: {self.operation.operation_id}, "
            f"Erro: {str(error)}, Tipo: {type(error).__name__}"
        )
        
        # Log do stack trace para debugging
        if current_app.debug:
            self.logger.debug(
                f"[CLEANUP-AUDIT] Stack trace - ID: {self.operation.operation_id}:\n"
                f"{traceback.format_exc()}"
            )
    
    def log_final_state(self, final_versions: List[str], final_active: str):
        """Registra o estado final após a operação."""
        self.logger.info(
            f"[CLEANUP-AUDIT] Estado final - ID: {self.operation.operation_id}, "
            f"Versões disponíveis: {final_versions}, Versão ativa: {final_active}"
        )


def analyze_key_usage(session, model_cls, column_name: str, batch_size: int = 1000) -> Dict[str, int]:
    """
    Analisa dados criptografados em lotes para identificar quais versões de chaves estão em uso.
    
    Esta função percorre todos os registros de uma coluna criptografada de um modelo para determinar
    quais versões de chaves de criptografia estão sendo usadas nos dados armazenados.
    
    Args:
        session: Sessão do SQLAlchemy para consultas ao banco de dados
        model_cls: A classe do modelo SQLAlchemy a ser analisada
        column_name: Nome da coluna criptografada a ser analisada
        batch_size: Número de registros a processar por lote (padrão: 1000)
        
    Returns:
        Dict[str, int]: Mapeamento de versão -> contagem de registros usando essa versão
        
    Raises:
        RuntimeError: Se o modelo não tiver primary key ou tiver primary key composta
        ValueError: Se a coluna não existir no modelo
    """
    # Obter nome da primary key para processamento em lotes
    pk_name = get_primary_key_name(model_cls)
    
    # Verificar se a coluna existe
    if not hasattr(model_cls, column_name):
        raise ValueError(f"Coluna '{column_name}' não encontrada no modelo {model_cls.__name__}")
    
    # Obter SecretsManager para detecção de versões
    sm: SecretsManager = current_app.extensions.get('secrets_manager')
    if not sm:
        raise RuntimeError("SecretsManager não inicializado")
    
    version_counts = defaultdict(int)
    total_processed = 0
    
    # Processar registros em lotes com acompanhamento de progresso
    with click.progressbar(
        length=session.query(model_cls).count(),
        label=f'Analisando {model_cls.__name__}.{column_name}',
        show_pos=True
    ) as bar:
        
        for batch in iter_records_in_batches(session, model_cls, pk_name, batch_size=batch_size):
            for obj in batch:
                pk_val = getattr(obj, pk_name)
                
                try:
                    # Obter valor criptografado bruto do banco de dados
                    raw_query = text(f"SELECT {column_name} FROM {model_cls.__tablename__} WHERE {pk_name} = :pk")
                    
                    # Tratar primary keys UUID corretamente
                    if hasattr(pk_val, 'hex'):
                        pk_param = pk_val.hex
                    else:
                        pk_param = str(pk_val)
                    
                    raw_result = session.execute(raw_query, {"pk": pk_param})
                    raw_encrypted_val = raw_result.scalar()
                    
                    if not raw_encrypted_val:
                        continue
                    
                    # Determinar versão usada para este registro
                    version_used = _detect_encryption_version(raw_encrypted_val, sm)
                    if version_used:
                        version_counts[version_used] += 1
                    
                    total_processed += 1
                    bar.update(1)
                    
                except Exception as e:
                    current_app.logger.warning(
                        f"Erro ao analisar registro {pk_name}={pk_val}: {e}"
                    )
                    bar.update(1)
                    continue
    
    current_app.logger.info(f"Análise de uso de chaves concluída: {total_processed} registros processados")
    return dict(version_counts)


def _detect_encryption_version(encrypted_value: str, sm: SecretsManager) -> str:
    """
    Detecta qual versão de criptografia foi usada para um valor criptografado específico.
    
    Args:
        encrypted_value: A string criptografada bruta do banco de dados
        sm: Instância do SecretsManager para descriptografia
        
    Returns:
        str: A string da versão que foi usada, ou None se a detecção falhar
    """
    from app.models.custom_types import EncryptedString
    
    try:
        # Verificar se o valor tem prefixo de versão (formato novo: "v1:base64data")
        if EncryptedString.VERSION_SEPARATOR in encrypted_value:
            version_hint, b64_ct = encrypted_value.split(EncryptedString.VERSION_SEPARATOR, 1)
            ciphertext = base64.urlsafe_b64decode(b64_ct.encode('ascii'))
        else:
            # Formato legado sem prefixo de versão
            version_hint = None
            ciphertext = base64.urlsafe_b64decode(encrypted_value.encode('ascii'))
        
        # Usar SecretsManager.decrypt() para determinar qual versão foi realmente usada
        version_used, _ = sm.decrypt(ciphertext, version_hint)
        return version_used
        
    except Exception:
        # Se a descriptografia falhar, retornar o hint se disponível, senão None
        if EncryptedString.VERSION_SEPARATOR in encrypted_value:
            return encrypted_value.split(EncryptedString.VERSION_SEPARATOR, 1)[0]
        return None


def calculate_usage_statistics(version_counts: Dict[str, int], active_version: str) -> List[KeyUsageStats]:
    """
    Calcula estatísticas detalhadas sobre o uso de versões de chaves.
    
    Args:
        version_counts: Dicionário mapeando versão -> contagem de registros
        active_version: A versão de criptografia atualmente ativa
        
    Returns:
        List[KeyUsageStats]: Lista de estatísticas de uso para cada versão
    """
    total_records = sum(version_counts.values())
    stats = []
    
    for version, count in version_counts.items():
        percentage = (count / total_records * 100) if total_records > 0 else 0
        is_active = version == active_version
        # Por enquanto, marcar como removível se não for ativa e não estiver em uso
        # Isso será refinado pela lógica de limpeza nas próximas tarefas
        is_removable = not is_active and count == 0
        
        stats.append(KeyUsageStats(
            version=version,
            record_count=count,
            percentage=percentage,
            is_active=is_active,
            is_removable=is_removable
        ))
    
    # Ordenar por nome da versão para saída consistente
    return sorted(stats, key=lambda x: x.version)


def load_model_from_path(path: str):
    """
    Carrega dinamicamente uma classe de modelo a partir de uma string de caminho.

    Formatos aceitos:
      1. module:Class  (ex.: app.models.user:User)
      2. module.Class  (ex.: app.models.user.User)

    A diferença entre os formatos é apenas sintática; ambos resultam no
    import do módulo indicado e na obtenção do atributo de nome `Class`.

    Args:
        path (str): Caminho no formato 'module:Class' ou 'module.Class'.

    Returns:
        Any: A referência à classe (não instanciada) localizada.

    Raises:
        ValueError: Se o formato não corresponder aos aceitos.
        ModuleNotFoundError: Se o módulo não puder ser importado.
        AttributeError: Se a classe não existir dentro do módulo.

    Exemplo:
        cls = load_model_from_path("app.models.user:User")
        instancia = cls()

    Observacao de seguranca:
        Evite aceitar valores arbitrários não validados de usuários finais,
        pois permite importação dinâmica de qualquer módulo acessível.
    """
    if ':' in path:
        module_path, cls_name = path.split(':', 1)
    elif path.count('.') >= 1:
        module_path, cls_name = path.rsplit('.', 1)
    else:
        raise ValueError("model_path deve ser 'module:Class' ou 'module.Class'")

    module = importlib.import_module(module_path)
    return getattr(module, cls_name)


def get_primary_key_name(model_cls) -> str:
    """
    Obtém o nome da coluna de primary key de um modelo SQLAlchemy.

    Args:
        model_cls: A classe do modelo SQLAlchemy a ser inspecionada.

    Returns:
        str: O nome da coluna de primary key.

    Raises:
        RuntimeError: Se o modelo não tiver primary key ou tiver primary key composta.
    """
    mapper = inspect(model_cls)
    pks = [c.name for c in mapper.primary_key]

    if not pks:
        raise RuntimeError(f"Modelo {model_cls.__name__} não tem primary key")
    if len(pks) > 1:
        raise RuntimeError(
                f"Modelo {model_cls.__name__} tem primary key composta. "
                f"Não suportado nesta implementação."
        )

    return pks[0]


def iter_records_in_batches(session,
                            model_cls,
                            pk_name: str,
                            start_after: Any = None,
                            batch_size: int = 100):
    """
    Itera registros em batches ordenados por primary key (PK).

    Evita problemas de performance com offset crescente ao usar filtro PK > last_pk
    para processar registros em lotes sequenciais.

    Args:
        session: Sessão do SQLAlchemy para executar as consultas.
        model_cls: Classe do modelo SQLAlchemy a ser consultada.
        pk_name (str): Nome da coluna de primary key.
        start_after (Any, optional): Valor da PK para iniciar a iteração após este ponto.
            Se None, começa do início. Defaults to None.
        batch_size (int, optional): Número de registros por batch. Defaults to 100.

    Yields:
        list: Lista de objetos do modelo para cada batch processado.

    Raises:
        Nenhum erro específico é levantado diretamente, mas consultas podem falhar
        se a sessão ou modelo forem inválidos.
    """
    while True:
        query = session.query(model_cls).order_by(asc(getattr(model_cls, pk_name)))

        if start_after is not None:
            query = query.filter(getattr(model_cls, pk_name) > start_after)

        batch = query.limit(batch_size).all()

        if not batch:
            break

        yield batch

        # Atualiza filtro para próximo batch
        start_after = getattr(batch[-1], pk_name)


@dataclass
class CleanupValidationResult:
    """Resultado da validação de limpeza de chaves."""
    is_valid: bool
    error_message: str = ""
    versions_to_keep: List[str] = None
    versions_to_remove: List[str] = None
    
    def __post_init__(self):
        if self.versions_to_keep is None:
            self.versions_to_keep = []
        if self.versions_to_remove is None:
            self.versions_to_remove = []


def identify_removable_versions(all_versions: List[str], 
                              used_versions: Set[str], 
                              active_version: str, 
                              keep_count: int) -> Tuple[List[str], List[str]]:
    """
    Identifica quais versões podem ser removidas com segurança.
    
    Esta função implementa a lógica central para determinar quais versões de chaves
    podem ser removidas, respeitando as regras de segurança:
    - Nunca remover a versão ativa
    - Nunca remover versões em uso nos dados
    - Manter pelo menos o número especificado de versões mais recentes
    
    Args:
        all_versions: Lista de todas as versões disponíveis
        used_versions: Conjunto de versões que estão em uso nos dados
        active_version: A versão atualmente ativa
        keep_count: Número mínimo de versões a manter
        
    Returns:
        Tuple[List[str], List[str]]: (versions_to_keep, versions_to_remove)
        
    Requirements: 1.4, 1.5, 2.3, 5.3
    """
    if not all_versions:
        return [], []
    
    # Ordenar versões (assumindo formato v1, v2, v3, etc.)
    sorted_versions = sorted(all_versions, key=lambda v: _extract_version_number(v), reverse=True)
    
    # Versões que DEVEM ser mantidas (critérios de segurança)
    must_keep = set()
    
    # 1. Sempre manter versão ativa (Requirement 1.4)
    if active_version in sorted_versions:
        must_keep.add(active_version)
    
    # 2. Sempre manter versões em uso nos dados (Requirement 5.3)
    must_keep.update(used_versions)
    
    # 3. Manter as versões mais recentes até atingir keep_count (Requirement 2.3)
    recent_versions = sorted_versions[:keep_count]
    must_keep.update(recent_versions)
    
    # Separar versões para manter e remover
    versions_to_keep = sorted([v for v in sorted_versions if v in must_keep])
    versions_to_remove = sorted([v for v in sorted_versions if v not in must_keep])
    
    return versions_to_keep, versions_to_remove


def validate_cleanup_safety(all_versions: List[str], 
                          used_versions: Set[str], 
                          active_version: str, 
                          keep_count: int) -> CleanupValidationResult:
    """
    Valida se a operação de limpeza pode ser executada com segurança.
    
    Esta função executa todas as verificações de segurança necessárias antes
    de permitir a remoção de versões de chaves, garantindo que:
    - O número de versões a manter é válido
    - A versão ativa não será removida
    - Versões em uso não serão removidas
    - Pelo menos o número mínimo de versões será mantido
    
    Args:
        all_versions: Lista de todas as versões disponíveis
        used_versions: Conjunto de versões que estão em uso nos dados
        active_version: A versão atualmente ativa
        keep_count: Número de versões a manter
        
    Returns:
        CleanupValidationResult: Resultado da validação com detalhes
        
    Requirements: 1.4, 1.5, 2.3, 5.3
    """
    # Validação 1: keep_count deve ser pelo menos 1 (Requirement 2.3)
    if keep_count < 1:
        return CleanupValidationResult(
            is_valid=False,
            error_message="Número de versões a manter deve ser pelo menos 1"
        )
    
    # Validação 2: Verificar se versão ativa existe
    if active_version not in all_versions:
        return CleanupValidationResult(
            is_valid=False,
            error_message=f"Versão ativa '{active_version}' não encontrada nas versões disponíveis"
        )
    
    # Identificar versões para manter e remover
    versions_to_keep, versions_to_remove = identify_removable_versions(
        all_versions, used_versions, active_version, keep_count
    )
    
    # Validação 3: Versão ativa deve estar nas versões a manter (Requirement 1.4)
    if active_version not in versions_to_keep:
        return CleanupValidationResult(
            is_valid=False,
            error_message=f"Versão ativa '{active_version}' seria removida, operação não permitida"
        )
    
    # Validação 4: Versões em uso devem estar nas versões a manter (Requirement 5.3)
    used_versions_to_remove = used_versions.intersection(set(versions_to_remove))
    if used_versions_to_remove:
        return CleanupValidationResult(
            is_valid=False,
            error_message=f"Versões em uso nos dados seriam removidas: {sorted(used_versions_to_remove)}"
        )
    
    # Validação 5: Deve manter pelo menos keep_count versões (Requirement 2.3)
    if len(versions_to_keep) < keep_count:
        return CleanupValidationResult(
            is_valid=False,
            error_message=f"Não é possível manter {keep_count} versões (apenas {len(versions_to_keep)} disponíveis)"
        )
    
    return CleanupValidationResult(
        is_valid=True,
        versions_to_keep=versions_to_keep,
        versions_to_remove=versions_to_remove
    )


def ensure_minimum_versions_kept(all_versions: List[str], 
                               versions_to_remove: List[str], 
                               min_keep: int) -> List[str]:
    """
    Garante que o número mínimo de versões seja mantido.
    
    Esta função ajusta a lista de versões a serem removidas para garantir
    que pelo menos min_keep versões sejam preservadas. Remove versões da
    lista de remoção começando pelas mais recentes se necessário.
    
    Args:
        all_versions: Lista de todas as versões disponíveis
        versions_to_remove: Lista de versões candidatas à remoção
        min_keep: Número mínimo de versões a manter
        
    Returns:
        List[str]: Lista ajustada de versões a remover
        
    Requirements: 2.3
    """
    if len(all_versions) <= min_keep:
        # Se o total de versões é menor ou igual ao mínimo, não remover nenhuma
        return []
    
    max_removable = len(all_versions) - min_keep
    
    if len(versions_to_remove) <= max_removable:
        # Pode remover todas as versões candidatas
        return versions_to_remove
    
    # Precisa reduzir a lista de remoção
    # Ordenar por número de versão (mais antigas primeiro para remoção)
    sorted_to_remove = sorted(versions_to_remove, key=lambda v: _extract_version_number(v))
    
    return sorted_to_remove[:max_removable]


def validate_active_version_preservation(active_version: str, 
                                       versions_to_remove: List[str]) -> bool:
    """
    Valida que a versão ativa não está na lista de remoção.
    
    Args:
        active_version: A versão atualmente ativa
        versions_to_remove: Lista de versões a serem removidas
        
    Returns:
        bool: True se a versão ativa será preservada, False caso contrário
        
    Requirements: 1.4
    """
    return active_version not in versions_to_remove


def validate_used_versions_preservation(used_versions: Set[str], 
                                      versions_to_remove: List[str]) -> Tuple[bool, Set[str]]:
    """
    Valida que versões em uso nos dados não estão na lista de remoção.
    
    Args:
        used_versions: Conjunto de versões em uso nos dados
        versions_to_remove: Lista de versões a serem removidas
        
    Returns:
        Tuple[bool, Set[str]]: (is_valid, conflicting_versions)
        
    Requirements: 5.3
    """
    conflicting_versions = used_versions.intersection(set(versions_to_remove))
    is_valid = len(conflicting_versions) == 0
    
    return is_valid, conflicting_versions


def _extract_version_number(version: str) -> int:
    """
    Extrai o número da versão para ordenação.
    
    Usa EncryptedString.VERSION_PREFIX para determinar o formato da versão.
    Retorna 0 para versões que não seguem o padrão.
    
    Args:
        version: String da versão (ex: 'v1', 'v2')
        
    Returns:
        int: Número da versão para ordenação
    """
    from app.models.custom_types import EncryptedString
    
    try:
        if version.startswith(EncryptedString.VERSION_PREFIX):
            return int(version[len(EncryptedString.VERSION_PREFIX):])
        return int(version)
    except (ValueError, IndexError):
        return 0


# Configuration Backup and Restore Functionality

@dataclass
class BackupResult:
    """Resultado de uma operação de backup."""
    success: bool
    backup_file: Optional[str] = None
    error_message: Optional[str] = None


def backup_configuration(env_file: str) -> BackupResult:
    """
    Cria backup do arquivo de configuração com timestamp.
    
    Esta função cria uma cópia de segurança do arquivo de configuração
    antes de modificações, usando um nome baseado em timestamp para
    evitar conflitos e permitir múltiplos backups.
    
    Args:
        env_file: Caminho para o arquivo de configuração a ser copiado
        
    Returns:
        BackupResult: Resultado da operação com caminho do backup ou erro
        
    Requirements: 6.1
    """
    try:
        # Verificar se o arquivo original existe
        env_path = Path(env_file)
        if not env_path.exists():
            return BackupResult(
                success=False,
                error_message=f"Arquivo de configuração não encontrado: {env_file}"
            )

        # Gerar nome do backup com timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = f"{env_file}.backup_{timestamp}"
        backup_path = Path(backup_file)

        # Criar backup
        shutil.copy2(env_file, backup_file)

        # Verificar se o backup foi criado corretamente
        if not backup_path.exists():
            return BackupResult(
                success=False,
                error_message=f"Falha ao criar arquivo de backup: {backup_file}"
            )
        
        # Definir permissões seguras no backup (mesmas do original)
        original_stat = env_path.stat()
        backup_path.chmod(original_stat.st_mode)
        
        current_app.logger.info(f"Backup criado com sucesso: {backup_file}")
        
        return BackupResult(
            success=True,
            backup_file=backup_file
        )
        
    except PermissionError as e:
        return BackupResult(
            success=False,
            error_message=f"Permissão negada ao criar backup: {e}"
        )
    except OSError as e:
        return BackupResult(
            success=False,
            error_message=f"Erro de sistema ao criar backup: {e}"
        )
    except Exception as e:
        return BackupResult(
            success=False,
            error_message=f"Erro inesperado ao criar backup: {e}"
        )


def restore_configuration(backup_file: str, original_file: str) -> bool:
    """
    Restaura configuração a partir de um arquivo de backup.
    
    Esta função restaura um arquivo de configuração a partir de um backup,
    usado em cenários de rollback quando uma operação de limpeza falha.
    
    Args:
        backup_file: Caminho para o arquivo de backup
        original_file: Caminho para o arquivo original a ser restaurado
        
    Returns:
        bool: True se a restauração foi bem-sucedida, False caso contrário
        
    Requirements: 6.2
    """
    try:
        # Verificar se o backup existe
        backup_path = Path(backup_file)
        if not backup_path.exists():
            current_app.logger.error(f"Arquivo de backup não encontrado: {backup_file}")
            return False

        # Fazer backup do estado atual antes de restaurar (por segurança)
        original_path = Path(original_file)
        if original_path.exists():
            temp_backup = f"{original_file}.temp_before_restore"
            try:
                shutil.copy2(original_file, temp_backup)
            except Exception as e:
                current_app.logger.warning(f"Não foi possível criar backup temporário: {e}")

        # Restaurar do backup
        shutil.copy2(backup_file, original_file)

        # Verificar se a restauração foi bem-sucedida
        if not original_path.exists():
            current_app.logger.error(f"Falha na restauração: arquivo não foi criado: {original_file}")
            return False

        current_app.logger.info(f"Configuração restaurada com sucesso de: {backup_file}")

        # Limpar backup temporário se existir
        temp_backup_path = Path(f"{original_file}.temp_before_restore")
        if temp_backup_path.exists():
            try:
                temp_backup_path.unlink()
            except Exception as e:
                current_app.logger.warning(f"Não foi possível remover backup temporário: {e}")
        
        return True
        
    except PermissionError as e:
        current_app.logger.error(f"Permissão negada ao restaurar configuração: {e}")
        return False
    except OSError as e:
        current_app.logger.error(f"Erro de sistema ao restaurar configuração: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Erro inesperado ao restaurar configuração: {e}")
        return False


def cleanup_old_backups(env_file: str, keep_backups: int = 5) -> int:
    """
    Remove backups antigos mantendo apenas os mais recentes.
    
    Esta função limpa backups antigos para evitar acúmulo excessivo de arquivos,
    mantendo apenas o número especificado de backups mais recentes.
    
    Args:
        env_file: Caminho do arquivo de configuração original
        keep_backups: Número de backups a manter (padrão: 5)
        
    Returns:
        int: Número de backups removidos
    """
    try:
        # Encontrar todos os arquivos de backup
        env_path = Path(env_file)
        env_dir = env_path.parent
        env_basename = env_path.name

        backup_files = []
        for item in env_dir.iterdir():
            if item.name.startswith(f"{env_basename}.backup_"):
                if item.is_file():
                    # Extrair timestamp do nome do arquivo
                    try:
                        timestamp_str = item.name.split('.backup_')[1]
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        backup_files.append((str(item), timestamp))
                    except (IndexError, ValueError):
                        # Ignorar arquivos com formato de timestamp inválido
                        continue
        
        # Ordenar por timestamp (mais recentes primeiro)
        backup_files.sort(key=lambda x: x[1], reverse=True)
        
        # Remover backups antigos
        removed_count = 0
        for backup_path_str, _ in backup_files[keep_backups:]:
            try:
                Path(backup_path_str).unlink()
                removed_count += 1
                current_app.logger.info(f"Backup antigo removido: {backup_path_str}")
            except Exception as e:
                current_app.logger.warning(f"Erro ao remover backup antigo {backup_path_str}: {e}")
        
        return removed_count
        
    except Exception as e:
        current_app.logger.error(f"Erro ao limpar backups antigos: {e}")
        return 0


def validate_backup_integrity(backup_file: str, original_file: str) -> bool:
    """
    Valida a integridade de um arquivo de backup.
    
    Esta função verifica se um backup é válido comparando tamanhos e
    verificando se o conteúdo pode ser lido corretamente.
    
    Args:
        backup_file: Caminho para o arquivo de backup
        original_file: Caminho para o arquivo original (para comparação)
        
    Returns:
        bool: True se o backup é válido, False caso contrário
    """
    try:
        # Verificar se o backup existe e é legível
        backup_path = Path(backup_file)
        if not backup_path.exists():
            return False

        # Verificar se o arquivo não está vazio
        try:
            file_size = backup_path.stat().st_size
            if file_size == 0:
                return False
        except (OSError, PermissionError):
            # Arquivo não é acessível
            return False

        # Tentar ler o conteúdo para verificar se não está corrompido
        try:
            with backup_path.open('r', encoding='utf-8') as f:
                content = f.read()
                # Verificar se contém pelo menos algumas linhas de configuração esperadas
                if 'ENCRYPTION_KEYS__' not in content and 'ACTIVE_ENCRYPTION_VERSION' not in content:
                    current_app.logger.warning(f"Backup pode estar corrompido - não contém chaves esperadas: {backup_file}")
                    return False
        except UnicodeDecodeError:
            current_app.logger.error(f"Backup contém caracteres inválidos: {backup_file}")
            return False
        except Exception as e:
            current_app.logger.error(f"Erro ao ler backup: {backup_file}: {e}")
            return False
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Erro ao validar integridade do backup: {e}")
        return False


@dataclass
class ConfigModificationResult:
    """Resultado de uma operação de modificação de configuração."""
    success: bool
    lines_removed: int = 0
    versions_removed: List[str] = None
    error_message: Optional[str] = None
    temp_file: Optional[str] = None
    
    def __post_init__(self):
        if self.versions_removed is None:
            self.versions_removed = []


def remove_versions_from_config(env_file: str, versions_to_remove: List[str]) -> ConfigModificationResult:
    """
    Remove versões específicas do arquivo de configuração com operações atômicas.
    
    Esta função remove as linhas de configuração relacionadas às versões
    especificadas, mantendo todas as outras configurações intactas. Usa
    operações atômicas para garantir que o arquivo não seja corrompido
    em caso de falha durante a escrita.
    
    Args:
        env_file: Caminho para o arquivo de configuração
        versions_to_remove: Lista de versões a serem removidas
        
    Returns:
        ConfigModificationResult: Resultado detalhado da operação
        
    Requirements: 1.3, 6.3
    """
    if not versions_to_remove:
        return ConfigModificationResult(
            success=True,
            lines_removed=0,
            versions_removed=[]
        )
    
    try:
        # Verificar se o arquivo existe
        env_path = Path(env_file)
        if not env_path.exists():
            return ConfigModificationResult(
                success=False,
                error_message=f"Arquivo de configuração não encontrado: {env_file}"
            )
        
        # Ler o arquivo atual
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filtrar linhas que não correspondem às versões a remover
        filtered_lines = []
        removed_count = 0
        actually_removed_versions = set()
        
        for line in lines:
            should_remove = False
            
            # Verificar se a linha contém configuração de alguma versão a remover
            for version in versions_to_remove:
                if _line_contains_version_config(line, version):
                    should_remove = True
                    removed_count += 1
                    actually_removed_versions.add(version)
                    current_app.logger.info(f"Removendo linha de configuração para {version}: {line.strip()}")
                    break
            
            if not should_remove:
                filtered_lines.append(line)
        
        # Atualizar timestamp no cabeçalho do arquivo
        filtered_lines = _update_config_timestamp(filtered_lines)
        
        # Escrever arquivo usando operação atômica
        write_result = _write_config_atomically(env_file, filtered_lines)
        
        if not write_result.success:
            return ConfigModificationResult(
                success=False,
                error_message=write_result.error_message,
                temp_file=write_result.temp_file
            )
        
        # Validar integridade após modificação
        if not validate_config_integrity(env_file):
            return ConfigModificationResult(
                success=False,
                error_message="Falha na validação de integridade após modificação",
                temp_file=write_result.temp_file
            )
        
        current_app.logger.info(f"Removidas {removed_count} linhas de configuração para versões: {sorted(actually_removed_versions)}")
        
        return ConfigModificationResult(
            success=True,
            lines_removed=removed_count,
            versions_removed=sorted(actually_removed_versions),
            temp_file=write_result.temp_file
        )
        
    except PermissionError as e:
        return ConfigModificationResult(
            success=False,
            error_message=f"Permissão negada ao modificar configuração: {e}"
        )
    except OSError as e:
        return ConfigModificationResult(
            success=False,
            error_message=f"Erro de sistema ao modificar configuração: {e}"
        )
    except Exception as e:
        return ConfigModificationResult(
            success=False,
            error_message=f"Erro inesperado ao modificar configuração: {e}"
        )


@dataclass
class AtomicWriteResult:
    """Resultado de uma operação de escrita atômica."""
    success: bool
    temp_file: Optional[str] = None
    error_message: Optional[str] = None


def _write_config_atomically(target_file: str, lines: List[str]) -> AtomicWriteResult:
    """
    Escreve arquivo de configuração usando operação atômica.
    
    Esta função escreve primeiro em um arquivo temporário e depois
    move para o destino final, garantindo que o arquivo original
    não seja corrompido em caso de falha durante a escrita.
    
    Args:
        target_file: Caminho do arquivo de destino
        lines: Linhas a serem escritas
        
    Returns:
        AtomicWriteResult: Resultado da operação atômica
        
    Requirements: 6.3
    """
    import tempfile
    
    temp_file = None
    try:
        # Criar arquivo temporário no mesmo diretório do arquivo de destino
        target_path = Path(target_file)
        target_dir = target_path.parent
        target_basename = target_path.name

        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=str(target_dir),
            prefix=f".{target_basename}.tmp.",
            suffix='.tmp',
            delete=False
        ) as temp_f:
            temp_file = temp_f.name
            temp_f.writelines(lines)
            temp_f.flush()
            os.fsync(temp_f.fileno())  # Forçar escrita no disco

        temp_path = Path(temp_file)

        # Copiar permissões do arquivo original
        if target_path.exists():
            original_stat = target_path.stat()
            temp_path.chmod(original_stat.st_mode)
        else:
            # Definir permissões seguras para novo arquivo
            temp_path.chmod(0o600)

        # Mover arquivo temporário para destino final (operação atômica)
        if os.name == 'nt':  # Windows
            # No Windows, precisamos remover o arquivo de destino primeiro
            if target_path.exists():
                target_path.unlink()

        shutil.move(temp_file, target_file)

        return AtomicWriteResult(
            success=True,
            temp_file=temp_file
        )

    except Exception as e:
        # Limpar arquivo temporário em caso de erro
        if temp_file:
            temp_path = Path(temp_file)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass  # Ignorar erros de limpeza
        
        return AtomicWriteResult(
            success=False,
            temp_file=temp_file,
            error_message=f"Erro na escrita atômica: {e}"
        )


def _update_config_timestamp(lines: List[str]) -> List[str]:
    """
    Atualiza o timestamp no cabeçalho do arquivo de configuração.
    
    Esta função procura por linhas de comentário com timestamp e as atualiza
    com o timestamp atual, ou adiciona uma nova linha de timestamp se não existir.
    
    Args:
        lines: Lista de linhas do arquivo de configuração
        
    Returns:
        List[str]: Lista de linhas com timestamp atualizado
    """
    updated_lines = []
    timestamp_updated = False
    current_timestamp = f"# Atualizado em {datetime.now(timezone.utc).isoformat()}Z\n"
    
    for line in lines:
        # Verificar se é uma linha de timestamp existente
        if line.strip().startswith('# Atualizado em') or line.strip().startswith('# Gerado em'):
            if not timestamp_updated:
                updated_lines.append(current_timestamp)
                timestamp_updated = True
            # Pular a linha antiga de timestamp
            continue
        else:
            updated_lines.append(line)
    
    # Se não encontrou timestamp existente, adicionar no início
    if not timestamp_updated:
        updated_lines.insert(0, current_timestamp)
    
    return updated_lines


def _line_contains_version_config(line: str, version: str) -> bool:
    """
    Verifica se uma linha contém configuração para uma versão específica.
    
    Esta função verifica todos os tipos de configuração relacionados a uma versão:
    - ENCRYPTION_KEYS__<version>=
    - ENCRYPTION_SALT__<version>=
    - ENCRYPTION_SALT_HASH__<version>=
    
    Args:
        line: Linha do arquivo de configuração
        version: Versão a verificar
        
    Returns:
        bool: True se a linha contém configuração da versão
    """
    line_stripped = line.strip()
    
    # Ignorar comentários e linhas vazias
    if not line_stripped or line_stripped.startswith('#'):
        return False
    
    # Verificar todos os tipos de configuração para a versão
    config_patterns = [
        f'ENCRYPTION_KEYS__{version}=',
        f'ENCRYPTION_SALT__{version}=',
        f'ENCRYPTION_SALT_HASH__{version}='
    ]
    
    return any(pattern in line for pattern in config_patterns)


def validate_config_integrity(env_file: str) -> bool:
    """
    Valida a integridade de um arquivo de configuração.
    
    Esta função verifica se o arquivo de configuração está bem formado
    e contém as configurações mínimas necessárias para funcionamento.
    
    Args:
        env_file: Caminho para o arquivo de configuração
        
    Returns:
        bool: True se o arquivo é válido, False caso contrário
        
    Requirements: 6.3
    """
    try:
        env_path = Path(env_file)
        if not env_path.exists():
            current_app.logger.error(f"Arquivo de configuração não existe: {env_file}")
            return False

        # Verificar se o arquivo não está vazio e é acessível
        try:
            file_size = env_path.stat().st_size
            if file_size == 0:
                current_app.logger.error(f"Arquivo de configuração está vazio: {env_file}")
                return False
        except (OSError, PermissionError):
            current_app.logger.error(f"Arquivo de configuração não é legível: {env_file}")
            return False

        # Ler e validar conteúdo
        with env_path.open('r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Verificar estrutura básica
        has_active_version = False
        encryption_keys = set()
        active_version = None
        
        for line in lines:
            line_stripped = line.strip()
            
            # Ignorar comentários e linhas vazias
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Verificar formato básico de variável de ambiente
            if '=' not in line_stripped:
                current_app.logger.warning(f"Linha mal formada no arquivo de configuração: {line_stripped}")
                continue
            
            var_name, var_value = line_stripped.split('=', 1)
            
            # Verificar versão ativa
            if var_name == 'ACTIVE_ENCRYPTION_VERSION':
                has_active_version = True
                active_version = var_value.strip('"\'')
            
            # Coletar chaves de criptografia
            elif var_name.startswith('ENCRYPTION_KEYS__'):
                version = var_name.replace('ENCRYPTION_KEYS__', '')
                encryption_keys.add(version)
        
        # Validações de integridade
        if not has_active_version:
            current_app.logger.error("Arquivo de configuração não contém ACTIVE_ENCRYPTION_VERSION")
            return False
        
        if not encryption_keys:
            current_app.logger.error("Arquivo de configuração não contém chaves de criptografia")
            return False
        
        if active_version and active_version not in encryption_keys:
            current_app.logger.error(f"Versão ativa '{active_version}' não tem chave correspondente")
            return False
        
        current_app.logger.debug(f"Validação de integridade bem-sucedida para: {env_file}")
        return True
        
    except UnicodeDecodeError as e:
        current_app.logger.error(f"Arquivo de configuração contém caracteres inválidos: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Erro ao validar integridade da configuração: {e}")
        return False


def get_config_versions(env_file: str) -> List[str]:
    """
    Obtém todas as versões de chaves presentes no arquivo de configuração.
    
    Args:
        env_file: Caminho para o arquivo de configuração
        
    Returns:
        List[str]: Lista de versões encontradas no arquivo
    """
    versions = set()

    try:
        env_path = Path(env_file)
        if not env_path.exists():
            return []
        
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_stripped = line.strip()
                
                # Ignorar comentários e linhas vazias
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # Procurar por chaves de criptografia
                if line_stripped.startswith('ENCRYPTION_KEYS__') and '=' in line_stripped:
                    var_name = line_stripped.split('=', 1)[0]
                    version = var_name.replace('ENCRYPTION_KEYS__', '')
                    versions.add(version)
        
        return sorted(versions, key=lambda v: _extract_version_number(v))
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter versões do arquivo de configuração: {e}")
        return []


class CleanupOrchestrator:
    """Orquestrador principal para operações de limpeza de chaves com tratamento de erro abrangente."""
    
    def __init__(self, operation: CleanupOperation):
        self.operation = operation
        self.audit_logger = CleanupAuditLogger(operation)
        self.session = None
        self.sm = None
        
    def execute(self) -> CleanupOperation:
        """
        Executa a operação completa de limpeza com tratamento de erro abrangente.
        
        Returns:
            CleanupOperation: Operação atualizada com resultados
            
        Requirements: 3.3, 3.4, 6.2, 6.3, 6.4
        """
        self.operation.start_time = datetime.now(timezone.utc)
        self.audit_logger.log_start()
        
        try:
            # Inicialização e validação
            self._initialize_components()
            self._validate_parameters()
            
            # Fase 1: Análise
            self._execute_analysis_phase()
            
            # Fase 2: Planejamento e validação
            self._execute_planning_phase()
            
            # Fase 3: Execução (se não for dry-run)
            if not self.operation.dry_run:
                self._execute_modification_phase()
            
            # Marcar como sucesso
            self.operation.success = True
            self.operation.end_time = datetime.now(timezone.utc)
            
            # Log do estado final
            if self.sm:
                final_versions = self.sm.get_all_versions()
                final_active = self.sm.get_active_version()
                self.audit_logger.log_final_state(final_versions, final_active)
            
            return self.operation
            
        except Exception as e:
            self.operation.success = False
            self.operation.error_message = str(e)
            self.operation.end_time = datetime.now(timezone.utc)
            
            self.audit_logger.log_error(e)
            
            # Tentar rollback automático se necessário
            if not self.operation.dry_run and self.operation.backup_file:
                try:
                    self._perform_automatic_rollback(str(e))
                except Exception as rollback_error:
                    self.audit_logger.log_error(rollback_error)
                    # Adicionar erro de rollback à mensagem original
                    self.operation.error_message += f" | Erro no rollback: {rollback_error}"
            
            raise CleanupError(str(e), self.operation, e)
            
        finally:
            # Limpeza de recursos
            self._cleanup_resources()
    
    def _initialize_components(self):
        """Inicializa componentes necessários."""
        # Obter SecretsManager
        self.sm = current_app.extensions.get('secrets_manager')
        if not self.sm:
            raise CleanupError("SecretsManager não inicializado", self.operation)
        
        # Criar sessão do banco de dados
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=current_app.extensions['migrate'].db.engine)
        self.session = Session()
    
    def _validate_parameters(self):
        """Valida parâmetros da operação."""
        # Validar keep_versions
        if self.operation.keep_versions < 1:
            raise CleanupError("Número de versões a manter deve ser pelo menos 1", self.operation)
        
        # Validar modelo
        try:
            model_cls = load_model_from_path(self.operation.model_path)
        except (ValueError, ModuleNotFoundError, AttributeError) as e:
            raise CleanupError(f"Erro ao carregar modelo '{self.operation.model_path}': {e}", self.operation)
        
        # Verificar coluna
        if not hasattr(model_cls, self.operation.column_name):
            raise CleanupError(
                f"Coluna '{self.operation.column_name}' não encontrada no modelo {model_cls.__name__}", 
                self.operation
            )
        
        # Verificar arquivo de configuração
        env_path = Path(self.operation.env_file)
        if not env_path.exists():
            raise CleanupError(f"Arquivo de configuração não encontrado: {self.operation.env_file}", self.operation)
        
        # Armazenar classe do modelo para uso posterior
        self.model_cls = model_cls
    
    def _execute_analysis_phase(self):
        """Executa a fase de análise de uso de chaves."""
        try:
            # Obter informações sobre versões
            self.operation.active_version = self.sm.get_active_version()
            self.operation.versions_found = self.sm.get_all_versions()
            
            # Analisar uso de chaves nos dados
            version_counts = analyze_key_usage(
                self.session, self.model_cls, self.operation.column_name, batch_size=1000
            )
            
            self.operation.total_records_analyzed = sum(version_counts.values())
            self.operation.versions_in_use = list(version_counts.keys())
            
            self.audit_logger.log_analysis_complete()
            
        except Exception as e:
            raise CleanupError(f"Erro na fase de análise: {e}", self.operation, e)
    
    def _execute_planning_phase(self):
        """Executa a fase de planejamento e validação."""
        try:
            # Executar validações de segurança
            used_versions = set(self.operation.versions_in_use)
            validation_result = validate_cleanup_safety(
                self.operation.versions_found, 
                used_versions, 
                self.operation.active_version, 
                self.operation.keep_versions
            )
            
            if not validation_result.is_valid:
                raise CleanupError(f"Validação de segurança falhou: {validation_result.error_message}", self.operation)
            
            self.operation.versions_to_keep = validation_result.versions_to_keep
            self.operation.versions_to_remove = validation_result.versions_to_remove
            
            self.audit_logger.log_planning_complete()
            
        except Exception as e:
            raise CleanupError(f"Erro na fase de planejamento: {e}", self.operation, e)
    
    def _execute_modification_phase(self):
        """Executa a fase de modificação (backup + remoção)."""
        try:
            # Criar backup
            backup_result = backup_configuration(self.operation.env_file)
            if not backup_result.success:
                raise CleanupError(f"Falha ao criar backup: {backup_result.error_message}", self.operation)
            
            self.operation.backup_file = backup_result.backup_file
            self.audit_logger.log_backup_created()
            
            # Executar remoção
            modification_result = remove_versions_from_config(
                self.operation.env_file, 
                self.operation.versions_to_remove
            )
            
            if not modification_result.success:
                raise CleanupError(f"Falha na remoção: {modification_result.error_message}", self.operation)
            
            self.operation.lines_removed = modification_result.lines_removed
            
            # Validar integridade pós-modificação
            if not validate_config_integrity(self.operation.env_file):
                raise CleanupError("Falha na validação de integridade pós-modificação", self.operation)
            
            # Limpar cache do SecretsManager
            self.sm.clear_cache()
            
            self.audit_logger.log_execution_complete()
            
        except Exception as e:
            raise CleanupError(f"Erro na fase de modificação: {e}", self.operation, e)
    
    def _perform_automatic_rollback(self, reason: str):
        """Executa rollback automático em caso de erro."""
        if not self.operation.backup_file:
            raise CleanupError("Não é possível fazer rollback: backup não disponível", self.operation)
        
        success = restore_configuration(self.operation.backup_file, self.operation.env_file)
        if not success:
            raise CleanupError("Falha no rollback automático", self.operation)
        
        self.operation.rollback_performed = True
        self.audit_logger.log_rollback(reason)
        
        # Limpar cache após rollback
        if self.sm:
            self.sm.clear_cache()
    
    def _cleanup_resources(self):
        """Limpa recursos utilizados."""
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass  # Ignorar erros de limpeza


def get_active_version_from_config(env_file: str) -> Optional[str]:
    """
    Obtém a versão ativa do arquivo de configuração.
    
    Args:
        env_file: Caminho para o arquivo de configuração
        
    Returns:
        Optional[str]: Versão ativa ou None se não encontrada
    """
    try:
        env_path = Path(env_file)
        if not env_path.exists():
            return None
        
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_stripped = line.strip()
                
                if line_stripped.startswith('ACTIVE_ENCRYPTION_VERSION='):
                    _, value = line_stripped.split('=', 1)
                    return value.strip('"\'')
        
        return None
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter versão ativa do arquivo de configuração: {e}")
        return None


class ProgressReporter:
    """Classe para relatórios de progresso e estatísticas detalhadas."""
    
    def __init__(self, operation: CleanupOperation):
        self.operation = operation
    
    def display_operation_header(self):
        """Exibe cabeçalho da operação."""
        click.echo("=" * 60)
        click.echo("LIMPEZA DE CHAVES CRIPTOGRÁFICAS")
        click.echo("=" * 60)
        click.echo(f"ID da Operação: {self.operation.operation_id}")
        click.echo(f"Modelo: {self.operation.model_path}")
        click.echo(f"Coluna: {self.operation.column_name}")
        click.echo(f"Versões a manter: {self.operation.keep_versions}")
        click.echo(f"Arquivo de configuração: {self.operation.env_file}")
        click.echo(f"Modo: {'Simulação (dry-run)' if self.operation.dry_run else 'Execução real'}")
        click.echo(f"Iniciado em: {self.operation.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        click.echo()
    
    def display_analysis_results(self):
        """Exibe resultados da análise."""
        click.echo("=== FASE 1: ANÁLISE DE USO DE CHAVES ===")
        click.echo(f"Versão ativa: {self.operation.active_version}")
        click.echo(f"Versões disponíveis ({len(self.operation.versions_found)}): {sorted(self.operation.versions_found)}")
        click.echo(f"Total de registros analisados: {self.operation.total_records_analyzed}")
        
        if self.operation.versions_in_use:
            click.echo(f"Versões em uso nos dados: {sorted(self.operation.versions_in_use)}")
        else:
            click.echo("Nenhuma versão encontrada em uso nos dados")
        
        click.echo()
    
    def display_usage_statistics(self, usage_stats: List[KeyUsageStats]):
        """Exibe estatísticas detalhadas de uso."""
        if not usage_stats:
            click.echo("Nenhuma estatística de uso disponível")
            return
        
        click.echo("Estatísticas detalhadas de uso:")
        click.echo("-" * 50)
        
        for stat in usage_stats:
            status_markers = []
            if stat.is_active:
                status_markers.append("ATIVA")
            if stat.record_count > 0:
                status_markers.append("EM USO")
            
            status_str = f" [{', '.join(status_markers)}]" if status_markers else ""
            
            click.echo(f"  {stat.version:>6}: {stat.record_count:>8} registros ({stat.percentage:>5.1f}%){status_str}")
        
        click.echo()
    
    def display_planning_results(self):
        """Exibe resultados do planejamento."""
        click.echo("=== FASE 2: VALIDAÇÃO E PLANEJAMENTO ===")
        click.echo(f"Versões a manter ({len(self.operation.versions_to_keep)}): {sorted(self.operation.versions_to_keep)}")
        click.echo(f"Versões a remover ({len(self.operation.versions_to_remove)}): {sorted(self.operation.versions_to_remove)}")
        
        if not self.operation.versions_to_remove:
            click.echo()
            click.echo("[INFO] Nenhuma versão precisa ser removida.")
            return False
        
        click.echo()
        return True
    
    def display_dry_run_simulation(self):
        """Exibe simulação de dry-run."""
        click.echo("=== SIMULAÇÃO (DRY-RUN) ===")
        click.echo("Nenhuma modificação será feita.")
        
        # Mostrar linhas que seriam removidas
        click.echo(f"\nLinhas que seriam removidas do arquivo {self.operation.env_file}:")
        
        try:
            with open(self.operation.env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            lines_to_remove = []
            for line in lines:
                for version in self.operation.versions_to_remove:
                    if _line_contains_version_config(line, version):
                        lines_to_remove.append(line.strip())
                        break
            
            if lines_to_remove:
                for line in lines_to_remove:
                    click.echo(f"  - {line}")
            else:
                click.echo("  (nenhuma linha seria removida)")
            
        except Exception as e:
            click.echo(f"  [ERRO] Não foi possível simular remoção: {e}")
        
        click.echo(f"\n[DRY-RUN] Operação simulada com sucesso.")
        click.echo(f"Execute novamente sem --dry-run para aplicar as mudanças.")
    
    def display_confirmation_prompt(self) -> bool:
        """Exibe prompt de confirmação e retorna resposta do usuário."""
        click.echo("=== CONFIRMAÇÃO NECESSÁRIA ===")
        click.echo(f"\nATENÇÃO: Esta operação irá:")
        click.echo(f"  - Remover {len(self.operation.versions_to_remove)} versões de chaves do arquivo de configuração")
        click.echo(f"  - Criar backup automático do arquivo atual")
        click.echo(f"  - Versões a remover: {sorted(self.operation.versions_to_remove)}")
        
        return click.confirm("\nDeseja continuar com a limpeza?")
    
    def display_execution_progress(self):
        """Exibe progresso da execução."""
        click.echo("=== EXECUÇÃO REAL ===")
        
        # Simular progresso com steps
        with click.progressbar(
            length=4, 
            label='Executando limpeza',
            show_pos=True,
            item_show_func=lambda x: x
        ) as bar:
            bar.update(1, "Criando backup...")
            bar.update(1, "Removendo versões...")
            bar.update(1, "Validando integridade...")
            bar.update(1, "Finalizando...")
    
    def display_success_results(self, final_versions: List[str], final_active: str):
        """Exibe resultados de sucesso."""
        duration = (self.operation.end_time - self.operation.start_time).total_seconds()
        
        click.echo(f"\n=== LIMPEZA CONCLUÍDA COM SUCESSO ===")
        click.echo(f"Tempo de execução: {duration:.2f} segundos")
        click.echo(f"Linhas removidas: {self.operation.lines_removed}")
        click.echo(f"Versões removidas: {sorted(self.operation.versions_to_remove)}")
        click.echo(f"Versões mantidas: {sorted(self.operation.versions_to_keep)}")
        
        if self.operation.backup_file:
            click.echo(f"Backup disponível: {self.operation.backup_file}")
        
        click.echo(f"\nEstado final:")
        click.echo(f"  Versões disponíveis: {sorted(final_versions)}")
        click.echo(f"  Versão ativa: {final_active}")
        
        click.echo(f"\n[OK] Limpeza de chaves concluída com sucesso!")
    
    def display_error_results(self, error: CleanupError):
        """Exibe resultados de erro."""
        duration = (self.operation.end_time - self.operation.start_time).total_seconds() if self.operation.end_time else 0
        
        click.echo(f"\n=== ERRO NA LIMPEZA ===")
        click.echo(f"Tempo até erro: {duration:.2f} segundos")
        click.echo(f"Erro: {error}")
        
        if self.operation.rollback_performed:
            click.echo(f"[INFO] Rollback automático executado com sucesso")
            click.echo(f"[INFO] Configuração restaurada do backup: {self.operation.backup_file}")
        elif self.operation.backup_file:
            click.echo(f"[INFO] Backup disponível para restauração manual: {self.operation.backup_file}")
        
        if error.original_error and current_app.debug:
            click.echo(f"\nDetalhes técnicos (modo debug):")
            click.echo(f"  Tipo: {type(error.original_error).__name__}")
            click.echo(f"  Mensagem: {error.original_error}")


def update_active_version_in_config(env_file: str, new_active_version: str) -> bool:
    """
    Atualiza a versão ativa no arquivo de configuração.
    
    Args:
        env_file: Caminho para o arquivo de configuração
        new_active_version: Nova versão ativa
        
    Returns:
        bool: True se a atualização foi bem-sucedida
    """
    try:
        env_path = Path(env_file)
        if not env_path.exists():
            current_app.logger.error(f"Arquivo de configuração não encontrado: {env_file}")
            return False
        
        # Ler arquivo atual
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Atualizar linha da versão ativa
        updated_lines = []
        version_updated = False
        
        for line in lines:
            if line.strip().startswith('ACTIVE_ENCRYPTION_VERSION='):
                updated_lines.append(f'ACTIVE_ENCRYPTION_VERSION="{new_active_version}"\n')
                version_updated = True
            else:
                updated_lines.append(line)
        
        if not version_updated:
            current_app.logger.error("ACTIVE_ENCRYPTION_VERSION não encontrada no arquivo")
            return False
        
        # Atualizar timestamp no cabeçalho do arquivo
        updated_lines = _update_config_timestamp(updated_lines)
        
        # Escrever usando operação atômica
        write_result = _write_config_atomically(env_file, updated_lines)
        
        if not write_result.success:
            current_app.logger.error(f"Falha ao escrever arquivo: {write_result.error_message}")
            return False
        
        # Validar integridade
        if not validate_config_integrity(env_file):
            current_app.logger.error("Falha na validação de integridade após atualização")
            return False
        
        current_app.logger.info(f"Versão ativa atualizada para: {new_active_version}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar versão ativa: {e}")
        return False


def generate_operation_id() -> str:
    """Gera um ID único para operações de limpeza."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    random_suffix = secrets.token_hex(4)
    return f"cleanup_{timestamp}_{random_suffix}"


def log_operation_summary(operation: CleanupOperation):
    """Registra um resumo final da operação para auditoria."""
    duration = 0
    if operation.end_time and operation.start_time:
        duration = (operation.end_time - operation.start_time).total_seconds()
    
    summary = {
        'operation_id': operation.operation_id,
        'model_path': operation.model_path,
        'column_name': operation.column_name,
        'keep_versions': operation.keep_versions,
        'dry_run': operation.dry_run,
        'success': operation.success,
        'duration_seconds': duration,
        'total_records_analyzed': operation.total_records_analyzed,
        'versions_removed': len(operation.versions_to_remove),
        'lines_removed': operation.lines_removed,
        'rollback_performed': operation.rollback_performed,
        'backup_file': operation.backup_file
    }
    
    current_app.logger.info(f"[CLEANUP-SUMMARY] {summary}")


@click.group('secrets')
def secrets_cli():
    """Gerenciamento de chaves de criptografia."""
    pass



@secrets_cli.command('list')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_list(logfile):
    """Lista versões de chaves de criptografia disponíveis."""
    logfile_path = resolve_logfile_path(logfile)
    
    with log_to_file(logfile_path):
        sm: SecretsManager = current_app.extensions.get('secrets_manager')
        if not sm:
            raise click.ClickException("SecretsManager não inicializado")

        active_version = sm.get_active_version()
        all_versions = sm.get_all_versions()

        click.echo(f"Versao ativa: {active_version}")
        click.echo(f"\nVersoes disponiveis ({len(all_versions)}):")

        for version in sorted(all_versions):
            marker = " [ATIVA]" if version == active_version else ""
            click.echo(f"  - {version}{marker}")

        if len(all_versions) == 0:
            click.echo("  (nenhuma versao encontrada)")

        # Verificar possíveis locais do arquivo
        instance_path = Path(current_app.instance_path)
        crypto_file = instance_path / '.env.crypto'

        click.echo(f"\n[INFO] Configuracao carregada de:")
        if crypto_file.exists():
            click.echo(f"  - {crypto_file}")
        click.echo("  - Variaveis de ambiente")


@secrets_cli.command('generate')
@click.option('--env-file', default=None,
              help='Arquivo para salvar configuração (padrão: instance/.env.crypto)')
@click.option('--version', default='v1', show_default=True,
              help='Nome da versão inicial')
@click.option('--key-bytes', default=32, type=int, show_default=True,
              help='Tamanho da chave em bytes')
@click.option('--salt-bytes', default=16, type=int, show_default=True,
              help='Tamanho do salt em bytes')
@click.option('--yes', is_flag=True, help='Confirmar sem prompt')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_generate(env_file, version, key_bytes, salt_bytes, yes, logfile):
    """Gera configuração inicial de chaves e salt."""
    logfile_path = resolve_logfile_path(logfile)
    
    with log_to_file(logfile_path):
        # Usar instance/.env.crypto como padrão
        if env_file is None:
            instance_path = Path(current_app.instance_path)
            env_file = str(instance_path / '.env.crypto')

        # Criar diretório instance se não existir
        env_path = Path(env_file)
        env_dir = env_path.parent
        if env_dir and not env_dir.exists():
            env_dir.mkdir(parents=True, exist_ok=True)

        if env_path.exists() and not yes:
            if not click.confirm(f"Arquivo '{env_file}' existe. Sobrescrever?"):
                click.echo("Operação cancelada.")
                return

        # Gerar chave e salt
        key_raw = secrets.token_bytes(key_bytes)
        key_b64 = base64.urlsafe_b64encode(key_raw).decode('ascii')

        salt_raw = os.urandom(salt_bytes)
        salt_b64 = base64.urlsafe_b64encode(salt_raw).decode('ascii')
        salt_hash = hashlib.sha256(salt_raw).hexdigest()

        # Escrever arquivo
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(f"# Gerado em {datetime.now(timezone.utc).isoformat()}Z\n")
            f.write(f"# MANTENHA ESTE ARQUIVO SEGURO - NÃO VERSIONE EM GIT\n\n")
            f.write(f'ACTIVE_ENCRYPTION_VERSION="{version}"\n')
            f.write(f'ENCRYPTION_KEYS__{version}="{key_b64}"\n')
            f.write(f'ENCRYPTION_SALT__{version}="{salt_b64}"\n')
            f.write(f'ENCRYPTION_SALT_HASH__{version}="{salt_hash}"\n')

        # Proteger arquivo imediatamente
        env_path.chmod(0o600)

        click.echo(f"[OK] Configuracao gerada em: {env_file}")
        click.echo(f"[OK] Versao: {version}")
        click.echo(f"[OK] Permissoes definidas como 600")
        click.echo(f"\n[AVISO] PROXIMOS PASSOS:")
        click.echo(f"   1. Arquivo ja esta em .gitignore (instance/.env.crypto)")
        click.echo(f"   2. Faca backup: cp {env_file} {env_file}.backup")
        click.echo(f"   3. Em producao, mova para Vault/Secret Manager")


@secrets_cli.command('rotate')
@click.option('--env-file', default=None,
              help='Arquivo para salvar configuração (padrão: instance/.env.crypto)')
@click.option('--new-version', default=None,
              help='Nome da nova versão (auto se omitido)')
@click.option('--key-bytes', default=32, type=int, show_default=True)
@click.option('--persist/--no-persist', default=True, show_default=True,
              help='Persistir em arquivo')
@click.option('--dry-run', is_flag=True, help='Simular sem modificar')
@click.option('--yes', is_flag=True, help='Confirmar sem prompt')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_rotate(env_file, new_version, key_bytes, persist, dry_run, yes, logfile):
    """Rotaciona chave de criptografia (não recriptografa dados)."""
    logfile_path = resolve_logfile_path(logfile)
    
    with log_to_file(logfile_path):
        sm: SecretsManager = current_app.extensions.get('secrets_manager')
        if not sm:
            raise click.ClickException("SecretsManager não inicializado")

        # Usar instance/.env.crypto como padrão
        if env_file is None:
            instance_path = Path(current_app.instance_path)
            env_file = str(instance_path / '.env.crypto')

        # Determinar próxima versão
        if not new_version:
            existing = sm.get_all_versions()
            max_num = 0
            for v in existing:
                if v.startswith('v'):
                    try:
                        num = int(v[1:])
                        max_num = max(max_num, num)
                    except ValueError:
                        continue
            new_version = f"v{max_num + 1}"

        # Gerar nova chave
        new_key = base64.urlsafe_b64encode(secrets.token_bytes(key_bytes)).decode('ascii')

        click.echo(f"Nova versão: {new_version}")
        click.echo(f"Persistir: {'Sim' if persist else 'Não'}")
        click.echo(f"Dry-run: {'Sim' if dry_run else 'Não'}")

        if dry_run:
            click.echo("\n[DRY-RUN] Operação simulada - nenhuma mudança aplicada")
            return

        if not yes:
            if not click.confirm(f"Criar versão '{new_version}' e marcar como ativa?"):
                click.echo("Operação cancelada.")
                return

        # Executar rotação
        sm.rotate_to_new_version(
                new_version,
                new_key,
                persist_to_file=env_file if persist else None
        )

        click.echo(f"\n[OK] Nova versao '{new_version}' criada e ativada")
        if persist:
            click.echo(f"[OK] Arquivo '{env_file}' atualizado")
        click.echo(f"\n[AVISO] Proximos passos:")
        click.echo(f"   1. Execute 'flask secrets reencrypt' para atualizar dados existentes")
        click.echo(f"   2. Monitore o progresso da recriptografia")
        click.echo(f"   3. Apos conclusao, remova versoes antigas se desejar")


@secrets_cli.command('cleanup-jobs')
@click.option('--finished-older-than', default=7, type=int, show_default=True,
              help='Remove jobs finalizados a mais de N dias')
@click.option('--stalled-older-than', default=7, type=int, show_default=True,
              help='Remove jobs parados (running/pending) a mais de N dias')
@click.option('--dry-run', is_flag=True, help='Apenas mostra o que será feito')
@click.option('--yes', is_flag=True, help='Confirma as remoções')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_cleanup_jobs(finished_older_than, stalled_older_than, dry_run, yes, logfile):
    """
    Remove jobs antigos de re-criptografia para evitar crescimento excessivo do banco de dados.
    
    Este comando remove:
    1. Jobs finalizados (status='finished') mais antigos que o número especificado de dias
    2. Jobs travados (status in ['running', 'pending']) mais antigos que o número especificado de dias
    3. Jobs com falha mais antigos que o número especificado de dias (mesmo critério dos finalizados)
    
    Jobs com status 'paused' são preservados pois podem ser retomados.
    """
    logfile_path = resolve_logfile_path(logfile)
    
    with log_to_file(logfile_path):
        from datetime import datetime, timedelta
        from sqlalchemy import and_, or_
        
        db = current_app.extensions.get('sqlalchemy')
        if not db:
            raise click.ClickException("SQLAlchemy não inicializado")
        
        session = db.session
        
        # Calculate cutoff dates using UTC to match database timestamps
        from datetime import timezone
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)  # Remove tzinfo for comparison
        finished_cutoff = now_utc - timedelta(days=finished_older_than)
        stalled_cutoff = now_utc - timedelta(days=stalled_older_than)
        
        # Query for jobs to be deleted
        finished_jobs_query = session.query(ReencryptJob).filter(
            and_(
                ReencryptJob.status.in_(['finished', 'failed']),
                ReencryptJob.updated_at < finished_cutoff
            )
        )
        
        stalled_jobs_query = session.query(ReencryptJob).filter(
            and_(
                ReencryptJob.status.in_(['running', 'pending']),
                ReencryptJob.updated_at < stalled_cutoff
            )
        )
        
        # Count jobs to be deleted
        finished_count = finished_jobs_query.count()
        stalled_count = stalled_jobs_query.count()
        total_count = finished_count + stalled_count
        
        if total_count == 0:
            click.echo("Nenhum job encontrado para limpeza.")
            return
        
        # Show summary
        click.echo(f"Jobs encontrados para limpeza:")
        click.echo(f"  - Finished/Failed (>{finished_older_than} dias): {finished_count}")
        click.echo(f"  - Stalled (>{stalled_older_than} dias): {stalled_count}")
        click.echo(f"  - Total: {total_count}")
        
        if dry_run:
            click.echo("\n[DRY-RUN] Nenhum job será removido.")
            
            # Show details of what would be deleted
            if finished_count > 0:
                click.echo(f"\nJobs finished/failed que seriam removidos:")
                for job in finished_jobs_query.limit(10):
                    age_days = (now_utc - job.updated_at).days
                    click.echo(f"  ID {job.id}: {job.model_path}.{job.column_name} "
                              f"({job.status}, {age_days} dias)")
                if finished_count > 10:
                    click.echo(f"  ... e mais {finished_count - 10} jobs")
            
            if stalled_count > 0:
                click.echo(f"\nJobs stalled que seriam removidos:")
                for job in stalled_jobs_query.limit(10):
                    age_days = (now_utc - job.updated_at).days
                    click.echo(f"  ID {job.id}: {job.model_path}.{job.column_name} "
                              f"({job.status}, {age_days} dias)")
                if stalled_count > 10:
                    click.echo(f"  ... e mais {stalled_count - 10} jobs")
            return
        
        # Confirm deletion
        if not yes:
            if not click.confirm(f"\nRemover {total_count} jobs?"):
                click.echo("Operação cancelada.")
                return
        
        # Perform deletion
        try:
            deleted_finished = finished_jobs_query.delete(synchronize_session=False)
            deleted_stalled = stalled_jobs_query.delete(synchronize_session=False)
            session.commit()
            
            click.echo(f"\n[OK] Jobs removidos:")
            click.echo(f"  - Finished/Failed: {deleted_finished}")
            click.echo(f"  - Stalled: {deleted_stalled}")
            click.echo(f"  - Total: {deleted_finished + deleted_stalled}")
            
        except Exception as e:
            session.rollback()
            raise click.ClickException(f"Erro ao remover jobs: {e}")


@secrets_cli.command('list-jobs')
@click.option('--status', default=None, help='Filter by status (pending, running, finished, failed, paused)')
@click.option('--limit', default=20, type=int, show_default=True, help='Maximum number of jobs to show')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_list_jobs(status, limit, logfile):
    """Lista jobs de re-criptografia com seus status e progresso."""
    logfile_path = resolve_logfile_path(logfile)
    
    with log_to_file(logfile_path):
        db = current_app.extensions.get('sqlalchemy')
        if not db:
            raise click.ClickException("SQLAlchemy não inicializado")
        
        session = db.session
        
        # Build query
        query = session.query(ReencryptJob).order_by(ReencryptJob.created_at.desc())
        
        if status:
            query = query.filter(ReencryptJob.status == status)
        
        jobs = query.limit(limit).all()
        
        if not jobs:
            click.echo("Nenhum job encontrado.")
            return
        
        # Display jobs
        click.echo(f"{'ID':<4} {'Status':<10} {'Model.Column':<40} {'Progress':<15} {'Created':<12} {'Updated':<12}")
        click.echo("-" * 100)
        
        for job in jobs:
            model_column = f"{job.model_path.split('.')[-1]}.{job.column_name}"
            if len(model_column) > 38:
                model_column = model_column[:35] + "..."
            
            if job.total_records > 0:
                progress = f"{job.processed}/{job.total_records}"
                if job.skipped > 0:
                    progress += f" ({job.skipped} skip)"
            else:
                progress = "0/0"
            
            created = job.created_at.strftime("%Y-%m-%d") if job.created_at else "N/A"
            updated = job.updated_at.strftime("%Y-%m-%d") if job.updated_at else "N/A"
            
            click.echo(f"{job.id:<4} {job.status:<10} {model_column:<40} {progress:<15} {created:<12} {updated:<12}")
            
            if job.last_error and len(job.last_error) > 0:
                error_preview = job.last_error[:60] + "..." if len(job.last_error) > 60 else job.last_error
                click.echo(f"     Error: {error_preview}")


@secrets_cli.command('reencrypt')
@click.option('--model', required=True,
              help='Modelo a recriptografar (module:Class)')
@click.option('--column', required=True,
              help='Coluna a recriptografar')
@click.option('--batch-size', default=500, type=int, show_default=True)
@click.option('--commit-every', default=1000, type=int, show_default=True)
@click.option('--dry-run', is_flag=True)
@click.option('--resume', is_flag=True, help='Retomar job existente')
@click.option('--job-id', type=int, default=None)
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_reencrypt(model, column, batch_size, commit_every, dry_run, resume, job_id, logfile):
    """
    Recriptografa dados de uma coluna específica de um modelo com a versão ativa da chave de criptografia.

    Este comando processa registros em lotes, ignorando automaticamente aqueles que já estão na versão ativa.
    Suporta retomada de jobs interrompidos e modo dry-run para simulação.

    Args:
        model (str): Caminho do modelo no formato 'module:Class' (ex.: app.models.user:User).
        column (str): Nome da coluna a ser recriptografada.
        batch_size (int): Número de registros processados por lote. Padrão: 500.
        commit_every (int): Número de registros processados antes de um commit. Padrão: 1000.
        dry_run (bool): Se True, simula a operação sem persistir mudanças.
        resume (bool): Se True, retoma um job pendente existente.
        job_id (int, optional): ID do job específico a retomar. Se None, usa o mais recente pendente.

    Raises:
        click.ClickException: Se extensões necessárias não estiverem inicializadas ou se houver falhas no processamento.

    Examples:
        flask secrets reencrypt --model app.models.user:User --column encrypted_field
        flask secrets reencrypt --model app.models.user:User --column encrypted_field --dry-run
        flask secrets reencrypt --model app.models.user:User --column encrypted_field --resume
    """
    # from flask_sqlalchemy import SQLAlchemy
    db = current_app.extensions.get('sqlalchemy')
    if not db:
        raise click.ClickException("SQLAlchemy não inicializado")

    sm: SecretsManager = current_app.extensions.get('secrets_manager')
    if not sm:
        raise click.ClickException("SecretsManager não inicializado")

    session = db.session

    # Carregar modelo
    model_cls = load_model_from_path(model)
    pk_name = get_primary_key_name(model_cls)
    target_version = sm.get_active_version()

    # Criar ou recuperar job
    if job_id:
        job = session.query(ReencryptJob).get(job_id)
        if not job:
            raise click.ClickException(f"Job {job_id} não encontrado")
    elif resume:
        stmt = (select(ReencryptJob)
                .where(ReencryptJob.model_path == model)
                .where(ReencryptJob.column_name == column)
                .where(ReencryptJob.status.in_(['pending', 'running', 'paused']))
                .order_by(ReencryptJob.created_at.desc())
                )
        job = session.execute(stmt).scalars().first()
        if not job:
            click.echo("Nenhum job pendente encontrado. Criando novo...")
            job = None
    else:
        job = None

    if not job:
        # Criar novo job
        total = session.query(model_cls).count()
        job = ReencryptJob(
                model_path=model,
                column_name=column,
                pk_name=pk_name,
                target_version=target_version,
                total_records=total,
                status='pending',
                dry_run=dry_run
        )
        session.add(job)
        session.commit()
        session.refresh(job)

    click.echo(f"Job ID: {job.id}")
    click.echo(f"Alvo: {model}.{column}")
    click.echo(f"Versão alvo: {target_version}")
    click.echo(f"Total de registros: {job.total_records}")
    click.echo(f"Progresso: {job.processed}/{job.total_records} ({job.skipped} ignorados)")

    if dry_run:
        click.echo("\n[DRY-RUN] Modo simulação - nenhuma mudança será persistida")

    # Processar registros
    try:
        job.status = 'running'
        session.commit()

        processed_since_commit = 0
        start_after = job.last_pk

        with click.progressbar(
                length=job.total_records,
                label='Recriptografando',
                show_pos=True
        ) as bar:
            bar.update(job.processed)

            for batch in iter_records_in_batches(
                    session, model_cls, pk_name, start_after, batch_size
            ):
                for obj in batch:
                    pk_val = getattr(obj, pk_name)

                    # Verificar se precisa re-criptografar usando SecretsManager.decrypt()
                    # para descobrir qual versão foi usada na descriptografia
                    from app.models.custom_types import EncryptedString
                    
                    needs_reencryption = EncryptedString.check_needs_reencryption(
                        session, model_cls, obj, column, target_version
                    )
                    
                    if not needs_reencryption:
                        job.skipped += 1
                        job.processed += 1
                        job.last_pk = str(pk_val)
                        bar.update(1)
                        continue

                    # Obter o valor descriptografado para re-criptografar
                    current_val = getattr(obj, column)

                    # Recriptografar: setando o valor descriptografado de volta,
                    # o TypeDecorator vai criptografar com a versão ativa atual
                    if not dry_run:
                        try:
                            # Simplesmente definir o valor descriptografado de volta
                            # O EncryptedString vai criptografar com a versão ativa atual
                            setattr(obj, column, current_val)
                            # Forçar SQLAlchemy a detectar mudança no campo
                            flag_modified(obj, column)
                            processed_since_commit += 1
                        except Exception as e:
                            job.errors += 1
                            job.last_error = str(e)
                            current_app.logger.error(
                                    f"Erro ao recriptografar {pk_name}={pk_val}: {e}"
                            )
                    else:
                        # Em dry-run, ainda contamos como processado para estatísticas
                        processed_since_commit += 1

                    job.processed += 1
                    job.last_pk = pk_val.hex if hasattr(pk_val, 'hex') else str(pk_val)
                    bar.update(1)

                    # Commit periódico
                    if not dry_run and processed_since_commit >= commit_every:
                        session.commit()
                        processed_since_commit = 0
                        session.add(job)
                        session.commit()

                # Commit ao final de cada batch
                if not dry_run:
                    session.commit()
                else:
                    session.rollback()

                session.add(job)
                session.commit()

        # Finalizar
        job.status = 'finished'
        session.commit()

        click.echo(f"\n[OK] Recriptografia concluida!")
        click.echo(f"  Processados: {job.processed}")
        click.echo(f"  Ignorados (ja atualizados): {job.skipped}")
        click.echo(f"  Erros: {job.errors}")

    except Exception as e:
        job.status = 'failed'
        job.last_error = str(e)
        session.commit()
        raise click.ClickException(f"Falha na recriptografia: {e}")


@secrets_cli.command('backup-config')
@click.option('--env-file', default=None,
              help='Arquivo de configuração para backup (padrão: instance/.env.crypto)')
@click.option('--cleanup-old', is_flag=True,
              help='Limpar backups antigos após criar novo')
@click.option('--keep-backups', default=5, type=int, show_default=True,
              help='Número de backups a manter ao limpar')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_backup_config(env_file, cleanup_old, keep_backups, logfile):
    """Cria backup do arquivo de configuração de chaves."""
    
    # Usar instance/.env.crypto como padrão
    if env_file is None:
        instance_path = Path(current_app.instance_path)
        env_file = str(instance_path / '.env.crypto')
    
    click.echo(f"Criando backup de: {env_file}")
    
    # Criar backup
    backup_result = backup_configuration(env_file)
    
    if not backup_result.success:
        raise click.ClickException(f"Falha ao criar backup: {backup_result.error_message}")
    
    click.echo(f"[OK] Backup criado: {backup_result.backup_file}")
    
    # Validar integridade do backup
    if validate_backup_integrity(backup_result.backup_file, env_file):
        click.echo("[OK] Integridade do backup validada")
    else:
        click.echo("[AVISO] Falha na validação da integridade do backup")
    
    # Limpar backups antigos se solicitado
    if cleanup_old:
        removed_count = cleanup_old_backups(env_file, keep_backups)
        if removed_count > 0:
            click.echo(f"[OK] Removidos {removed_count} backups antigos")
        else:
            click.echo("[INFO] Nenhum backup antigo para remover")


@secrets_cli.command('restore-config')
@click.option('--backup-file', required=True,
              help='Arquivo de backup para restaurar')
@click.option('--env-file', default=None,
              help='Arquivo de configuração de destino (padrão: instance/.env.crypto)')
@click.option('--yes', is_flag=True, help='Confirmar sem prompt')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_restore_config(backup_file, env_file, yes, logfile):
    """Restaura configuração a partir de um backup."""
    
    # Usar instance/.env.crypto como padrão
    if env_file is None:
        instance_path = Path(current_app.instance_path)
        env_file = str(instance_path / '.env.crypto')
    
    click.echo(f"Restaurando de: {backup_file}")
    click.echo(f"Para: {env_file}")
    
    # Validar integridade do backup antes de restaurar
    if not validate_backup_integrity(backup_file, env_file):
        raise click.ClickException("Backup falhou na validação de integridade")
    
    click.echo("[OK] Integridade do backup validada")
    
    # Confirmar operação
    if not yes:
        if not click.confirm("Esta operação irá sobrescrever o arquivo de configuração atual. Continuar?"):
            click.echo("Operação cancelada.")
            return
    
    # Executar restauração
    if restore_configuration(backup_file, env_file):
        click.echo("[OK] Configuração restaurada com sucesso")
    else:
        raise click.ClickException("Falha ao restaurar configuração")


@secrets_cli.command('remove-versions')
@click.option('--versions', required=True,
              help='Versões a remover (separadas por vírgula, ex: v1,v2)')
@click.option('--env-file', default=None,
              help='Arquivo de configuração (padrão: instance/.env.crypto)')
@click.option('--dry-run', is_flag=True, help='Simular sem modificar')
@click.option('--yes', is_flag=True, help='Confirmar sem prompt')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_remove_versions(versions, env_file, dry_run, yes, logfile):
    """Remove versões específicas do arquivo de configuração (comando de teste)."""
    
    # Usar instance/.env.crypto como padrão
    if env_file is None:
        instance_path = Path(current_app.instance_path)
        env_file = str(instance_path / '.env.crypto')
    
    # Parsear versões
    versions_to_remove = [v.strip() for v in versions.split(',') if v.strip()]
    
    if not versions_to_remove:
        raise click.ClickException("Nenhuma versão especificada")
    
    click.echo(f"Arquivo de configuração: {env_file}")
    click.echo(f"Versões a remover: {versions_to_remove}")
    click.echo(f"Dry-run: {'Sim' if dry_run else 'Não'}")
    
    # Verificar versões existentes
    existing_versions = get_config_versions(env_file)
    active_version = get_active_version_from_config(env_file)
    
    click.echo(f"\nVersões existentes: {existing_versions}")
    click.echo(f"Versão ativa: {active_version}")
    
    # Validar versões a remover
    invalid_versions = [v for v in versions_to_remove if v not in existing_versions]
    if invalid_versions:
        raise click.ClickException(f"Versões não encontradas: {invalid_versions}")
    
    # Verificar se versão ativa seria removida
    if active_version in versions_to_remove:
        raise click.ClickException(f"Não é possível remover a versão ativa: {active_version}")
    
    if dry_run:
        click.echo("\n[DRY-RUN] Simulação - nenhuma modificação será feita")
        
        # Simular remoção para mostrar o que seria removido
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        lines_to_remove = []
        for line in lines:
            for version in versions_to_remove:
                if _line_contains_version_config(line, version):
                    lines_to_remove.append(line.strip())
                    break
        
        if lines_to_remove:
            click.echo(f"\nLinhas que seriam removidas ({len(lines_to_remove)}):")
            for line in lines_to_remove:
                click.echo(f"  - {line}")
        else:
            click.echo("\nNenhuma linha seria removida")
        
        return
    
    # Confirmar operação
    if not yes:
        if not click.confirm(f"\nRemover {len(versions_to_remove)} versões do arquivo de configuração?"):
            click.echo("Operação cancelada.")
            return
    
    # Criar backup antes da modificação
    click.echo("\nCriando backup...")
    backup_result = backup_configuration(env_file)
    
    if not backup_result.success:
        raise click.ClickException(f"Falha ao criar backup: {backup_result.error_message}")
    
    click.echo(f"[OK] Backup criado: {backup_result.backup_file}")
    
    # Executar remoção
    click.echo("Removendo versões...")
    modification_result = remove_versions_from_config(env_file, versions_to_remove)
    
    if not modification_result.success:
        click.echo(f"[ERRO] Falha na remoção: {modification_result.error_message}")
        
        # Tentar restaurar backup
        if backup_result.backup_file:
            click.echo("Tentando restaurar backup...")
            if restore_configuration(backup_result.backup_file, env_file):
                click.echo("[OK] Backup restaurado")
            else:
                click.echo("[ERRO] Falha ao restaurar backup")
        
        raise click.ClickException("Operação falhou")
    
    # Mostrar resultado
    click.echo(f"\n[OK] Remoção concluída:")
    click.echo(f"  - Linhas removidas: {modification_result.lines_removed}")
    click.echo(f"  - Versões removidas: {modification_result.versions_removed}")
    click.echo(f"  - Backup disponível: {backup_result.backup_file}")
    
    # Validar integridade final
    if validate_config_integrity(env_file):
        click.echo("[OK] Integridade do arquivo validada")
    else:
        click.echo("[AVISO] Falha na validação de integridade")


@secrets_cli.command('cleanup-keys')
@click.option('--model', required=True, 
              help='Modelo a analisar no formato module:Class (ex: app.models.user:User)')
@click.option('--column', required=True,
              help='Nome da coluna criptografada a analisar')
@click.option('--keep-versions', default=3, type=int, show_default=True,
              help='Número de versões mais recentes a manter')
@click.option('--env-file', default=None,
              help='Arquivo de configuração (padrão: instance/.env.crypto)')
@click.option('--dry-run', is_flag=True,
              help='Simular operação sem fazer modificações')
@click.option('--yes', is_flag=True,
              help='Confirmar operação sem prompt interativo')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_cleanup_keys(model, column, keep_versions, env_file, dry_run, yes, logfile):
    """
    Limpa versões antigas de chaves criptográficas mantendo apenas as mais recentes.
    
    Este comando analisa os dados criptografados de um modelo/coluna específicos
    para identificar quais versões de chaves estão em uso, permitindo a remoção
    segura de versões não utilizadas.
    
    Exemplos:
    
    \b
    # Simular limpeza mantendo 3 versões
    flask secrets cleanup-keys --model app.models.user:User --column encrypted_field --dry-run
    
    \b
    # Executar limpeza mantendo 5 versões
    flask secrets cleanup-keys --model app.models.user:User --column encrypted_field --keep-versions 5 --yes
    
    Requirements: 3.3, 3.4, 6.2, 6.3, 6.4
    """
    # Definir arquivo de configuração padrão
    if env_file is None:
        instance_path = Path(current_app.instance_path)
        env_file = str(instance_path / '.env.crypto')
    
    # Criar operação de limpeza com ID único
    operation = CleanupOperation(
        operation_id=generate_operation_id(),
        start_time=datetime.now(timezone.utc),
        model_path=model,
        column_name=column,
        keep_versions=keep_versions,
        env_file=env_file,
        dry_run=dry_run,
        user_confirmed=yes
    )
    
    # Criar reporter de progresso
    reporter = ProgressReporter(operation)
    reporter.display_operation_header()
    
    try:
        # Executar operação usando o orquestrador
        orchestrator = CleanupOrchestrator(operation)
        completed_operation = orchestrator.execute()
        
        # Exibir resultados da análise
        reporter.display_analysis_results()
        
        # Calcular e exibir estatísticas de uso
        if completed_operation.total_records_analyzed > 0:
            # Recalcular estatísticas para exibição
            version_counts = {}
            for version in completed_operation.versions_in_use:
                # Para exibição, assumir contagem igual (seria melhor armazenar os dados reais)
                version_counts[version] = 1
            
            usage_stats = calculate_usage_statistics(version_counts, completed_operation.active_version)
            reporter.display_usage_statistics(usage_stats)
        
        # Exibir resultados do planejamento
        has_versions_to_remove = reporter.display_planning_results()
        
        if not has_versions_to_remove:
            return
        
        # Executar fase específica baseada no modo
        if completed_operation.dry_run:
            reporter.display_dry_run_simulation()
        else:
            # Confirmação do usuário se necessário
            if not yes:
                if not reporter.display_confirmation_prompt():
                    click.echo("Operação cancelada pelo usuário.")
                    return
                completed_operation.user_confirmed = True
            
            # Exibir progresso da execução
            reporter.display_execution_progress()
            
            # Obter estado final para exibição
            sm: SecretsManager = current_app.extensions.get('secrets_manager')
            final_versions = sm.get_all_versions() if sm else []
            final_active = sm.get_active_version() if sm else ""
            
            reporter.display_success_results(final_versions, final_active)
        
        # Log resumo final da operação
        log_operation_summary(completed_operation)
    
    except CleanupError as e:
        # Erro específico de limpeza - exibir detalhes formatados
        reporter.display_error_results(e)
        raise click.ClickException(str(e))
    
    except click.ClickException:
        # Re-raise click exceptions para manter formatação
        raise
    
    except Exception as e:
        # Capturar outros erros inesperados
        current_app.logger.error(f"Erro inesperado no comando cleanup-keys: {e}")
        if current_app.debug:
            current_app.logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        
        # Criar operação de erro para logging
        operation.success = False
        operation.error_message = str(e)
        operation.end_time = datetime.now(timezone.utc)
        
        error = CleanupError(f"Erro inesperado: {e}", operation, e)
        reporter.display_error_results(error)
        
        # Log resumo da operação com erro
        log_operation_summary(operation)
        
        raise click.ClickException(f"Erro inesperado: {e}")


@secrets_cli.command('validate-config')
@click.option('--env-file', default=None,
              help='Arquivo de configuração (padrão: instance/.env.crypto)')
@click.option('--logfile', default=None,
              help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
@with_appcontext
def cmd_validate_config(env_file, logfile):
    """Valida a integridade do arquivo de configuração."""
    logfile_path = resolve_logfile_path(logfile)
    
    with log_to_file(logfile_path):
        # Usar instance/.env.crypto como padrão
        if env_file is None:
            instance_path = Path(current_app.instance_path)
            env_file = str(instance_path / '.env.crypto')
        
        click.echo(f"Validando: {env_file}")

        env_path = Path(env_file)
        if not env_path.exists():
            raise click.ClickException(f"Arquivo não encontrado: {env_file}")
        
        # Executar validação
        is_valid = validate_config_integrity(env_file)
        
        if is_valid:
            click.echo("[OK] Arquivo de configuração é válido")
            
            # Mostrar informações adicionais
            versions = get_config_versions(env_file)
            active_version = get_active_version_from_config(env_file)
            
            click.echo(f"\nInformações do arquivo:")
            click.echo(f"  - Versões encontradas: {versions}")
            click.echo(f"  - Versão ativa: {active_version}")
            click.echo(f"  - Total de versões: {len(versions)}")
            
        else:
            raise click.ClickException("Arquivo de configuração é inválido")


# @secrets_cli.command('cleanup-stats')
# @click.option('--days', default=30, type=int, show_default=True,
#               help='Mostrar estatísticas dos últimos N dias')
# @click.option('--operation-id', default=None,
#               help='Mostrar detalhes de uma operação específica')
# @click.option('--logfile', default=None,
#               help='Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)')
# @with_appcontext
# def cmd_cleanup_stats(days, operation_id, logfile):
#     """
#     Exibe estatísticas e logs de operações de limpeza de chaves.
    
#     Este comando permite visualizar o histórico de operações de limpeza,
#     incluindo sucessos, falhas, e estatísticas de uso.
#     """
#     logfile_path = resolve_logfile_path(logfile)
    
#     with log_to_file(logfile_path):
#         if operation_id:
#             # Mostrar detalhes de uma operação específica
#             click.echo(f"Buscando detalhes da operação: {operation_id}")
            
#             # Buscar nos logs da aplicação
#             try:
#                 # Esta é uma implementação simplificada - em produção seria melhor
#                 # usar um sistema de logging estruturado como ELK stack
#                 click.echo(f"[INFO] Para detalhes completos, consulte os logs da aplicação")
#                 click.echo(f"[INFO] Procure por: [CLEANUP-AUDIT] ID: {operation_id}")
                
#             except Exception as e:
#                 click.echo(f"[ERRO] Não foi possível recuperar detalhes: {e}")
        
#         else:
#             # Mostrar estatísticas gerais
#             click.echo(f"Estatísticas de limpeza de chaves (últimos {days} dias)")
#             click.echo("=" * 50)
            
#             # Esta é uma implementação básica - em produção seria melhor
#             # armazenar estatísticas em banco de dados
#             click.echo("[INFO] Para estatísticas detalhadas, consulte os logs da aplicação")
#             click.echo("[INFO] Procure por: [CLEANUP-SUMMARY] e [CLEANUP-AUDIT]")
            
#             # Mostrar comandos úteis para análise de logs
#             click.echo(f"\nComandos úteis para análise:")
#             click.echo(f"  # Ver operações recentes:")
#             click.echo(f"  grep 'CLEANUP-SUMMARY' logs/app.log | tail -10")
#             click.echo(f"  ")
#             click.echo(f"  # Ver erros de limpeza:")
#             click.echo(f"  grep 'CLEANUP-AUDIT.*Erro' logs/app.log")
#             click.echo(f"  ")
#             click.echo(f"  # Ver rollbacks:")
#             click.echo(f"  grep 'CLEANUP-AUDIT.*Rollback' logs/app.log")

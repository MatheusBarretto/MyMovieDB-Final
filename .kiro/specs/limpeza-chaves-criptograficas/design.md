# Design Document

## Overview

O comando de limpeza de chaves criptográficas será implementado como um novo comando CLI no módulo `secrets_cli.py`, seguindo o padrão dos comandos existentes. A funcionalidade analisará os dados criptografados de um modelo/coluna específicos para determinar quais versões de chaves estão em uso, permitindo a remoção segura de versões não utilizadas.

O design aproveita a infraestrutura existente do `SecretsManager` e `EncryptedString` para detectar versões de chaves em uso, garantindo que apenas versões realmente não utilizadas sejam removidas.

## Architecture

### Command Structure
```
flask secrets cleanup-keys --model app.models.user:User --column encrypted_field [options]
```

### Core Components

1. **CLI Command Handler** (`cmd_cleanup_keys`)
   - Validação de parâmetros de entrada
   - Orquestração do processo de limpeza
   - Interface com usuário (confirmações, dry-run, progress)

2. **Key Usage Analyzer** 
   - Análise de dados criptografados para detectar versões em uso
   - Utiliza `EncryptedString.check_needs_reencryption` como base
   - Processa dados em batches para eficiência

3. **Key Cleanup Manager**
   - Identificação de versões candidatas para remoção
   - Backup de configurações antes da remoção
   - Remoção segura de chaves dos arquivos de configuração

4. **Safety Validator**
   - Verificação de versão ativa
   - Validação de número mínimo de versões
   - Verificação de integridade antes e após operações

## Components and Interfaces

### 1. CLI Command Interface

```python
@secrets_cli.command('cleanup-keys')
@click.option('--model', required=True, help='Modelo a analisar (module:Class)')
@click.option('--column', required=True, help='Coluna criptografada a analisar')
@click.option('--keep-versions', default=3, type=int, help='Número de versões a manter')
@click.option('--env-file', default=None, help='Arquivo de configuração')
@click.option('--dry-run', is_flag=True, help='Simular sem modificar')
@click.option('--yes', is_flag=True, help='Confirmar sem prompt')
@with_appcontext
def cmd_cleanup_keys(model, column, keep_versions, env_file, dry_run, yes):
```

### 2. Key Usage Analysis

```python
def analyze_key_usage(session, model_cls, column_name, batch_size=1000):
    """
    Analisa dados criptografados para identificar versões de chaves em uso.
    
    Returns:
        Dict[str, int]: Mapeamento de versão -> quantidade de registros
    """
```

### 3. Key Cleanup Logic

```python
def identify_removable_versions(all_versions, used_versions, active_version, keep_count):
    """
    Identifica quais versões podem ser removidas com segurança.
    
    Returns:
        Tuple[List[str], List[str]]: (versions_to_keep, versions_to_remove)
    """
```

### 4. Configuration Management

```python
def backup_configuration(env_file):
    """Cria backup do arquivo de configuração."""
    
def remove_versions_from_config(env_file, versions_to_remove):
    """Remove versões específicas do arquivo de configuração."""
    
def restore_configuration(backup_file, original_file):
    """Restaura configuração em caso de erro."""
```

## Data Models

### Key Usage Statistics
```python
@dataclass
class KeyUsageStats:
    version: str
    record_count: int
    percentage: float
    is_active: bool
    is_removable: bool
```

### Cleanup Operation Result
```python
@dataclass
class CleanupResult:
    total_versions_before: int
    total_versions_after: int
    versions_removed: List[str]
    versions_kept: List[str]
    backup_file: Optional[str]
    operation_time: datetime
```

## Error Handling

### Validation Errors
- **Invalid Model/Column**: Verificação de existência do modelo e coluna
- **Insufficient Versions**: Erro se `keep_versions < 1`
- **Active Version Removal**: Erro se versão ativa seria removida
- **Configuration File Issues**: Problemas de acesso/permissão

### Runtime Errors
- **Database Connection**: Falhas na análise de dados
- **Backup Creation**: Problemas ao criar backup
- **Configuration Update**: Falhas na atualização do arquivo
- **Rollback**: Restauração automática em caso de erro

### Error Recovery
```python
try:
    # Operação de limpeza
    perform_cleanup()
except Exception as e:
    # Restaurar backup se existir
    if backup_file and os.path.exists(backup_file):
        restore_configuration(backup_file, env_file)
    raise CleanupError(f"Falha na limpeza: {e}")
```

## Testing Strategy

### Unit Tests
- Validação de parâmetros de entrada
- Lógica de identificação de versões removíveis
- Funções de backup e restauração
- Análise de uso de chaves (mocked)

### Integration Tests
- Teste completo com dados reais em banco de teste
- Verificação de integridade após limpeza
- Teste de rollback em cenários de erro
- Validação de arquivos de configuração

### Test Data Setup
```python
def setup_test_encryption_data():
    """Cria dados de teste com múltiplas versões de chaves."""
    # Criar registros com v1, v2, v3
    # Alguns registros órfãos com versões antigas
    # Versão ativa = v3
```

### Safety Tests
- Tentativa de remoção de versão ativa (deve falhar)
- Tentativa de manter 0 versões (deve falhar)
- Verificação de preservação de versões em uso
- Teste de dry-run (nenhuma modificação)

## Implementation Flow

### Phase 1: Analysis
1. Validar parâmetros de entrada
2. Carregar modelo e verificar coluna
3. Obter todas as versões disponíveis
4. Analisar dados em batches para identificar versões em uso
5. Calcular estatísticas de uso

### Phase 2: Planning
1. Identificar versão ativa
2. Determinar versões candidatas para remoção
3. Aplicar regras de segurança (manter ativa, manter mínimo)
4. Gerar plano de limpeza

### Phase 3: Execution (se não dry-run)
1. Criar backup da configuração
2. Solicitar confirmação do usuário (se não --yes)
3. Remover versões do arquivo de configuração
4. Verificar integridade pós-operação
5. Limpar caches do SecretsManager

### Phase 4: Reporting
1. Exibir estatísticas da operação
2. Informar localização do backup
3. Sugerir próximos passos se necessário

## Security Considerations

### Data Protection
- Backup automático antes de qualquer modificação
- Verificação de integridade antes e após operações
- Logs detalhados de todas as operações

### Access Control
- Comando requer contexto de aplicação Flask
- Verificação de permissões de arquivo
- Proteção contra remoção acidental de versão ativa

### Audit Trail
- Log de todas as versões removidas
- Timestamp de operações
- Identificação do usuário/processo que executou

## Performance Considerations

### Batch Processing
- Análise de dados em lotes para evitar sobrecarga de memória
- Processamento incremental com progress bar
- Otimização de queries para grandes volumes

### Caching
- Limpeza de caches do SecretsManager após operações
- Cache de resultados de análise durante operação
- Evitar recarregamento desnecessário de configurações

### Resource Management
- Controle de memória durante análise de grandes datasets
- Conexões de banco otimizadas
- Cleanup de recursos temporários
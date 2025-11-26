# Sistema de Criptografia e Gerenciamento de Chaves

Este documento descreve o sistema de criptografia de dados sensíveis da aplicação, incluindo o
processo de configuração inicial, rotação de chaves e boas práticas de segurança.

## Índice

1. [Visão Geral](#visão-geral)
2. [Configuração Inicial](#configuração-inicial)
3. [Rotação de Chaves](#rotação-de-chaves)
4. [Comandos CLI Disponíveis](#comandos-cli-disponíveis)
5. [Benefícios e Integração dos Logs](#benefícios-e-integração-dos-logs)
6. [Uso em Código Python](#uso-em-código-python)
7. [Boas Práticas de Segurança](#boas-práticas-de-segurança)
8. [Resolução de Problemas](#resolução-de-problemas)
9. [Arquitetura Interna](#arquitetura-interna)
10. [Referências](#referências)

## Visão Geral

A aplicação implementa um sistema robusto de criptografia para proteger dados sensíveis armazenados
no banco de dados, como:

- Segredos OTP (autenticação de dois fatores)
- Tokens de API
- Outros dados confidenciais

### Características Principais

- **Criptografia Transparente**: Os dados são automaticamente criptografados ao serem salvos e
  descriptografados ao serem lidos
- **Rotação de Chaves**: Suporte para múltiplas versões de chaves, permitindo rotação sem
  interrupção do serviço
- **Versionamento**: Cada registro mantém a informação de qual versão de chave foi usada para
  criptografá-lo
- **CLI Integrada**: Comandos Flask para gerenciar todo o ciclo de vida das chaves

### Componentes Técnicos

- **EncryptedString**: Tipo SQLAlchemy personalizado que criptografa/descriptografa automaticamente
- **SecretsManager**: Gerenciador centralizado de chaves com suporte a múltiplas versões
- **Fernet**: Algoritmo de criptografia simétrica (AES-128 em modo CBC)

## Configuração Inicial

### 1. Gerar Chaves de Criptografia

Execute o comando para gerar a configuração inicial:

```bash
flask secrets generate
```

Este comando irá:

- Gerar uma chave de criptografia aleatória (32 bytes por padrão)
- Gerar um salt aleatório (16 bytes por padrão)
- Criar o arquivo `.env.crypto` com as configurações
- Definir permissões restritivas (600) no arquivo

**Saída esperada:**

```
[OK] Configuracao gerada em: .env.crypto
[OK] Versao: v1
[OK] Permissoes definidas como 600

[AVISO] PROXIMOS PASSOS:
   1. Adicione ao .gitignore: echo '.env.crypto' >> .gitignore
   2. Faca backup: cp .env.crypto .env.crypto.backup
   3. Em producao, mova para Vault/Secret Manager
```

### 2. Proteger o Arquivo de Chaves

**IMPORTANTE**: O arquivo `.env.crypto` contém informações extremamente sensíveis e **NUNCA** deve
ser versionado no Git.

```bash
# Adicionar ao .gitignore
echo '.env.crypto' >> .gitignore
echo '.env.crypto.backup' >> .gitignore

# Fazer backup seguro
cp .env.crypto .env.crypto.backup
```

### 3. Estrutura do Arquivo `.env.crypto`

```bash
# Gerado em 2025-01-14T12:34:56Z
# MANTENHA ESTE ARQUIVO SEGURO - NÃO VERSIONE EM GIT

ACTIVE_ENCRYPTION_VERSION="v1"
ENCRYPTION_KEYS__v1="a1b2c3d4e5f6..."
ENCRYPTION_SALT__v1="x9y8z7w6v5u4..."
ENCRYPTION_SALT_HASH__v1="abc123def456..."
```

**Campos:**

- `ACTIVE_ENCRYPTION_VERSION`: Versão ativa usada para novos dados
- `ENCRYPTION_KEYS__<versão>`: Chave de criptografia em base64
- `ENCRYPTION_SALT__<versão>`: Salt para derivação de chave em base64
- `ENCRYPTION_SALT_HASH__<versão>`: Hash SHA-256 do salt (para validação de integridade)

### 4. Verificar Configuração

Liste as versões de chaves disponíveis:

```bash
flask secrets list
```

**Saída esperada:**

```
Versao ativa: v1

Versoes disponiveis (1):
  - v1 [ATIVA]

[INFO] Configuracao carregada de:
  - .env.crypto
  - Variaveis de ambiente
```

## Rotação de Chaves

A rotação de chaves deve ser realizada periodicamente por motivos de segurança ou em caso de
suspeita de comprometimento.

### Processo Completo de Rotação

#### Passo 1: Criar Nova Versão de Chave

```bash
flask secrets rotate
```

O comando irá:

- Detectar a versão mais recente (ex: v1)
- Gerar automaticamente a próxima versão (ex: v2)
- Criar nova chave e salt aleatórios
- Atualizar o arquivo `.env.crypto`
- Marcar a nova versão como ativa

**Saída esperada:**

```
Nova versão: v2
Persistir: Sim
Dry-run: Não
Criar versão 'v2' e marcar como ativa? [y/N]: y

[OK] Nova versao 'v2' criada e ativada
[OK] Arquivo '.env.crypto' atualizado

[AVISO] Proximos passos:
   1. Execute 'flask secrets reencrypt' para atualizar dados existentes
   2. Monitore o progresso da recriptografia
   3. Apos conclusao, remova versoes antigas se desejar
```

#### Passo 2: Verificar Novas Chaves

```bash
flask secrets list
```

**Saída esperada:**

```
Versao ativa: v2

Versoes disponiveis (2):
  - v1
  - v2 [ATIVA]
```

#### Passo 3: Re-criptografar Dados Existentes

**IMPORTANTE**: Use o **nome da coluna do banco de dados** (ex: `_otp_secret`), não o nome da
propriedade Python.

```bash
flask secrets reencrypt --model app.models.autenticacao:User --column _otp_secret
```

O comando irá:

- Ler cada registro com a chave antiga (v1)
- Descriptografar usando a chave v1
- Re-criptografar usando a chave ativa (v2)
- Atualizar o registro no banco de dados
- Exibir progresso em tempo real

**Saída esperada:**

```
Job ID: 1
Alvo: app.models.autenticacao:User._otp_secret
Versão alvo: v2
Total de registros: 150
Progresso: 0/150 (0 ignorados)
Recriptografando  [####################################]  150/150

[OK] Recriptografia concluida!
  Processados: 150
  Ignorados (ja atualizados): 0
  Erros: 0
```

#### Passo 4: Validar Re-criptografia

Verifique se todos os dados estão usando a nova versão:

```bash
# Via Flask shell
flask shell
>>> from app.models.autenticacao import User
>>> from sqlalchemy import text
>>> result = db.session.execute(text("SELECT _otp_secret FROM usuarios WHERE _otp_secret IS NOT NULL LIMIT 5"))
>>> for row in result:
...     print(row[0][:10])  # Deve mostrar "v2:..." para todos
```

#### Passo 5: Remover Chaves Antigas (Opcional)

**ATENÇÃO**: Só remova chaves antigas **APÓS** confirmar que todos os dados foram re-criptografados
com sucesso.

Edite `.env.crypto` e remova as linhas das versões antigas:

```bash
# Remover estas linhas:
# ENCRYPTION_KEYS__v1="..."
# ENCRYPTION_SALT__v1="..."
# ENCRYPTION_SALT_HASH__v1="..."
```

Mantenha um backup antes de remover:

```bash
cp .env.crypto .env.crypto.backup-$(date +%Y%m%d)
```

## Comandos CLI Disponíveis

Todos os comandos CLI de secrets agora suportam a opção `--logfile` para redirecionar logs e saídas para um arquivo.

### Opção `--logfile` (Disponível em Todos os Comandos)

**Uso Básico:**

```bash
# Comportamento padrão (sem arquivo de log)
flask secrets list

# Auto-gerar arquivo de log com timestamp
flask secrets list --logfile ""

# Usar arquivo de log específico
flask secrets list --logfile "minha_operacao.log"
```

**Nomes de Arquivo Auto-gerados:**

Quando usar `--logfile ""` (string vazia), o sistema gera automaticamente um nome de arquivo no formato:

```
secrets_AAAAMMDD_HHMMSS.log
```

Exemplo: `secrets_20241015_143022.log`

**O que é Registrado:**

Quando usar `--logfile`, as seguintes informações são capturadas:

1. **Saída do Console**: Todas as mensagens click.echo() e saída dos comandos
2. **Logs da Aplicação**: Mensagens do logger Flask com timestamps
3. **Mensagens de Erro**: Detalhes de exceções e stack traces
4. **Trilha de Auditoria**: Rastreamento detalhado de operações para comandos de limpeza

**Formato do Log:**

O arquivo de log contém:

- Timestamp para cada entrada de log
- Nível do log (INFO, WARNING, ERROR, etc.)
- Nome do logger
- Conteúdo detalhado da mensagem

Exemplo de entrada de log:

```
2024-10-15 14:30:22,123 - app.cli.secrets_cli - INFO - [CLEANUP-AUDIT] Operação iniciada - ID: cleanup_20241015_143022_a1b2
```

### `flask secrets generate`

Gera configuração inicial de chaves de criptografia.

**Opções:**

- `--env-file` (padrão: `.env.crypto`): Arquivo de destino
- `--version` (padrão: `v1`): Nome da versão inicial
- `--key-bytes` (padrão: `32`): Tamanho da chave em bytes
- `--salt-bytes` (padrão: `16`): Tamanho do salt em bytes
- `--yes`: Confirmar automaticamente (sem prompt)
- `--logfile`: Arquivo para salvar logs (padrão: sem arquivo, vazio para auto-gerar)

**Exemplos:**

```bash
# Geração básica
flask secrets generate --version v1 --key-bytes 32

# Com log detalhado
flask secrets generate --logfile "geracao_chaves.log"
```

### `flask secrets list`

Lista todas as versões de chaves disponíveis e mostra qual está ativa.

**Opções:**

- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Listagem básica
flask secrets list

# Com log
flask secrets list --logfile "lista_chaves.log"
```

### `flask secrets rotate`

Cria uma nova versão de chave e a marca como ativa.

**Opções:**

- `--env-file` (padrão: `.env.crypto`): Arquivo a atualizar
- `--new-version`: Nome da nova versão (auto-incrementa se omitido)
- `--key-bytes` (padrão: `32`): Tamanho da nova chave
- `--persist/--no-persist` (padrão: `True`): Salvar no arquivo
- `--dry-run`: Simular sem modificar
- `--yes`: Confirmar automaticamente
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Rotação automática (v1 → v2, v2 → v3, etc.)
flask secrets rotate

# Rotação com nome específico e log
flask secrets rotate --new-version v2-prod --logfile "rotacao_$(date +%Y%m%d).log"

# Simulação (não persiste mudanças)
flask secrets rotate --dry-run --logfile ""
```

### `flask secrets reencrypt`

Re-criptografa dados existentes com a versão ativa de chave.

**Opções:**

- `--model` (obrigatório): Caminho do modelo (formato: `module:Class`)
- `--column` (obrigatório): Nome da coluna no banco de dados
- `--batch-size` (padrão: `500`): Registros por lote
- `--commit-every` (padrão: `1000`): Frequência de commits
- `--dry-run`: Simular sem modificar dados
- `--resume`: Retomar job interrompido
- `--job-id`: ID de job específico para retomar
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Re-criptografia padrão
flask secrets reencrypt --model app.models.autenticacao:User --column _otp_secret

# Com log detalhado
flask secrets reencrypt --model app.models.autenticacao:User --column _otp_secret --logfile "recriptografia.log"

# Simulação (não persiste mudanças)
flask secrets reencrypt --model app.models.autenticacao:User --column _otp_secret --dry-run --logfile ""

# Retomar job interrompido
flask secrets reencrypt --model app.models.autenticacao:User --column _otp_secret --resume --logfile "retomada.log"
```

### `flask secrets cleanup-jobs`

Remove jobs antigos de re-criptografia para evitar crescimento excessivo do banco de dados.

**Opções:**

- `--finished-older-than` (padrão: `7`): Remove jobs finalizados a mais de N dias
- `--stalled-older-than` (padrão: `7`): Remove jobs parados (running/pending) a mais de N dias
- `--dry-run`: Apenas mostra o que será feito
- `--yes`: Confirma as remoções
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Limpeza padrão (7 dias)
flask secrets cleanup-jobs

# Limpeza personalizada com log
flask secrets cleanup-jobs --finished-older-than 30 --stalled-older-than 14 --logfile "limpeza_jobs.log"

# Simulação
flask secrets cleanup-jobs --dry-run --logfile ""
```

### `flask secrets list-jobs`

Lista jobs de re-criptografia com seus status e progresso.

**Opções:**

- `--status`: Filtrar por status (pending, running, finished, failed, paused)
- `--limit` (padrão: `20`): Número máximo de jobs a mostrar
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Listar todos os jobs
flask secrets list-jobs

# Filtrar jobs em execução
flask secrets list-jobs --status running --logfile "jobs_ativos.log"

# Listar últimos 50 jobs
flask secrets list-jobs --limit 50 --logfile ""
```

### `flask secrets backup-config`

Cria backup do arquivo de configuração de chaves.

**Opções:**

- `--env-file` (padrão: `instance/.env.crypto`): Arquivo de configuração para backup
- `--cleanup-old`: Limpar backups antigos após criar novo
- `--keep-backups` (padrão: `5`): Número de backups a manter ao limpar
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Backup simples
flask secrets backup-config

# Backup com limpeza automática
flask secrets backup-config --cleanup-old --keep-backups 10 --logfile "backup.log"
```

### `flask secrets restore-config`

Restaura configuração a partir de um backup.

**Opções:**

- `--backup-file` (obrigatório): Arquivo de backup para restaurar
- `--env-file` (padrão: `instance/.env.crypto`): Arquivo de configuração de destino
- `--yes`: Confirmar sem prompt
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Restaurar de backup específico
flask secrets restore-config --backup-file .env.crypto.backup_20241015_143022

# Restaurar com confirmação automática e log
flask secrets restore-config --backup-file .env.crypto.backup_20241015_143022 --yes --logfile "restauracao.log"
```

### `flask secrets remove-versions`

Remove versões específicas do arquivo de configuração (comando de teste).

**Opções:**

- `--versions` (obrigatório): Versões a remover (separadas por vírgula, ex: v1,v2)
- `--env-file` (padrão: `instance/.env.crypto`): Arquivo de configuração
- `--dry-run`: Simular sem modificar
- `--yes`: Confirmar sem prompt
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Remover versões específicas (simulação)
flask secrets remove-versions --versions v1,v3 --dry-run --logfile ""

# Remover versões (execução real)
flask secrets remove-versions --versions v1 --yes --logfile "remocao_versoes.log"
```

### `flask secrets cleanup-keys`

Limpa versões antigas de chaves criptográficas mantendo apenas as mais recentes.

**Opções:**

- `--model` (obrigatório): Modelo a analisar no formato module:Class (ex: app.models.user:User)
- `--column` (obrigatório): Nome da coluna criptografada a analisar
- `--keep-versions` (padrão: `3`): Número de versões mais recentes a manter
- `--env-file` (padrão: `instance/.env.crypto`): Arquivo de configuração
- `--dry-run`: Simular operação sem fazer modificações
- `--yes`: Confirmar operação sem prompt interativo
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Limpeza simulada mantendo 3 versões
flask secrets cleanup-keys --model app.models.user:User --column encrypted_field --dry-run --logfile ""

# Limpeza real mantendo 5 versões
flask secrets cleanup-keys --model app.models.user:User --column encrypted_field --keep-versions 5 --yes --logfile "limpeza_$(date +%Y%m%d).log"
```

### `flask secrets validate-config`

Valida a integridade do arquivo de configuração.

**Opções:**

- `--env-file` (padrão: `instance/.env.crypto`): Arquivo de configuração
- `--logfile`: Arquivo para salvar logs

**Exemplos:**

```bash
# Validação básica
flask secrets validate-config

# Validação com log detalhado
flask secrets validate-config --logfile "validacao_config.log"
```

## Benefícios e Integração dos Logs

### Benefícios do Sistema de Logs

1. **Trilha de Auditoria**: Registro completo de operações para conformidade
2. **Depuração**: Logs detalhados para solução de problemas
3. **Automação**: Fácil integração com scripts e pipelines CI/CD
4. **Monitoramento**: Acompanhar histórico e performance das operações

### Exemplos de Uso Avançado

```bash
# Operação de limpeza com log detalhado
flask secrets cleanup-keys \
  --model app.models.user:User \
  --column encrypted_field \
  --keep-versions 3 \
  --logfile "limpeza_$(date +%Y%m%d).log"

# Re-criptografia com log auto-gerado
flask secrets reencrypt \
  --model app.models.user:User \
  --column encrypted_field \
  --logfile ""

# Validação de configuração com relatório
flask secrets validate-config --logfile "relatorio_validacao.log"
```

### Integração com Sistemas de Monitoramento

O output dos logs pode ser facilmente integrado com sistemas de monitoramento:

```bash
# Enviar logs para syslog
flask secrets cleanup-keys --model app.models.user:User --column encrypted_field --logfile "" | logger

# Monitorar logs em tempo real
flask secrets reencrypt --model app.models.user:User --column encrypted_field --logfile "recriptografia.log" &
tail -f recriptografia.log

# Integração com ELK Stack
flask secrets cleanup-keys --model app.models.user:User --column encrypted_field --logfile "/var/log/app/cleanup.log"

# Análise de logs com grep
grep "CLEANUP-AUDIT" /var/log/app/*.log | grep "Erro"
grep "CLEANUP-SUMMARY" /var/log/app/*.log | tail -10
```

### Automação e Scripts

```bash
#!/bin/bash
# Script de manutenção automática

LOG_DIR="/var/log/secrets"
DATE=$(date +%Y%m%d)

# Criar diretório de logs se não existir
mkdir -p "$LOG_DIR"

# Limpeza de jobs antigos
flask secrets cleanup-jobs \
  --finished-older-than 30 \
  --stalled-older-than 7 \
  --yes \
  --logfile "$LOG_DIR/cleanup-jobs-$DATE.log"

# Validação de configuração
flask secrets validate-config \
  --logfile "$LOG_DIR/validate-config-$DATE.log"

# Backup de configuração
flask secrets backup-config \
  --cleanup-old \
  --keep-backups 10 \
  --logfile "$LOG_DIR/backup-config-$DATE.log"

echo "Manutenção concluída. Logs salvos em $LOG_DIR"
```

## Uso em Código Python

### Definir Campo Criptografado

No seu modelo SQLAlchemy:

```python
from app.models.custom_types import EncryptedString
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from app.infra.modulos import db

class User(db.Model):
    __tablename__ = "usuarios"

    # Campo criptografado
    _otp_secret: Mapped[Optional[str]] = mapped_column(
        EncryptedString(length=500),  # Tamanho no DB (inclui overhead de criptografia)
        default=None
    )

    # Property para acesso conveniente
    @property
    def otp_secret(self):
        return self._otp_secret

    @otp_secret.setter
    def otp_secret(self, value: Optional[str]):
        self._otp_secret = value
```

### Criar Registro com Dados Criptografados

```python
from app.models.autenticacao import User
from app.infra.modulos import db

# Criar usuário
user = User(nome="João Silva",
            email="joao@example.com",
            password="senha123",
            otp_secret="JBSWY3DPEHPK3PXP"  # Será criptografado automaticamente
)

db.session.add(user)
db.session.commit()

# Ler valor descriptografado
print(user.otp_secret)  # Output: "JBSWY3DPEHPK3PXP"
```

### Atualizar Dados Criptografados

```python
# Buscar usuário
user = User.query.filter_by(email="joao@example.com").first()

# Atualizar valor (será re-criptografado automaticamente)
user.otp_secret = "NOVO_SEGREDO_OTP"
db.session.commit()
```

## Boas Práticas de Segurança

### 1. Proteção de Chaves

- ✅ **FAÇA**: Mantenha `.env.crypto` fora do controle de versão
- ✅ **FAÇA**: Use permissões restritivas (chmod 600) no arquivo
- ✅ **FAÇA**: Faça backups criptografados das chaves
- ❌ **NÃO FAÇA**: Comite `.env.crypto` no Git
- ❌ **NÃO FAÇA**: Compartilhe chaves por email ou chat
- ❌ **NÃO FAÇA**: Use as mesmas chaves em dev/staging/prod

### 2. Rotação de Chaves

- Rotacione chaves a cada 90-180 dias
- Rotacione imediatamente se houver suspeita de comprometimento
- Mantenha logs de quando cada rotação foi feita
- Teste o processo de rotação em ambiente de staging primeiro

### 3. Backup de Chaves

```bash
# Backup local (criptografado)
gpg --symmetric --cipher-algo AES256 .env.crypto
mv .env.crypto.gpg ~/backups/env-crypto-$(date +%Y%m%d).gpg

# Em produção, use um gerenciador de segredos
# Ex: AWS Secrets Manager, HashiCorp Vault, Azure Key Vault
```

### 4. Ambientes Separados

Use chaves diferentes para cada ambiente:

```bash
# Desenvolvimento
.env.crypto

# Staging
.env.crypto.staging

# Produção
.env.crypto.production
```

Configure a aplicação para carregar o arquivo correto:

```python
import os
env = os.getenv('FLASK_ENV', 'development')
crypto_file = f'.env.crypto.{env}' if env != 'development' else '.env.crypto'
```

### 5. Monitoramento

- Monitore logs de erros de criptografia/descriptografia
- Configure alertas para falhas de validação de integridade
- Acompanhe métricas de performance da criptografia

### 6. Gestão de Segredos em Produção

Para ambientes de produção, considere migrar para uma solução enterprise:

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name myapp/encryption-keys \
  --secret-string file://.env.crypto

# HashiCorp Vault
vault kv put secret/myapp/encryption @.env.crypto
```

## Resolução de Problemas

### Erro: "SecretsManager não inicializado"

**Causa**: O `SecretsManager` não foi registrado corretamente na aplicação.

**Solução**: Verifique se `secrets_manager.init_app(app)` está sendo chamado em `app/__init__.py`:

```python
from app.infra.modulos import secrets_manager

secrets_manager.init_app(app)
```

### Erro: "Incorrect padding" ou "Invalid token"

**Causa**: A chave usada para criptografar não está mais disponível ou foi alterada.

**Solução**:

1. Verifique se `.env.crypto` contém todas as versões de chaves necessárias
2. Use `flask secrets list` para ver quais versões estão configuradas
3. Se perdeu chaves antigas, restaure do backup

### Erro: "Salt integrity check failed"

**Causa**: O hash do salt não corresponde ao salt fornecido.

**Solução**:

1. Verifique se `.env.crypto` não foi corrompido
2. Restaure de um backup válido
3. Como último recurso, regenere as chaves (perderá dados criptografados antigos)

### Job de Re-criptografia Interrompido

Se um job de re-criptografia for interrompido:

```bash
# Retomar do ponto onde parou
flask secrets reencrypt --model app.models.autenticacao:User --column _otp_secret --resume --logfile "retomada.log"

# Listar jobs para verificar status
flask secrets list-jobs --status running --logfile ""

# Limpar jobs antigos se necessário
flask secrets cleanup-jobs --finished-older-than 7 --yes --logfile "limpeza_jobs.log"
```

O sistema mantém registro do progresso no banco de dados (tabela `reencrypt_jobs`).

### Problemas com Arquivo de Log

**Erro: "Não foi possível configurar arquivo de log"**

**Causa**: Permissões insuficientes ou diretório não existe.

**Solução**:

```bash
# Verificar permissões do diretório
ls -la $(dirname "meu_arquivo.log")

# Criar diretório se necessário
mkdir -p logs/

# Usar arquivo no diretório atual
flask secrets list --logfile "operacao.log"
```

### Análise de Logs de Operações

```bash
# Ver operações recentes
grep 'CLEANUP-SUMMARY' logs/app.log | tail -10

# Ver erros de limpeza
grep 'CLEANUP-AUDIT.*Erro' logs/app.log

# Ver rollbacks automáticos
grep 'CLEANUP-AUDIT.*Rollback' logs/app.log

# Estatísticas de uma operação específica
flask secrets cleanup-stats --operation-id cleanup_20241015_143022_a1b2 --logfile ""
```

### Backup e Restauração de Configuração

**Problema**: Arquivo de configuração corrompido ou perdido.

**Solução**:

```bash
# Listar backups disponíveis
ls -la .env.crypto.backup_*

# Restaurar do backup mais recente
LATEST_BACKUP=$(ls -t .env.crypto.backup_* | head -1)
flask secrets restore-config --backup-file "$LATEST_BACKUP" --logfile "restauracao.log"

# Validar após restauração
flask secrets validate-config --logfile "validacao_pos_restauracao.log"
```

## Arquitetura Interna

### Fluxo de Criptografia

```
┌─────────────┐
│ Aplicação   │
│ user.otp =  │
│ "SECRET"    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ EncryptedString     │
│ process_bind_param()│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ SecretsManager      │
│ encrypt()           │
│ - Obtém chave ativa │
│ - Deriva com salt   │
│ - Criptografa       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Banco de Dados      │
│ "v2:Z0FBQUFBQm8..." │
└─────────────────────┘
```

### Fluxo de Descriptografia

```
┌─────────────────────┐
│ Banco de Dados      │
│ "v2:Z0FBQUFBQm8..." │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────────┐
│ EncryptedString         │
│ process_result_value()  │
│ - Parse versão          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ SecretsManager          │
│ decrypt()               │
│ - Busca chave v2        │
│ - Deriva com salt       │
│ - Descriptografa        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────┐
│ Aplicação   │
│ "SECRET"    │
└─────────────┘
```

## Referências

- [Cryptography.io - Fernet](https://cryptography.io/en/latest/fernet/)
- [SQLAlchemy - Custom Types](https://docs.sqlalchemy.org/en/20/core/custom_types.html)
- [OWASP - Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)

---

**Última atualização**: 2024-10-15
**Versão do documento**: 2.0
**Novidades desta versão**:

- Adicionados novos comandos CLI: `cleanup-jobs`, `list-jobs`, `backup-config`, `restore-config`, `remove-versions`, `cleanup-keys`, `validate-config`, `cleanup-stats`
- Implementado suporte a `--logfile` em todos os comandos para auditoria e depuração
- Melhorada documentação com exemplos práticos de automação e monitoramento
- Adicionadas seções sobre integração com sistemas de monitoramento e scripts de manutenção

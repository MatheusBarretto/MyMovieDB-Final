# Requirements Document

## Introduction

Esta funcionalidade adiciona um comando CLI para limpeza automática de chaves criptográficas antigas no sistema, permitindo manter apenas um número determinado de versões mais recentes. O objetivo é evitar o acúmulo excessivo de chaves no banco de dados e arquivos de configuração, mantendo a segurança e permitindo rollback para versões recentes quando necessário.

## Requirements

### Requirement 1

**User Story:** Como administrador do sistema, eu quero poder limpar chaves criptográficas antigas automaticamente, para que o sistema não acumule versões desnecessárias e mantenha apenas as versões mais recentes necessárias para operação.

#### Acceptance Criteria

1. WHEN o comando de limpeza é executado com modelo e coluna especificados THEN o sistema SHALL identificar todas as versões de chaves disponíveis
2. WHEN o número de versões a manter é especificado THEN o sistema SHALL preservar exatamente esse número das versões mais recentes que não estão em uso
3. WHEN versões antigas são identificadas para remoção THEN o sistema SHALL remover as chaves dos arquivos de configuração
4. WHEN a versão ativa está entre as versões a serem removidas THEN o sistema SHALL gerar um erro e não executar a limpeza
5. WHEN versões em uso nos dados são identificadas THEN o sistema SHALL sempre preservar essas versões independentemente do número especificado

### Requirement 2

**User Story:** Como administrador do sistema, eu quero ter controle sobre quantas versões manter, para que eu possa balancear entre segurança (capacidade de rollback) e limpeza do sistema.

#### Acceptance Criteria

1. WHEN o comando é executado sem especificar número de versões THEN o sistema SHALL usar um padrão de 3 versões
2. WHEN o número de versões especificado é maior que as versões existentes THEN o sistema SHALL manter todas as versões existentes
3. WHEN o número de versões especificado é menor que 1 THEN o sistema SHALL gerar um erro
4. WHEN o número de versões especificado é 1 THEN o sistema SHALL manter apenas a versão ativa

### Requirement 3

**User Story:** Como administrador do sistema, eu quero poder simular a limpeza antes de executá-la, para que eu possa verificar quais versões serão removidas sem fazer alterações irreversíveis.

#### Acceptance Criteria

1. WHEN o modo dry-run é ativado THEN o sistema SHALL mostrar quais versões seriam removidas sem executar a remoção
2. WHEN o modo dry-run é ativado THEN o sistema SHALL mostrar quais versões seriam mantidas
3. WHEN o modo dry-run é ativado THEN nenhum arquivo ou configuração SHALL ser modificado
4. WHEN o modo dry-run é executado THEN o sistema SHALL mostrar o impacto estimado da operação

### Requirement 4

**User Story:** Como administrador do sistema, eu quero ter confirmação antes da remoção das chaves, para que eu possa evitar remoções acidentais de versões importantes.

#### Acceptance Criteria

1. WHEN a limpeza é executada sem flag de confirmação THEN o sistema SHALL solicitar confirmação do usuário
2. WHEN a flag --yes é usada THEN o sistema SHALL executar a limpeza sem solicitar confirmação
3. WHEN o usuário cancela a confirmação THEN nenhuma versão SHALL ser removida
4. WHEN versões críticas estão sendo removidas THEN o sistema SHALL mostrar avisos específicos

### Requirement 5

**User Story:** Como administrador do sistema, eu quero especificar qual modelo e atributo verificar para determinar se uma versão de chave está em uso, para que o sistema possa tomar decisões informadas sobre quais versões podem ser removidas com segurança.

#### Acceptance Criteria

1. WHEN o comando é executado THEN o sistema SHALL exigir a especificação de modelo e coluna no formato 'module:Class' e nome da coluna
2. WHEN modelo e coluna são especificados THEN o sistema SHALL verificar quais versões de chave estão sendo usadas nos dados criptografados dessa coluna
3. WHEN uma versão de chave está sendo usada nos dados THEN o sistema SHALL preservar essa versão independentemente da quantidade especificada para manter
4. WHEN uma versão de chave não está sendo usada nos dados THEN o sistema SHALL considerar essa versão como candidata para remoção
5. WHEN o modelo ou coluna especificados não existem THEN o sistema SHALL gerar um erro explicativo

### Requirement 6

**User Story:** Como administrador do sistema, eu quero que a limpeza seja segura e reversível, para que eu possa recuperar versões removidas se necessário através de backups.

#### Acceptance Criteria

1. WHEN versões são removidas THEN o sistema SHALL criar um backup das configurações antes da remoção
2. WHEN a remoção falha THEN o sistema SHALL restaurar o estado anterior automaticamente
3. WHEN versões são removidas THEN o sistema SHALL registrar log detalhado da operação
4. WHEN há jobs de recriptografia pendentes THEN o sistema SHALL avisar sobre possíveis impactos mas permitir a remoção


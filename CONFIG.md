# Configuração da Aplicação

Este documento descreve as opções de configuração disponíveis para a aplicação MyMovieDB.

## Arquivo de Configuração

A aplicação utiliza um arquivo JSON para configuração, localizado no diretório `instance/`. Por padrão, o arquivo utilizado é `instance/config.dev.json`.

Para utilizar um arquivo de configuração diferente, especifique o nome do arquivo ao criar a aplicação.

## Opções de Configuração

### Aplicação Básica

#### `APP_NAME` (opcional)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: Nome da aplicação, utilizado em emails e interface
- **Exemplo**: `"MyMovieDB"`

#### `APP_HOST` (opcional)
- **Tipo**: String
- **Padrão**: `"0.0.0.0"`
- **Descrição**: Endereço IP no qual a aplicação será executada
- **Exemplo**: `"0.0.0.0"` (todas as interfaces) ou `"127.0.0.1"` (apenas localhost)

#### `APP_PORT` (opcional)
- **Tipo**: Integer
- **Padrão**: `5000`
- **Descrição**: Porta na qual a aplicação será executada
- **Validação**: Deve ser um inteiro entre 1 e 65535
- **Exemplo**: `5000`

#### `TIMEZONE` (opcional)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: Timezone da aplicação
- **Exemplo**: `"America/Sao_Paulo"`

### Segurança

#### `SECRET_KEY` (obrigatório em produção)
- **Tipo**: String
- **Padrão**: Gerado automaticamente (não recomendado para produção)
- **Descrição**: Chave secreta utilizada para criptografia de tokens JWT e sessões. Se não fornecida, uma chave aleatória será gerada a cada execução, invalidando tokens anteriores
- **Exemplo**: `"e92a984a9a1ced6c12d532d2f1c7c61c81552526547e1eeb647ed8a3bff4aabb"`
- **⚠️ Importante**: Em produção, sempre defina uma chave fixa e segura. Use `os.urandom(32).hex()` para gerar uma

#### `PASSWORD_MIN` (opcional)
- **Tipo**: Integer
- **Padrão**: `0` (sem validação de tamanho mínimo)
- **Descrição**: Comprimento mínimo obrigatório para senhas de usuários
- **Exemplo**: `8`

#### `PASSWORD_MAIUSCULA` (opcional)
- **Tipo**: Boolean
- **Padrão**: `false`
- **Descrição**: Se `true`, senhas devem conter pelo menos uma letra maiúscula (A-Z)
- **Exemplo**: `true`

#### `PASSWORD_MINUSCULA` (opcional)
- **Tipo**: Boolean
- **Padrão**: `false`
- **Descrição**: Se `true`, senhas devem conter pelo menos uma letra minúscula (a-z)
- **Exemplo**: `true`

#### `PASSWORD_NUMERO` (opcional)
- **Tipo**: Boolean
- **Padrão**: `false`
- **Descrição**: Se `true`, senhas devem conter pelo menos um número (0-9)
- **Exemplo**: `true`

#### `PASSWORD_SIMBOLO` (opcional)
- **Tipo**: Boolean
- **Padrão**: `false`
- **Descrição**: Se `true`, senhas devem conter pelo menos um símbolo especial (!@#$%&*, etc.)
- **Exemplo**: `true`

#### `PASSWORD_MAX_AGE` (opcional)
- **Tipo**: Integer
- **Padrão**: `0` (sem validação de idade)
- **Descrição**: Idade máxima permitida para senhas, em dias. Se a senha for mais antiga que este valor, o usuário receberá um aviso após o login recomendando a troca. Se `0` ou não definido, não haverá validação de idade de senha
- **Exemplo**: `90` (90 dias)
- **Nota**: Este é um aviso de segurança que não bloqueia o login, apenas informa ao usuário

#### `2FA_SESSION_TIMEOUT` (opcional)
- **Tipo**: Integer
- **Padrão**: `90` (segundos)
- **Descrição**: Tempo máximo, em segundos, que o usuário tem para inserir o código 2FA após ter digitado a senha correta. Após este tempo, o token de sessão expira e o usuário precisa fazer login novamente
- **Exemplo**: `120` (2 minutos)


### Upload de Imagens

#### `AVATAR_SIZE` (opcional)
- **Tipo**: Integer
- **Padrão**: `64`
- **Descrição**: Tamanho do avatar em pixels (largura e altura). O avatar é gerado automaticamente a partir da foto do perfil, redimensionado proporcionalmente para caber neste tamanho
- **Exemplo**: `128`

#### `MAX_IMAGE_SIZE` (opcional)
- **Tipo**: Integer
- **Padrão**: `5242880` (5 MB)
- **Descrição**: Tamanho máximo permitido para upload de imagens, em bytes
- **Exemplos**:
  - `1048576` (1 MB)
  - `10485760` (10 MB)
  - `5242880` (5 MB - padrão)

#### `MAX_IMAGE_DIMENSIONS` (opcional)
- **Tipo**: Array com 2 inteiros [largura, altura]
- **Padrão**: `[2048, 2048]`
- **Descrição**: Dimensões máximas permitidas para imagens, em pixels (largura x altura). Imagens maiores serão rejeitadas
- **Exemplo**: `[4096, 4096]`

#### `MAX_CONTENT_LENGTH` (opcional)
- **Tipo**: Integer
- **Padrão**: `16777216` (16 MB)
- **Descrição**: Tamanho máximo permitido para requisições HTTP, em bytes. Este limite se aplica ao tamanho total da requisição, incluindo todos os campos do formulário e arquivos enviados. É importante que este valor seja maior ou igual a `MAX_IMAGE_SIZE` para permitir uploads de imagens
- **Exemplos**:
  - `5242880` (5 MB)
  - `16777216` (16 MB - padrão)
  - `52428800` (50 MB)
- **⚠️ Importante**: Se você estiver tendo erros 413 (Request Entity Too Large), aumente este valor. O limite também é validado pelo Werkzeug internamente, então valores muito baixos podem causar problemas com uploads de imagens

### Banco de Dados

#### `SQLALCHEMY_DATABASE_URI` (obrigatório)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: URI de conexão com o banco de dados
- **Exemplos**:
  - SQLite: `"sqlite:///mymovie.db"`
  - PostgreSQL: `"postgresql://user:password@localhost/dbname"`
  - MySQL: `"mysql://user:password@localhost/dbname"`

#### `MAX_PER_PAGE` (opcional)
- **Tipo**: Integer
- **Padrão**: `500`
- **Descrição**: Número máximo de itens por página em paginação
- **Exemplo**: `50`

### Interface (Bootstrap)

#### `BOOTSTRAP_SERVE_LOCAL` (opcional)
- **Tipo**: Boolean
- **Padrão**: `false`
- **Descrição**: Se `true`, serve os arquivos Bootstrap localmente. Se `false`, utiliza CDN
- **Exemplo**: `true`

#### `BOOTSTRAP_BOOTSWATCH_THEME` (opcional)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: Nome do tema Bootswatch a ser utilizado
- **Exemplo**: `"Litera"`, `"Darkly"`, `"Cosmo"`, etc.
- **Referência**: https://bootswatch.com/

### Email

#### `SEND_EMAIL` (opcional)
- **Tipo**: Boolean
- **Padrão**: `false`
- **Descrição**: Se `true`, envia emails reais. Se `false`, utiliza provedor mock (desenvolvimento)
- **Exemplo**: `false`

#### `EMAIL_SENDER` (obrigatório)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: Endereço de email remetente padrão
- **Exemplo**: `"noreply@mymoviedb.com"`

#### `EMAIL_SENDER_NAME` (opcional)
- **Tipo**: String
- **Padrão**: Valor de `APP_NAME`
- **Descrição**: Nome do remetente exibido nos emails
- **Exemplo**: `"MyMovieDB Team"`

#### `EMAIL_PROVIDER` (obrigatório quando `SEND_EMAIL=true`)
- **Tipo**: String
- **Padrão**: `"postmark"`
- **Descrição**: Provedor de email a ser utilizado
- **Valores aceitos**: `"postmark"`, `"smtp"`
- **Exemplo**: `"postmark"`

### Configuração do Postmark (quando `EMAIL_PROVIDER="postmark"`)

#### `POSTMARK_SERVER_TOKEN` (obrigatório)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: Token de servidor da API do Postmark
- **Exemplo**: `"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`
- **Referência**: https://postmarkapp.com/

### Configuração SMTP (quando `EMAIL_PROVIDER="smtp"`)

#### `SMTP_SERVER` (obrigatório)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: Endereço do servidor SMTP
- **Exemplo**: `"smtp.gmail.com"`

#### `SMTP_PORT` (opcional)
- **Tipo**: Integer
- **Padrão**: `587`
- **Descrição**: Porta do servidor SMTP
- **Exemplo**: `587` (TLS) ou `465` (SSL)

#### `SMTP_USERNAME` (obrigatório)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: Nome de usuário para autenticação SMTP
- **Exemplo**: `"user@example.com"`

#### `SMTP_PASSWORD` (obrigatório)
- **Tipo**: String
- **Padrão**: N/A
- **Descrição**: Senha para autenticação SMTP
- **Exemplo**: `"your-password-here"`

#### `SMTP_USE_TLS` (opcional)
- **Tipo**: Boolean
- **Padrão**: `true`
- **Descrição**: Se `true`, utiliza TLS para conexão segura
- **Exemplo**: `true`

## Exemplos de Configuração

### Desenvolvimento (Mock Email)

```json
{
  "BOOTSTRAP_SERVE_LOCAL": true,
  "BOOTSTRAP_BOOTSWATCH_THEME": "Litera",
  "APP_NAME": "MyMovieDB",
  "APP_HOST": "0.0.0.0",
  "APP_PORT": 5000,
  "TIMEZONE": "America/Sao_Paulo",
  "SQLALCHEMY_DATABASE_URI": "sqlite:///mymovie.db",
  "SECRET_KEY": "e92a984a9a1ced6c12d532d2f1c7c61c81552526547e1eeb647ed8a3bff4aabb",
  "PASSWORD_MIN": 8,
  "PASSWORD_MAIUSCULA": true,
  "PASSWORD_MINUSCULA": true,
  "PASSWORD_NUMERO": true,
  "PASSWORD_SIMBOLO": false,
  "AVATAR_SIZE": 64,
  "MAX_IMAGE_SIZE": 5242880,
  "MAX_IMAGE_DIMENSIONS": [2048, 2048],
  "MAX_CONTENT_LENGTH": 5242880,
  "EMAIL_SENDER": "dev@localhost",
  "SEND_EMAIL": false
}
```

### Produção (Postmark)

```json
{
  "BOOTSTRAP_SERVE_LOCAL": false,
  "BOOTSTRAP_BOOTSWATCH_THEME": "Litera",
  "APP_NAME": "MyMovieDB",
  "APP_HOST": "0.0.0.0",
  "APP_PORT": 8000,
  "TIMEZONE": "America/Sao_Paulo",
  "SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@db.example.com/mymoviedb",
  "SECRET_KEY": "YOUR-SECURE-RANDOM-SECRET-KEY-HERE",
  "PASSWORD_MIN": 12,
  "PASSWORD_MAIUSCULA": true,
  "PASSWORD_MINUSCULA": true,
  "PASSWORD_NUMERO": true,
  "PASSWORD_SIMBOLO": true,
  "PASSWORD_MAX_AGE": 90,
  "2FA_SESSION_TIMEOUT": 120,
  "AVATAR_SIZE": 128,
  "MAX_IMAGE_SIZE": 10485760,
  "MAX_IMAGE_DIMENSIONS": [4096, 4096],
  "MAX_CONTENT_LENGTH": 16777216,
  "EMAIL_SENDER": "noreply@mymoviedb.com",
  "EMAIL_SENDER_NAME": "MyMovieDB",
  "SEND_EMAIL": true,
  "EMAIL_PROVIDER": "postmark",
  "POSTMARK_SERVER_TOKEN": "your-postmark-token-here"
}
```

### Produção (SMTP/Gmail)

```json
{
  "BOOTSTRAP_SERVE_LOCAL": false,
  "BOOTSTRAP_BOOTSWATCH_THEME": "Litera",
  "APP_NAME": "MyMovieDB",
  "APP_HOST": "0.0.0.0",
  "APP_PORT": 8000,
  "TIMEZONE": "America/Sao_Paulo",
  "SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@db.example.com/mymoviedb",
  "SECRET_KEY": "YOUR-SECURE-RANDOM-SECRET-KEY-HERE",
  "PASSWORD_MIN": 12,
  "PASSWORD_MAIUSCULA": true,
  "PASSWORD_MINUSCULA": true,
  "PASSWORD_NUMERO": true,
  "PASSWORD_SIMBOLO": true,
  "PASSWORD_MAX_AGE": 90,
  "2FA_SESSION_TIMEOUT": 120,
  "AVATAR_SIZE": 128,
  "MAX_IMAGE_SIZE": 10485760,
  "MAX_IMAGE_DIMENSIONS": [4096, 4096],
  "MAX_CONTENT_LENGTH": 16777216,
  "EMAIL_SENDER": "noreply@gmail.com",
  "EMAIL_SENDER_NAME": "MyMovieDB",
  "SEND_EMAIL": true,
  "EMAIL_PROVIDER": "smtp",
  "SMTP_SERVER": "smtp.gmail.com",
  "SMTP_PORT": 587,
  "SMTP_USERNAME": "your-email@gmail.com",
  "SMTP_PASSWORD": "your-app-password",
  "SMTP_USE_TLS": true
}
```

## Notas Importantes

1. **Nunca comite** arquivos de configuração contendo dados sensíveis (senhas, tokens) no controle de versão
2. Use variáveis de ambiente ou serviços de gerenciamento de segredos em produção
3. A aplicação validará as configurações obrigatórias na inicialização e exibirá erros claros se algo estiver faltando
4. Quando `SEND_EMAIL=false`, todos os emails serão exibidos nos logs em vez de serem enviados

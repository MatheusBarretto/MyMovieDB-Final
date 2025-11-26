# Requirements Document

## Introduction

Este documento especifica os requisitos para implementar a funcionalidade de busca genérica no MyMovieDB. A interface de busca já existe na navbar da aplicação, mas atualmente não possui funcionalidade implementada (action="#"). Este spec define os requisitos para conectar a interface existente a um sistema de busca que permite pesquisar simultaneamente em filmes e pessoas.

## Glossary

- **Sistema_Busca**: O sistema de busca genérica do MyMovieDB
- **Usuario**: Qualquer pessoa que acessa a aplicação (autenticada ou não)
- **Termo_Busca**: A string de texto inserida pelo usuário para realizar a pesquisa
- **Resultado_Filme**: Um filme encontrado na busca que corresponde aos critérios
- **Resultado_Pessoa**: Uma pessoa encontrada na busca que corresponde aos critérios
- **Interface_Busca**: O campo de entrada e botão de busca na página inicial
- **Lista_Resultados**: A página que exibe os resultados da busca organizados por tipo

## Requirements

### Requirement 1

**User Story:** Como usuário do MyMovieDB, eu quero que o campo de busca existente na navbar funcione para pesquisar filmes e pessoas, para que eu possa encontrar rapidamente o conteúdo que procuro sem precisar navegar por diferentes seções.

#### Acceptance Criteria

1. THE Sistema_Busca SHALL conectar o campo de busca existente na navbar a uma rota funcional
2. WHEN o Usuario digita um Termo_Busca e pressiona Enter ou clica no botão de busca, THE Sistema_Busca SHALL executar a pesquisa
3. THE Sistema_Busca SHALL pesquisar simultaneamente em filmes e pessoas
4. THE Sistema_Busca SHALL redirecionar o Usuario para uma página de resultados
5. THE Sistema_Busca SHALL funcionar para usuários autenticados e não autenticados

### Requirement 2

**User Story:** Como usuário, eu quero que a busca encontre filmes baseada em títulos e sinopses, para que eu possa localizar filmes mesmo quando não lembro o título exato.

#### Acceptance Criteria

1. WHEN o Usuario insere um Termo_Busca, THE Sistema_Busca SHALL pesquisar no campo titulo_original dos filmes
2. WHEN o Usuario insere um Termo_Busca, THE Sistema_Busca SHALL pesquisar no campo titulo_portugues dos filmes
3. WHEN o Usuario insere um Termo_Busca, THE Sistema_Busca SHALL pesquisar no campo sinopse dos filmes
4. THE Sistema_Busca SHALL realizar busca case-insensitive em todos os campos de filme
5. THE Sistema_Busca SHALL retornar Resultado_Filme para qualquer correspondência parcial nos campos especificados

### Requirement 3

**User Story:** Como usuário, eu quero que a busca encontre pessoas baseada em nomes e biografias, para que eu possa localizar atores, diretores e outras pessoas do cinema.

#### Acceptance Criteria

1. WHEN o Usuario insere um Termo_Busca, THE Sistema_Busca SHALL pesquisar no campo nome das pessoas
2. WHEN o Usuario insere um Termo_Busca, THE Sistema_Busca SHALL pesquisar no campo nome_artistico dos atores
3. WHEN o Usuario insere um Termo_Busca, THE Sistema_Busca SHALL pesquisar no campo biografia das pessoas
4. THE Sistema_Busca SHALL realizar busca case-insensitive em todos os campos de pessoa
5. THE Sistema_Busca SHALL retornar Resultado_Pessoa para qualquer correspondência parcial nos campos especificados

### Requirement 4

**User Story:** Como usuário, eu quero ver os resultados da busca organizados e com informações relevantes, para que eu possa identificar rapidamente o item que procuro e navegar para sua página de detalhes.

#### Acceptance Criteria

1. THE Sistema_Busca SHALL exibir os resultados separados em seções "Filmes" e "Pessoas"
2. WHEN há Resultado_Filme, THE Sistema_Busca SHALL exibir título, ano de lançamento e poster (se disponível)
3. WHEN há Resultado_Pessoa, THE Sistema_Busca SHALL exibir nome, nome artístico (se ator) e foto (se disponível)
4. THE Sistema_Busca SHALL criar links clicáveis para cada resultado que direcionam para a página de detalhes
5. THE Sistema_Busca SHALL exibir uma mensagem quando nenhum resultado for encontrado

### Requirement 5

**User Story:** Como usuário, eu quero que a busca seja eficiente e responsiva, para que eu tenha uma experiência fluida ao pesquisar conteúdo.

#### Acceptance Criteria

1. THE Sistema_Busca SHALL limitar os resultados a um máximo de 20 filmes e 20 pessoas
2. THE Sistema_Busca SHALL executar a consulta em menos de 2 segundos para termos de busca típicos
3. WHEN o Termo_Busca tem menos de 2 caracteres, THE Sistema_Busca SHALL exibir uma mensagem solicitando mais caracteres
4. THE Sistema_Busca SHALL escapar caracteres especiais para prevenir erros de SQL
5. THE Sistema_Busca SHALL manter o Termo_Busca no campo após a execução da pesquisa

### Requirement 6

**User Story:** Como usuário, eu quero que a interface de busca existente seja mantida e funcione corretamente, para que eu possa usar a funcionalidade de forma consistente com o design atual da aplicação.

#### Acceptance Criteria

1. THE Sistema_Busca SHALL manter o placeholder existente "Buscar filmes ou pessoas"
2. THE Sistema_Busca SHALL manter o botão de busca existente funcionando
3. THE Sistema_Busca SHALL manter a responsividade existente (versões desktop e mobile)
4. THE Sistema_Busca SHALL manter as práticas de acessibilidade já implementadas
5. THE Sistema_Busca SHALL preservar a consistência visual com o design existente da aplicação
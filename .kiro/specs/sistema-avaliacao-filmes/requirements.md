# Documento de Requisitos - Sistema de Avaliação de Filmes

## Introdução

O sistema de avaliação de filmes permite que usuários registrados avaliem filmes com notas, comentários e recomendações. O sistema deve fornecer funcionalidades completas para criar, visualizar, editar e excluir avaliações, além de exibir estatísticas agregadas dos filmes baseadas nas avaliações dos usuários.

## Requisitos

### Requisito 1

**História do Usuário:** Como um usuário registrado, eu quero avaliar um filme com nota, comentário e recomendação, para que eu possa compartilhar minha opinião sobre o filme.

#### Critérios de Aceitação

1. QUANDO um usuário autenticado acessa a página de um filme ENTÃO o sistema DEVE exibir um formulário de avaliação
2. QUANDO um usuário submete uma avaliação ENTÃO o sistema DEVE validar que a nota está entre 0 e 5
3. QUANDO um usuário submete uma avaliação ENTÃO o sistema DEVE permitir comentário opcional de até 1000 caracteres
4. QUANDO um usuário submete uma avaliação ENTÃO o sistema DEVE permitir marcar se recomendaria o filme
5. QUANDO um usuário submete uma avaliação válida ENTÃO o sistema DEVE salvar a avaliação no banco de dados
6. QUANDO um usuário já avaliou um filme ENTÃO o sistema DEVE atualizar a avaliação existente ao invés de criar uma nova

### Requisito 2

**História do Usuário:** Como um usuário, eu quero visualizar as avaliações de um filme, para que eu possa ler as opiniões de outros usuários antes de assistir.

#### Critérios de Aceitação

1. QUANDO um usuário acessa a página de um filme ENTÃO o sistema DEVE exibir todas as avaliações do filme
2. QUANDO exibindo avaliações ENTÃO o sistema DEVE mostrar nota, comentário, recomendação e nome do usuário
3. QUANDO exibindo avaliações ENTÃO o sistema DEVE ordenar por data de criação (mais recentes primeiro)
4. QUANDO há muitas avaliações ENTÃO o sistema DEVE implementar paginação com 10 avaliações por página
5. QUANDO não há avaliações ENTÃO o sistema DEVE exibir mensagem informativa

### Requisito 3

**História do Usuário:** Como um usuário registrado, eu quero editar ou excluir minha avaliação, para que eu possa corrigir ou remover minha opinião sobre um filme.

#### Critérios de Aceitação

1. QUANDO um usuário visualiza uma avaliação própria ENTÃO o sistema DEVE exibir opções de editar e excluir
2. QUANDO um usuário clica em editar ENTÃO o sistema DEVE carregar o formulário preenchido com os dados atuais
3. QUANDO um usuário salva uma edição ENTÃO o sistema DEVE validar e atualizar a avaliação
4. QUANDO um usuário confirma exclusão ENTÃO o sistema DEVE remover a avaliação permanentemente
5. QUANDO um usuário tenta editar/excluir avaliação de outro usuário ENTÃO o sistema DEVE negar acesso

### Requisito 4

**História do Usuário:** Como um usuário, eu quero ver estatísticas detalhadas de avaliação de um filme, para que eu possa ter uma visão geral completa da recepção do filme.

#### Critérios de Aceitação

1. QUANDO um usuário visualiza um filme ENTÃO o sistema DEVE exibir a nota média com 2 casas decimais
2. QUANDO um usuário visualiza um filme ENTÃO o sistema DEVE exibir o total de avaliações
3. QUANDO um usuário visualiza um filme ENTÃO o sistema DEVE exibir o percentual de recomendações
4. QUANDO um usuário visualiza um filme ENTÃO o sistema DEVE exibir a distribuição de notas por nota inteira (0 a 5) em percentuais
5. QUANDO não há avaliações ENTÃO o sistema DEVE exibir "Sem avaliações" ao invés de estatísticas
6. QUANDO há avaliações ENTÃO o sistema DEVE atualizar estatísticas automaticamente após cada nova avaliação

### Requisito 5

**História do Usuário:** Como um usuário, eu quero navegar por uma lista de filmes com suas avaliações, para que eu possa descobrir filmes bem avaliados.

#### Critérios de Aceitação

1. QUANDO um usuário acessa a lista de filmes ENTÃO o sistema DEVE exibir cada filme com sua nota média
2. QUANDO exibindo a lista ENTÃO o sistema DEVE permitir ordenação por nota média (maior para menor)
3. QUANDO exibindo a lista ENTÃO o sistema DEVE permitir filtrar apenas filmes com avaliações
4. QUANDO exibindo a lista ENTÃO o sistema DEVE implementar paginação com 20 filmes por página
5. QUANDO um filme não tem avaliações ENTÃO o sistema DEVE exibir "Não avaliado"

### Requisito 6

**História do Usuário:** Como um usuário registrado, eu quero ver um filme aleatório, para que eu possa descobrir novos filmes para assistir.

#### Critérios de Aceitação

1. QUANDO um usuário clica em "Filme Aleatório" ENTÃO o sistema DEVE selecionar um filme aleatório do banco
2. QUANDO selecionando filme aleatório ENTÃO o sistema DEVE redirecionar para a página do filme
3. QUANDO não há filmes cadastrados ENTÃO o sistema DEVE exibir mensagem informativa
4. QUANDO há filtros ativos na lista ENTÃO o sistema DEVE considerar apenas filmes que atendem aos filtros
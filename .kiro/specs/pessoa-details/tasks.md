# Implementation Plan

- [x] 1. Criar estrutura de templates para pessoa

  - Criar diretório `app/routes/pessoas/templates/pessoa/web/`
  - Criar template base `details.jinja2` com estrutura de card responsiva
  - Criar template parcial `_header_pessoa.jinja2` seguindo padrão do filme
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Implementar rota de detalhes da pessoa

  - Adicionar rota `/<uuid:pessoa_id>/detalhes` no blueprint pessoa_bp
  - Implementar função `pessoa_detalhes()` com busca da pessoa e tratamento 404
  - Integrar chamadas aos serviços PessoaService e AtorService
  - Preparar contexto de dados para o template
  - _Requirements: 1.1, 2.4, 3.4, 5.1, 5.2_

- [x] 3. Implementar template de header da pessoa

  - Criar `_header_pessoa.jinja2` com nome, biografia e informações básicas
  - Implementar exibição de foto com fallback para placeholder
  - Seguir padrão visual do `_header_filme.jinja2`
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 4. Implementar seção de filmografia como ator

  - Criar coluna para exibição de filmes onde a pessoa atuou
  - Exibir nome dos personagens interpretados
  - Implementar links para detalhes dos filmes
  - Adicionar mensagem informativa quando não há atuações
  - _Requirements: 2.1, 2.2, 2.3, 2.5_

- [x] 5. Implementar seção de participação técnica

  - Criar coluna para exibição de filmes da equipe técnica
  - Exibir funções técnicas desempenhadas
  - Implementar links para detalhes dos filmes
  - Adicionar mensagem informativa quando não há participação técnica
  - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [x] 6. Atualizar template de detalhes do filme


  - Modificar `filme/web/details.jinja2` para incluir links de navegação
  - Adicionar links dos nomes do elenco para detalhes da pessoa
  - Adicionar links dos nomes da equipe técnica para detalhes da pessoa
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ]\* 7. Criar testes para a funcionalidade
- [ ]\* 7.1 Escrever testes unitários para a rota pessoa_detalhes

  - Testar rota com pessoa existente
  - Testar rota com pessoa inexistente (404)
  - Testar integração com serviços
  - _Requirements: 5.1, 5.2, 5.3_

- [ ]\* 7.2 Escrever testes de integração para navegação
  - Testar navegação bidirecional filme ↔ pessoa
  - Testar links funcionais entre páginas
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

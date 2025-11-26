# Implementation Plan

- [x] 1. Criar o serviço de busca genérica







  - Implementar a classe `SearchService` com método `buscar_geral()`
  - Criar as dataclasses `SearchResult`, `FilmeSearchResult` e `PessoaSearchResult`
  - Implementar consultas SQL otimizadas para filmes e pessoas com busca case-insensitive
  - Adicionar tratamento de erros e exceção customizada `SearchServiceError`
  - Limitar resultados a 20 itens por categoria
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.4_

- [x] 2. Implementar a rota de busca





  - Adicionar rota `/buscar` no blueprint `root_bp`
  - Implementar validação de entrada (mínimo 2 caracteres)
  - Integrar com o `SearchService` para executar a busca
  - Adicionar tratamento de erros e logging
  - Retornar template com resultados ou mensagens de erro
  - _Requirements: 1.2, 5.3, 5.4_

- [x] 3. Criar o template de resultados de busca





  - Criar template `app/routes/root/templates/root/buscar.jinja2`
  - Implementar layout responsivo com seções separadas para filmes e pessoas
  - Os resultados devem ser apresentados na forma de lista
  - Os filmes devem ter título, ano e thumbnail do poster
  - As pessoas devem ter nome, nome artístico (opcional) e thumbnail da foto
  - Adicionar links clicáveis para páginas de detalhes
  - Implementar mensagens para "nenhum resultado encontrado"
  - Preservar o termo de busca no campo após a pesquisa
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.5_

- [x] 4. Conectar o formulário da navbar à funcionalidade





  - Atualizar o `action="#"` para `action="{{ url_for('root.buscar') }}"` na navbar
  - Verificar que ambas as versões (desktop e mobile) estão conectadas
  - Manter toda a estrutura visual e responsividade existente
  - _Requirements: 1.1, 6.1, 6.2, 6.3, 6.5_

- [ ]* 5. Criar testes para o serviço de busca
  - Escrever testes unitários para `SearchService.buscar_geral()`
  - Testar cenários: com resultados, sem resultados, só filmes, só pessoas
  - Testar validação de entrada e tratamento de erros
  - Testar busca case-insensitive e caracteres especiais
  - _Requirements: 2.4, 3.4, 5.4_

- [ ]* 6. Criar testes de integração para a rota
  - Testar submissão do formulário da navbar
  - Testar renderização do template de resultados
  - Testar validação de entrada na rota
  - Testar tratamento de erros end-to-end
  - _Requirements: 1.2, 4.1, 4.5, 5.3_
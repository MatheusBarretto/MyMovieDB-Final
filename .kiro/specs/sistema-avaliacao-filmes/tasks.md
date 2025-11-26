# Plano de Implementação - Sistema de Avaliação de Filmes

- [x] 1. Criar estrutura de formulários para avaliações

  - Implementar AvaliacaoForm com validação de nota (0-5), comentário (max 1000 chars) e recomendação
  - Criar diretório app/forms/filme/ e arquivo **init**.py com o formulário
  - _Requisitos: 1.2, 1.3, 1.4_

- [x] 2. Implementar serviço de avaliações

  - Criar AvaliacaoService em app/services/avaliacao_service.py
  - Implementar método criar_ou_atualizar_avaliacao para criar nova avaliação ou atualizar existente
  - Implementar método obter_avaliacao_usuario para buscar avaliação específica do usuário
  - Implementar método listar_avaliacoes_filme com paginação
  - Implementar método excluir_avaliacao com validação de permissão
  - Implementar método validar_permissao_edicao para verificar se usuário pode editar avaliação
  - _Requisitos: 1.5, 1.6, 2.1, 3.1, 3.5_

- [x] 3. Implementar rota de detalhes do filme com avaliações

  - Implementar rota GET /filme/<filme_id> para exibir filme com avaliações e formulário
  - Carregar filme, suas avaliações paginadas e estatísticas usando os serviços
  - Verificar se usuário logado já avaliou o filme para pré-popular formulário
  - _Requisitos: 1.1, 2.1, 2.2, 2.3, 4.1, 4.2, 4.3_

- [x] 4. Implementar rota para criar/atualizar avaliação

  - Implementar rota POST /filme/<filme_id>/avaliar para processar formulário de avaliação
  - Validar dados do formulário e permissões do usuário
  - Usar AvaliacaoService para criar ou atualizar avaliação
  - Redirecionar para página do filme com mensagem de sucesso/erro
  - _Requisitos: 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 5. Implementar rotas para edição e exclusão de avaliações

  - Implementar rota GET/POST /filme/avaliacao/<avaliacao_id>/editar para editar avaliação
  - Implementar rota POST /filme/avaliacao/<avaliacao_id>/excluir para excluir avaliação
  - Validar permissões (usuário só pode editar/excluir suas próprias avaliações)
  - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 6. Criar templates para exibição de avaliações

  - Criar template app/route/filme/templates/filme/web/detalhes.jinja2 para página principal do filme
  - Criar partial app/route/filme/templates/filme/web/\_avaliacao_form.jinja2 para formulário de avaliação
  - Criar partial app/route/filme/templates/filme/web/\_avaliacao_item.jinja2 para exibir avaliação individual
  - Criar partial app/route/filme/templates/filme/web/\_estatisticas.jinja2 para estatísticas do filme
  - _Requisitos: 2.2, 2.4, 4.1, 4.2, 4.3, 4.4_

- [x] 7. Implementar lista de filmes com avaliações

  - Implementar rota GET /filme/ para listar filmes com suas estatísticas
  - Adicionar filtros para filmes com/sem avaliações
  - Implementar ordenação por nota média (maior para menor)
  - Implementar paginação com 20 filmes por página
  - _Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8. Atualizar método FilmeService.obter_estatisticas_avaliacoes para distribuição de notas



  - Adicionar cálculo de distribuição de notas por nota inteira (0, 1, 2, 3, 4, 5) em percentuais
  - Atualizar dataclass FilmeReviewStats para incluir campo distribuicao_notas
  - Manter compatibilidade com notas existentes no banco (assumindo que já estão na escala 0-5)
  - _Requisitos: 4.1, 4.2, 4.3, 4.4_

- [ ] 9. Criar template para lista de filmes

  - Criar template app/route/filme/templates/filme/web/lista.jinja2 para exibir lista de filmes
  - Incluir estatísticas de avaliação para cada filme
  - Implementar controles de filtro e ordenação
  - Adicionar paginação com navegação
  - _Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Implementar funcionalidade de filme aleatório

  - Implementar rota GET /filme/random para selecionar filme aleatório
  - Considerar filtros ativos na seleção aleatória
  - Redirecionar para página de detalhes do filme selecionado
  - Tratar caso de não haver filmes disponíveis
  - _Requisitos: 6.1, 6.2, 6.3, 6.4_

- [x] 11. Registrar blueprint e integrar com aplicação principal

  - Registrar filme_bp no app/**init**.py
  - Verificar se todas as rotas estão funcionando corretamente
  - Testar fluxo completo de avaliação (criar, editar, excluir)
  - _Requisitos: Todos os requisitos_

- [x] 12. Adicionar usuários e avaliações

  - As operações devem ser executadas no arquivo seed_reviews.py, e devem ser idempotentes (veja o que foi feito no seed_data.py)
  - Criar um conjunto de 5 usuários no sistema (Usuário 1, Usuário 2, ..., Usuário 5)
  - Todos com a senha "Senha123", todos ativados a priori.
  - Cada usuário deve produzir avaliação para 8 filmes diferentes
  - As avaliações devem ser variadas: positivas, negativas e neutras
  - Cada avaliação positiva deve produzir uma indicação positiva para o filme

- [ ]\* 13. Implementar testes unitários para AvaliacaoService

  - Escrever testes para método criar_ou_atualizar_avaliacao
  - Escrever testes para método obter_avaliacao_usuario
  - Escrever testes para método listar_avaliacoes_filme
  - Escrever testes para método excluir_avaliacao
  - Escrever testes para método validar_permissao_edicao
  - _Requisitos: 1.5, 1.6, 2.1, 3.1, 3.5_

- [ ]\* 14. Implementar testes de integração para rotas
  - Escrever testes end-to-end para fluxo de criação de avaliação
  - Escrever testes para validação de permissões
  - Escrever testes para paginação e filtros
  - Escrever testes para filme aleatório
  - _Requisitos: Todos os requisitos_

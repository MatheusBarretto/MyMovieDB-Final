# Implementation Plan

- [x] 1. Create service layer for cast and crew management

  - Create CastCrewService class following the established service pattern with session management and error handling
  - Implement methods for adding, editing, and removing cast members (elenco operations)
  - Implement methods for adding, editing, and removing crew members (equipe técnica operations)
  - Add proper validation for uniqueness constraints and required fields
  - _Requirements: 1.4, 1.5, 2.4, 2.5, 3.4, 3.5, 4.4, 4.5, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 2. Create form classes for cast and crew operations

  - Create AdicionarElencoForm with pessoa_id and personagem fields
  - Create EditarElencoForm with pessoa_id and personagem fields
  - Create AdicionarEquipeTecnicaForm with pessoa_id and funcao_tecnica_id fields
  - Create EditarEquipeTecnicaForm with pessoa_id and funcao_tecnica_id fields
  - Add proper validation rules including UUID validation and length constraints
  - _Requirements: 1.4, 2.4, 3.3, 4.3, 6.3, 6.4_

- [x] 3. Implement Flask routes for cast management

  - Create POST route for adding cast members (/filme/<filme_id>/elenco/adicionar)
  - Create POST route for editing cast members (/filme/<filme_id>/elenco/<atuacao_id>/editar)
  - Create POST route for removing cast members (/filme/<filme_id>/elenco/<atuacao_id>/remover)
  - Add proper authentication checks and error handling
  - Integrate with CastCrewService for business logic
  - _Requirements: 1.5, 3.5, 5.4, 6.5, 6.6_

- [x] 4. Implement Flask routes for crew management

  - Create POST route for adding crew members (/filme/<filme_id>/equipe-tecnica/adicionar)
  - Create POST route for editing crew members (/filme/<filme_id>/equipe-tecnica/<equipe_id>/editar)
  - Create POST route for removing crew members (/filme/<filme_id>/equipe-tecnica/<equipe_id>/remover)
  - Add proper authentication checks and error handling
  - Integrate with CastCrewService for business logic
  - _Requirements: 2.5, 4.5, 5.4, 6.5, 6.6_

- [x] 5. Update movie detail template with cast and crew management links

  - Add "Adicionar Elenco" link in cast section for authenticated users
  - Add "Adicionar Equipe Técnica" link in crew section for authenticated users
  - Add small edit/remove links next to each person for authenticated users
  - Links redirect to dedicated pages for each operation
  - _Requirements: 1.2, 2.2, 3.2, 4.2, 5.1, 5.2_

- [x] 6. Create dedicated page templates for cast and crew operations



  - Create template for adding cast members with person search and character input
  - Create template for editing cast members with pre-populated data
  - Create template for adding crew members with person search and role dropdown
  - Create template for editing crew members with pre-populated data
  - Create confirmation templates for removal operations
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]\* 7. Write comprehensive tests for the cast and crew management feature

  - Create unit tests for CastCrewService methods covering success and error scenarios
  - Write integration tests for all new Flask routes with authentication checks
  - Add tests for form validation with valid and invalid data
  - Test uniqueness constraints and error handling scenarios
  - _Requirements: 6.1, 6.2, 6.5, 6.6_

- [ ]\* 8. Integration and final testing
  - Test complete user workflows for adding, editing, and removing cast and crew
  - Verify proper error handling and user feedback across all operations
  - Ensure responsive design works correctly on different screen sizes
  - Test authentication requirements and access control
  - Validate that public users see appropriate read-only views
  - _Requirements: 7.5, 8.5_

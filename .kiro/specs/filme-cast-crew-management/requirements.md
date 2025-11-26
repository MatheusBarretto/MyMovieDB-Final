# Requirements Document

## Introduction

This feature enables authenticated users to manage cast (elenco) and technical crew (equipe técnica) for movies in the MyMovieDB system. Users will be able to add, edit, and remove cast members with character names and technical crew members with their roles directly from the movie detail view. The system will provide an intuitive interface with autocomplete functionality for person selection and proper validation for all operations.

## Glossary

- **Sistema_Filme**: The movie management subsystem within MyMovieDB
- **Usuario_Autenticado**: Authenticated user with permissions to manage movie cast and crew
- **Elenco**: Cast members (actors) associated with a movie through the Atuacao relationship
- **Equipe_Tecnica**: Technical crew members associated with a movie through the EquipeTecnica relationship
- **Autocomplete_Pessoa**: The person search interface component using existing API endpoint
- **Botao_Adicionar**: Action buttons for adding cast or crew members
- **Botao_Gerenciar**: Small management buttons (edit/remove) next to each person's photo
- **Modal_Adicionar**: Modal dialog for adding new cast or crew relationships
- **Modal_Editar**: Modal dialog for editing existing cast or crew relationships

## Requirements

### Requirement 1

**User Story:** As an authenticated user, I want to add cast members to a movie, so that I can build complete filmography records with character information.

#### Acceptance Criteria

1. WHEN the Usuario_Autenticado views a movie detail page, THE Sistema_Filme SHALL display an "Adicionar Elenco" button in the cast section
2. WHEN the Usuario_Autenticado clicks the "Adicionar Elenco" button, THE Sistema_Filme SHALL display a Modal_Adicionar with person autocomplete and character name fields
3. WHEN the Usuario_Autenticado types in the person field, THE Autocomplete_Pessoa SHALL display matching suggestions using the existing /api/pessoas/search endpoint
4. WHEN the Usuario_Autenticado selects a person and enters a character name, THE Sistema_Filme SHALL validate that the combination is unique for this movie
5. WHEN the Usuario_Autenticado submits valid cast data, THE Sistema_Filme SHALL create an Atuacao relationship and refresh the movie detail view

### Requirement 2

**User Story:** As an authenticated user, I want to add technical crew members to a movie, so that I can document all people involved in the film production.

#### Acceptance Criteria

1. WHEN the Usuario_Autenticado views a movie detail page, THE Sistema_Filme SHALL display an "Adicionar Equipe Técnica" button in the crew section
2. WHEN the Usuario_Autenticado clicks the "Adicionar Equipe Técnica" button, THE Sistema_Filme SHALL display a Modal_Adicionar with person autocomplete and technical role dropdown
3. WHEN the Usuario_Autenticado opens the technical role dropdown, THE Sistema_Filme SHALL populate it with active FuncaoTecnica instances
4. WHEN the Usuario_Autenticado selects a person and technical role, THE Sistema_Filme SHALL validate that the combination is unique for this movie
5. WHEN the Usuario_Autenticado submits valid crew data, THE Sistema_Filme SHALL create an EquipeTecnica relationship and refresh the movie detail view

### Requirement 3

**User Story:** As an authenticated user, I want to edit existing cast member information, so that I can correct character names or update actor details.

#### Acceptance Criteria

1. WHEN the Usuario_Autenticado views a movie with cast members, THE Sistema_Filme SHALL display small Botao_Gerenciar (edit/remove) next to each person's photo
2. WHEN the Usuario_Autenticado clicks the edit button for a cast member, THE Sistema_Filme SHALL display a Modal_Editar pre-populated with current person and character data
3. WHEN the Usuario_Autenticado modifies the character name, THE Sistema_Filme SHALL validate the new character name is not empty and within length limits
4. WHEN the Usuario_Autenticado changes the person selection, THE Sistema_Filme SHALL validate the new person-character combination is unique for this movie
5. WHEN the Usuario_Autenticado submits valid changes, THE Sistema_Filme SHALL update the Atuacao relationship and refresh the movie detail view

### Requirement 4

**User Story:** As an authenticated user, I want to edit existing technical crew member information, so that I can correct roles or update crew assignments.

#### Acceptance Criteria

1. WHEN the Usuario_Autenticado views a movie with crew members, THE Sistema_Filme SHALL display small Botao_Gerenciar (edit/remove) next to each person's photo
2. WHEN the Usuario_Autenticado clicks the edit button for a crew member, THE Sistema_Filme SHALL display a Modal_Editar pre-populated with current person and technical role data
3. WHEN the Usuario_Autenticado changes the technical role selection, THE Sistema_Filme SHALL validate the new person-role combination is unique for this movie
4. WHEN the Usuario_Autenticado changes the person selection, THE Sistema_Filme SHALL validate the new person-role combination is unique for this movie
5. WHEN the Usuario_Autenticado submits valid changes, THE Sistema_Filme SHALL update the EquipeTecnica relationship and refresh the movie detail view

### Requirement 5

**User Story:** As an authenticated user, I want to remove cast and crew members from a movie, so that I can correct mistakes or update outdated information.

#### Acceptance Criteria

1. WHEN the Usuario_Autenticado clicks the remove button for a cast member, THE Sistema_Filme SHALL display a confirmation dialog with person and character details
2. WHEN the Usuario_Autenticado clicks the remove button for a crew member, THE Sistema_Filme SHALL display a confirmation dialog with person and role details
3. WHEN the Usuario_Autenticado confirms removal, THE Sistema_Filme SHALL delete the corresponding Atuacao or EquipeTecnica relationship
4. WHEN the removal is successful, THE Sistema_Filme SHALL refresh the movie detail view and display a success message
5. IF the removal fails due to system constraints, THEN THE Sistema_Filme SHALL display an error message and retain the relationship

### Requirement 6

**User Story:** As an authenticated user, I want proper validation and error handling for cast and crew operations, so that I can successfully manage movie relationships with clear feedback.

#### Acceptance Criteria

1. THE Sistema_Filme SHALL prevent duplicate person-character combinations in the same movie's cast
2. THE Sistema_Filme SHALL prevent duplicate person-role combinations in the same movie's crew
3. THE Sistema_Filme SHALL validate that character names are not empty and do not exceed 100 characters
4. THE Sistema_Filme SHALL require both person selection and role selection for all operations
5. IF validation fails, THEN THE Sistema_Filme SHALL display specific error messages and retain form data
6. THE Sistema_Filme SHALL handle database errors gracefully and display user-friendly error messages

### Requirement 7

**User Story:** As a public user, I want to view cast and crew information without management buttons, so that I can browse movie information without being distracted by editing controls.

#### Acceptance Criteria

1. WHEN a non-authenticated user views a movie detail page, THE Sistema_Filme SHALL display cast and crew information without Botao_Adicionar or Botao_Gerenciar
2. WHEN a non-authenticated user views cast members, THE Sistema_Filme SHALL show person photos, names, and character names as clickable links to person details
3. WHEN a non-authenticated user views crew members, THE Sistema_Filme SHALL show person photos, names, and technical roles as clickable links to person details
4. THE Sistema_Filme SHALL maintain consistent styling and layout for both authenticated and non-authenticated views
5. THE Sistema_Filme SHALL ensure all person links navigate correctly to person detail pages

### Requirement 8

**User Story:** As an authenticated user, I want responsive and intuitive user interface elements, so that I can efficiently manage cast and crew on different devices.

#### Acceptance Criteria

1. THE Sistema_Filme SHALL display Botao_Adicionar prominently in each section header for easy discovery
2. THE Sistema_Filme SHALL position Botao_Gerenciar as small, unobtrusive buttons that appear on hover or focus
3. THE Sistema_Filme SHALL implement Modal_Adicionar and Modal_Editar with proper keyboard navigation and accessibility
4. THE Sistema_Filme SHALL provide visual feedback during autocomplete searches and form submissions
5. THE Sistema_Filme SHALL ensure all interface elements work correctly on mobile and desktop devices
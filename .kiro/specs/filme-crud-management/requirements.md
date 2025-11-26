# Requirements Document

## Introduction

This feature enables comprehensive CRUD (Create, Read, Update, Delete) operations for the Filme entity in the MyMovieDB system. Users will be able to manage movie records including their basic attributes and genre associations through an intuitive web interface with autocomplete functionality for genre selection.

## Glossary

- **Filme_System**: The movie management subsystem within MyMovieDB
- **User**: An authenticated user with permissions to manage movie records
- **Genero_Autocomplete**: The genre search and selection interface component
- **Genre_Badge**: A visual element displaying selected genres with removal capability
- **CRUD_Interface**: The web interface providing Create, Read, Update, Delete operations

## Requirements

### Requirement 1

**User Story:** As a movie database administrator, I want to create new movie records with all essential information, so that I can build a comprehensive movie database.

#### Acceptance Criteria

1. WHEN the User accesses the create movie form, THE Filme_System SHALL display input fields for titulo_original, titulo_portugues, ano_lancamento, lancado, duracao_minutos, sinopse, orcamento_milhares, faturamento_lancamento_milhares, an image that will be stored  at poster_base64, and trailer_youtube
2. WHEN the User submits a valid create form, THE Filme_System SHALL persist the new movie record to the database
3. IF the User submits invalid data, THEN THE Filme_System SHALL display validation error messages and retain the entered data
4. WHEN the User successfully creates a movie, THE Filme_System SHALL redirect to the movie detail view and display a success message

### Requirement 2

**User Story:** As a movie database administrator, I want to update existing movie records, so that I can maintain accurate and current information.

#### Acceptance Criteria

1. WHEN the User accesses the edit movie form, THE Filme_System SHALL pre-populate all fields with current movie data
2. WHEN the User modifies and submits the edit form, THE Filme_System SHALL update the movie record with the new information
3. IF the User submits invalid data during edit, THEN THE Filme_System SHALL display validation error messages and retain the modified data
4. WHEN the User successfully updates a movie, THE Filme_System SHALL redirect to the movie detail view and display a success message


### Requirement 3

**User Story:** As a movie database administrator, I want to delete movie records that are no longer needed, so that I can maintain a clean database.

#### Acceptance Criteria

1. WHEN the User initiates movie deletion, THE Filme_System SHALL display a confirmation dialog with movie details
2. WHEN the User confirms deletion, THE Filme_System SHALL remove the movie record and all associated relationships from the database
3. WHEN the User successfully deletes a movie, THE Filme_System SHALL redirect to the movie list view and display a success message
4. IF deletion fails due to system constraints, THEN THE Filme_System SHALL display an error message and retain the movie record

### Requirement 4

**User Story:** As a movie database administrator, I want to associate genres with movies using an autocomplete interface, so that I can efficiently categorize movies.

#### Acceptance Criteria

1. WHEN the User types in the genre input field, THE Genero_Autocomplete SHALL display matching genre suggestions after 2 characters
2. WHEN the User selects a genre from suggestions, THE Genero_Autocomplete SHALL add the genre as a Genre_Badge to the selected list
3. WHEN the User clicks the remove button on a Genre_Badge, THE Genero_Autocomplete SHALL remove the genre from the selected list
4. WHEN the User submits the form, THE Filme_System SHALL persist all selected genre associations to the database
5. THE Genero_Autocomplete SHALL prevent duplicate genre selection for the same movie

### Requirement 5

**User Story:** As a movie database administrator, I want to navigate between movie management operations seamlessly, so that I can efficiently manage the movie database.

#### Acceptance Criteria

1. WHEN the User is on any movie management page, THE CRUD_Interface SHALL provide navigation links to list, create, edit, and delete operations
2. WHEN the User cancels a create or edit operation, THE CRUD_Interface SHALL return to the previous page without saving changes
3. WHEN the User accesses a non-existent movie record, THE Filme_System SHALL display a 404 error page with navigation options
4. THE CRUD_Interface SHALL maintain consistent styling and layout across all movie management pages

### Requirement 6

**User Story:** As a movie database administrator, I want proper validation of movie data, so that I can ensure data quality and system integrity.

#### Acceptance Criteria

1. THE Filme_System SHALL require titulo_original as a mandatory field with maximum 180 characters
2. THE Filme_System SHALL validate ano_lancamento as a positive integer between 1800 and current year plus 10
3. THE Filme_System SHALL validate duracao_minutos as a positive integer when provided
4. THE Filme_System SHALL validate orcamento_milhares and faturamento_lancamento_milhares as positive decimal values when provided
5. THE Filme_System SHALL validate trailer_youtube as a valid YouTube URL format when provided
6. IF any validation fails, THEN THE Filme_System SHALL display specific error messages for each invalid field
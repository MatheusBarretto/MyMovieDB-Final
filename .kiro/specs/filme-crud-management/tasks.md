# Implementation Plan

- [x] 1. Create form classes for CRUD operations

  - Create FilmeCrudForm with all movie fields and validation
  - Create FilmeDeleteForm for delete confirmation
  - Add custom validators for YouTube URL and year range validation
  - _Requirements: 1.1, 2.1, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 2. Implement FilmeService for business logic

  - [x] 2.1 Create FilmeService class following service pattern

    - Implement create_filme method with transaction handling
    - Implement update_filme method with existing record validation
    - Implement delete_filme method with relationship cleanup
    - Use existing Filme.get_by_id() from BasicRepositoryMixin for retrieval
    - _Requirements: 1.2, 2.2, 3.2_

  - [x] 2.2 Implement genre association management

    - Create update_filme_generos method for managing genre relationships
    - Handle adding and removing genre associations efficiently
    - Ensure proper transaction handling for genre updates
    - _Requirements: 4.4_

  - [x] 2.3 Write unit tests for FilmeService

    - Test create_filme with valid and invalid data
    - Test update_filme with existing and non-existent records
    - Test delete_filme with and without relationships
    - Test genre association management
    - _Requirements: 1.2, 2.2, 3.2, 4.4_

- [x] 3. Create CRUD route handlers

  - [x] 3.1 Implement create_filme route

    - Handle GET request to display create form
    - Handle POST request to process form submission
    - Integrate with FilmeService for data persistence
    - Implement proper error handling and flash messages
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 3.2 Implement edit_filme route

    - Handle GET request to display pre-populated edit form
    - Handle POST request to process form updates
    - Validate filme existence and handle 404 cases
    - Integrate with FilmeService for data updates
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.3 Implement delete_filme route

    - Handle GET request to display delete confirmation
    - Handle POST request to process deletion
    - Implement title confirmation validation
    - Integrate with FilmeService for safe deletion
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]\* 3.4 Write integration tests for CRUD routes
    - Test create workflow with valid and invalid data
    - Test edit workflow with existing and non-existent records
    - Test delete workflow with confirmation validation
    - Test authentication requirements for all routes
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2_

- [x] 4. Create template files for CRUD interface

  - [x] 4.1 Create shared form template components

    - Create \_form_fields.jinja2 with reusable form field macros
    - Implement genre autocomplete widget template
    - Create poster upload widget with preview functionality and croping to 2:3 aspect ratio using existing methods in the ImageProcessingService
    - Add form validation error display components
    - _Requirements: 4.1, 4.2, 4.3, 6.6_

  - [x] 4.2 Create create.jinja2 template

    - Design create form layout using Bootstrap 5
    - Integrate genre autocomplete widget
    - Add form validation and error display
    - Implement navigation and breadcrumb components
    - _Requirements: 1.1, 4.1, 4.2, 5.1, 5.2_

  - [x] 4.3 Create edit.jinja2 template

    - Design edit form layout with pre-populated fields
    - Integrate genre autocomplete with existing selections
    - Add form validation and error display
    - Implement navigation and cancel functionality
    - _Requirements: 2.1, 4.1, 4.2, 5.1, 5.2_

  - [x] 4.4 Create delete.jinja2 template

    - Design delete confirmation interface
    - Display movie details for confirmation
    - Implement title confirmation input
    - Add navigation and cancel options
    - _Requirements: 3.1, 5.1, 5.2_

- [x] 5. Implement frontend JavaScript functionality

  - [x] 5.1 Create GenreAutocomplete JavaScript class

    - Implement autocomplete functionality using existing API
    - Create genre badge display and removal system
    - Handle form submission data synchronization
    - Add debouncing for API calls optimization
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

  - [x] 5.2 Implement form enhancement JavaScript

    - Add client-side validation for immediate feedback
    - Implement poster upload preview functionality
    - Create confirmation dialogs for destructive operations
    - Add progressive enhancement for core functionality
    - _Requirements: 3.1, 5.3, 6.6_

  - [ ]\* 5.3 Write frontend tests for JavaScript components
    - Test genre autocomplete functionality
    - Test form validation and submission
    - Test poster upload and preview features
    - Test confirmation dialog behavior
    - _Requirements: 4.1, 4.2, 4.3, 3.1_

- [x] 6. Enhance existing templates with CRUD navigation






  - [x] 6.1 Update lista.jinja2 template



    - Add "Create New Movie" button to movie list
    - Add edit and delete action buttons to movie cards
    - Implement consistent navigation patterns
    - Ensure responsive design for all screen sizes
    - _Requirements: 5.1, 5.2_



  - [ ] 6.2 Update details.jinja2 template
    - Add edit and delete action buttons to movie details
    - Implement breadcrumb navigation
    - Add links to related CRUD operations
    - Maintain existing functionality for reviews and ratings
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 7. Integrate and test complete CRUD workflow

  - [ ] 7.1 Wire up all components and test integration

    - Register new routes in blueprint configuration
    - Test complete create-edit-delete workflow
    - Verify genre autocomplete integration works correctly
    - Ensure proper error handling across all operations
    - _Requirements: 1.4, 2.4, 3.3, 4.4, 5.1, 5.2_

  - [ ] 7.2 Perform final validation and cleanup

    - Verify all form validations work correctly
    - Test authentication and authorization requirements
    - Ensure consistent UI/UX across all CRUD operations
    - Validate proper database transaction handling
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]\* 7.3 Create end-to-end tests for complete workflow
    - Test full CRUD lifecycle from creation to deletion
    - Test genre association workflow with multiple genres
    - Test error scenarios and recovery paths
    - Test concurrent user operations and data consistency
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4_

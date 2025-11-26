# Implementation Plan

- [x] 1. Create pessoa form definitions

  - Create PessoaForm class with all required fields and validation
  - Implement proper field types, validators, and error messages
  - Add file upload validation for photo field
  - _Requirements: 2.2, 3.2, 5.1, 5.2_

- [x] 2. Extend PessoaService with CRUD operations

  - [x] 2.1 Implement pessoa listing with pagination and search

    - Add listar_pessoas method with pagination support
    - Implement search functionality by person name
    - Add proper query optimization and ordering
    - _Requirements: 1.1, 1.3_

  - [x] 2.2 Implement pessoa creation service method

    - Add criar_pessoa method to handle form data processing
    - Implement photo upload handling using existing foto setter
    - Add validation for required fields and data integrity
    - _Requirements: 2.1, 2.3, 2.4_

  - [x] 2.3 Implement pessoa update service method

    - Add atualizar_pessoa method for editing existing records
    - Handle photo replacement and removal logic
    - Maintain audit trail through AuditMixin

    - _Requirements: 3.1, 3.2, 3.3, 3.5_

  - [x] 2.4 Implement pessoa deletion service method

    - Add deletar_pessoa method with relationship checking

    - Handle cascade deletion of related Ator and EquipeTecnica records
    - Implement proper error handling for constraint violations
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 2.5 Add pessoa uniqueness validation
    - Implement validar_pessoa_unica method
    - Check for duplicate nome + data_nascimento combinations
    - Exclude current record when editing existing pessoa
    - _Requirements: 5.4_

- [x] 3. Create pessoa list template and functionality

  - [x] 3.1 Implement pessoa listing route handler

    - Add pessoa_list route with pagination support
    - Implement search parameter handling
    - Add proper error handling and template rendering
    - _Requirements: 1.1, 1.2_

  - [x] 3.2 Create pessoa list template

    - Design Bootstrap card-based grid layout for person listing
    - Add pagination controls and search form
    - Include person thumbnails and basic information display
    - Add conditional action buttons based on authentication status
    - _Requirements: 1.2, 6.4, 6.5_

- [x] 4. Create pessoa creation functionality

  - [x] 4.1 Implement pessoa creation route handler

    - Add pessoa_create route with GET and POST methods
    - Implement form validation and error handling
    - Add success redirect to person details page
    - Apply @login_required decorator for authentication
    - _Requirements: 2.1, 2.4, 2.5, 6.2_

  - [x] 4.2 Create pessoa creation template

    - Design form layout using Bootstrap styling
    - Implement shared form template for reusability
    - Add proper form validation error display
    - Include photo upload interface with preview
    - _Requirements: 2.1, 5.1, 5.5_

- [x] 5. Create pessoa editing functionality

  - [x] 5.1 Implement pessoa edit route handler

    - Add pessoa_edit route with form pre-population
    - Implement update logic with proper validation
    - Add error handling and success feedback
    - Apply @login_required decorator for authentication
    - _Requirements: 3.1, 3.4, 3.5, 6.2_

  - [x] 5.2 Create pessoa edit template

    - Reuse shared form template with edit mode support
    - Display current photo with replacement option
    - Add form pre-population with existing data
    - Include cancel and save action buttons
    - _Requirements: 3.1, 3.2_

- [x] 6. Create pessoa deletion functionality

  - [x] 6.1 Implement pessoa deletion route handler

    - Add pessoa_delete route with POST method only
    - Implement relationship checking and cascade warnings
    - Add confirmation dialog and success feedback
    - Apply @login_required decorator for authentication
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 6.2_

  - [x] 6.2 Add deletion confirmation to templates

    - Implement JavaScript confirmation dialog
    - Display cascade deletion warnings when applicable
    - Add proper form submission for delete action
    - Include relationship impact information
    - _Requirements: 4.1, 4.3_

- [x] 7. Update existing pessoa details template

  - Add edit and delete action buttons for authenticated users
  - Include navigation links to pessoa listing page
  - Add conditional display based on user authentication status
  - Maintain existing functionality while adding CRUD actions
  - _Requirements: 6.4, 6.5_

- [x] 8. Integrate CRUD routes with existing blueprint

  - Register new routes in pessoa_bp blueprint
  - Update URL patterns and route organization
  - Ensure proper template folder configuration
  - Test route registration and URL generation
  - _Requirements: 6.1, 6.3_

- [ ]\* 9. Create comprehensive test suite

  - [ ]\* 9.1 Write unit tests for PessoaService CRUD methods

    - Test listar_pessoas with various parameters
    - Test criar_pessoa with valid and invalid data
    - Test atualizar_pessoa with different scenarios
    - Test deletar_pessoa with and without relationships
    - _Requirements: All service methods_

  - [ ]\* 9.2 Write integration tests for route handlers

    - Test all CRUD routes with authenticated and unauthenticated users
    - Test form validation and error handling
    - Test photo upload and processing workflows
    - Test pagination and search functionality
    - _Requirements: All route handlers_

  - [ ]\* 9.3 Write form validation tests
    - Test PessoaForm with valid and invalid inputs
    - Test file upload validation and restrictions
    - Test uniqueness validation scenarios
    - Test date validation and logical constraints
    - _Requirements: 5.1, 5.2, 5.4_

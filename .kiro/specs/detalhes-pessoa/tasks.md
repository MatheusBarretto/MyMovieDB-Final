# Implementation Plan

- [x] 1. Create person service layer

  - Implement `PessoaService` class with methods for retrieving person filmography data
  - Create methods to get acting credits and crew credits ordered by release date
  - Follow the same session management pattern as existing `FilmeService`
  - _Requirements: 2.2, 2.3, 3.2, 3.3_

- [x] 2. Create person routes and blueprint

  - Create new `pessoa_bp` Blueprint with person details route
  - Implement route handler for `/pessoa/<uuid:pessoa_id>` endpoint
  - Add proper error handling for invalid person IDs (404 responses)
  - Register the new blueprint in the main application
  - _Requirements: 1.3, 4.1, 4.2_

- [x] 3. Create person details template

  - Design and implement `app/templates/pessoa/detalhes.jinja2` template
  - Display person biographical information (name, birth date, nationality, biography, photo)
  - Create sections for acting credits and crew credits with proper conditional rendering
  - Ensure consistent styling with existing movie detail pages
  - _Requirements: 1.4, 1.5, 2.1, 3.1_

- [x] 4. Update movie details template with person hyperlinks

  - Modify `app/templates/filme/detalhes.jinja2` to add hyperlinks to person names
  - Convert actor names in the cast section to clickable links
  - Convert crew member names in the technical crew section to clickable links
  - Ensure proper URL generation using Flask's `url_for()` function
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 5. Add navigation and breadcrumb support

  - Implement breadcrumb navigation in person details template
  - Add proper page title setting with person's name
  - Ensure smooth navigation flow between movie and person pages
  - _Requirements: 4.3, 4.4_

- [x] 6. Write unit tests for PessoaService


  - Create unit tests for filmography retrieval methods
  - Test edge cases: person with no credits, only acting credits, only crew credits
  - Verify proper data ordering by release date
  - _Requirements: 2.2, 2.3, 3.2, 3.3_

- [x]* 7. Write integration tests for person routes










  - Test route handling with valid and invalid person IDs
  - Verify template rendering with various data scenarios
  - Test hyperlink generation from movie detail pages
  - _Requirements: 1.3, 4.1, 4.2_

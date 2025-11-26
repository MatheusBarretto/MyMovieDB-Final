# Implementation Plan

- [x] 1. Implement key usage analysis functionality

  - Create function to analyze encrypted data in batches and identify which key versions are in use
  - Implement database querying logic to scan encrypted columns efficiently
  - Add progress tracking for large datasets
  - _Requirements: 5.2, 5.3, 5.4_

- [x] 2. Create key cleanup logic and safety validators

  - Implement logic to identify which versions can be safely removed
  - Add validation to prevent removal of active version
  - Create function to ensure minimum number of versions are kept

  - Add checks to preserve versions that are still in use in the data
  - _Requirements: 1.4, 1.5, 2.3, 5.3_

- [x] 3. Implement configuration file backup and restore functionality

  - Create backup mechanism for .env.crypto files before modifications
  - Implement restore functionality for rollback scenarios
  - Add timestamp-based backup naming
  - Include error handling for file operations
  - _Requirements: 6.1, 6.2_

- [x] 4. Build configuration file modification utilities

  - Create function to remove specific key versions from configuration files
  - Implement safe file writing with atomic operations
  - Add validation to ensure configuration integrity after modifications
  - Handle both Flask config and environment variable formats
  - _Requirements: 1.3, 6.3_

- [x] 5. Create the main CLI command interface


  - Implement the `cleanup-keys` command with all required options
  - Add parameter validation for model and column specifications
  - Implement dry-run mode functionality
  - Add user confirmation prompts with --yes flag support
  - _Requirements: 1.1, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1_

- [x] 6. Integrate all components and add comprehensive error handling






  - Wire together analysis, validation, backup, and cleanup components
  - Implement comprehensive error handling with automatic rollback
  - Add detailed logging and audit trail functionality
  - Create progress reporting and statistics display
  - _Requirements: 3.3, 3.4, 6.2, 6.3, 6.4_

- [ ]\* 7. Add comprehensive testing coverage
  - Create unit tests for key usage analysis functions
  - Write tests for safety validation logic
  - Add integration tests with real database scenarios
  - Create tests for backup/restore functionality
  - Test error scenarios and rollback mechanisms
  - _Requirements: All requirements validation_

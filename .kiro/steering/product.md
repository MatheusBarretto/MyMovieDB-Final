# MyMovieDB - Product Overview

MyMovieDB is a comprehensive movie management system with complete user authentication, movie and people database management, user reviews, and interactive navigation between entities.

## Core Features

### User Management & Security
- **Complete authentication system**: Registration, login/logout, email validation, password reset
- **Two-factor authentication (2FA/TOTP)**: Enhanced security with authenticator apps and backup codes
- **Advanced security**: Password complexity validation, JWT tokens, encrypted sensitive data
- **Rich user profiles**: Photo upload with cropping, automatic avatar generation, identicons
- **Personal review history**: View all your movie reviews with posters and quick navigation

### Movie Database
- **Full CRUD operations**: Create, read, update, and delete movie entries
- **Rich movie data**: Titles (original/Portuguese), year, duration, synopsis, budget, revenue, posters, trailers
- **Genre management**: Multiple genre associations with autocomplete interface
- **Cast & crew**: Complete filmography with actors (characters, protagonist markers), technical crew (directors, writers, etc.)
- **Discovery features**: Movie listing with pagination, search/filters, random movie selector

### People Database
- **Comprehensive person profiles**: Biographical data, photos, birth/death dates, birthplace, biography
- **Actor specialization**: Artistic names for actors
- **Career visualization**: Complete filmography as actor and technical crew member
- **Bidirectional navigation**: Links between movies and people for easy exploration
- **Public access with protected editing**: View person data publicly, authentication required for modifications

### Review System
- **User ratings**: 0-10 scale with comments (up to 4096 characters) and recommendation flag
- **Review management**: Create, edit, and delete your own reviews
- **Movie statistics**: Average ratings, review counts, recommendation percentages, rating distribution
- **Smart navigation**: Stay on the same movie page after reviewing
- **Profile integration**: View all your reviews from your profile page

### Data Management
- **TMDB integration**: Seeding system for populating database with movie data
- **Data validation**: Comprehensive validation for all entities (dates, URLs, uniqueness constraints)
- **Relationship protection**: Prevent deletion of entities with dependencies

## Target Users

- **Movie enthusiasts** who want to track and rate their movie collections
- **Database administrators** managing comprehensive movie and people catalogs
- **Security-conscious users** requiring modern 2FA authentication
- **Community members** sharing and discovering movies through reviews

## Key Value Propositions

- **Complete movie ecosystem**: Movies, people, reviews all interconnected
- **Professional security**: 2FA, encryption, JWT tokens, password policies
- **Rich metadata**: Detailed movie and people information with TMDB integration
- **Social features**: Share opinions through reviews, discover via ratings
- **Intuitive navigation**: Seamless exploration between movies, people, and reviews
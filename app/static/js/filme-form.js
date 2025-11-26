// Genre Autocomplete functionality
class GenreAutocomplete {
    constructor() {
        this.searchInput = document.getElementById('genre-search-input');
        this.dropdown = document.getElementById('genre-dropdown');
        this.selectedContainer = document.getElementById('selected-genres');
        this.hiddenField = document.getElementById('generos_selecionados');
        this.selectedGenres = new Map();
        this.debounceTimer = null;

        this.init();
    }

    init() {
        if (!this.searchInput) return;

        this.searchInput.addEventListener('input', (e) => this.handleInput(e));
        this.searchInput.addEventListener('focus', () => this.showDropdown());
        document.addEventListener('click', (e) => this.handleOutsideClick(e));

        // Initialize with existing genres if any
        this.initializeExistingGenres();
    }

    initializeExistingGenres() {
        const existingBadges = this.selectedContainer.querySelectorAll('.genre-badge');
        existingBadges.forEach(badge => {
            const genreId = badge.dataset.genreId;
            const genreName = badge.textContent.trim();
            this.selectedGenres.set(genreId, genreName);
            this.attachRemoveHandler(badge);
        });
        this.updateHiddenField();
    }

    handleInput(e) {
        const query = e.target.value.trim();

        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            if (query.length >= 2) {
                this.searchGenres(query);
            } else {
                this.hideDropdown();
            }
        }, 300);
    }

    async searchGenres(query) {
        try {
            const response = await fetch(`/api/generos/search?q=${encodeURIComponent(query)}&only_active=1`);
            const genres = await response.json();
            this.displayResults(genres);
        } catch (error) {
            console.error('Error searching genres:', error);
            this.hideDropdown();
        }
    }

    displayResults(genres) {
        this.dropdown.innerHTML = '';

        if (genres.length === 0) {
            this.dropdown.innerHTML = '<div class="dropdown-item-text text-muted">Nenhum gênero encontrado</div>';
        } else {
            genres.forEach(genre => {
                if (!this.selectedGenres.has(genre.id.toString())) {
                    const item = document.createElement('button');
                    item.type = 'button';
                    item.className = 'dropdown-item';
                    item.textContent = genre.nome;
                    item.addEventListener('click', () => this.selectGenre(genre));
                    this.dropdown.appendChild(item);
                }
            });
        }

        this.showDropdown();
    }

    selectGenre(genre) {
        this.selectedGenres.set(genre.id.toString(), genre.nome);
        this.addGenreBadge(genre);
        this.updateHiddenField();
        this.searchInput.value = '';
        this.hideDropdown();
    }

    addGenreBadge(genre) {
        const badge = document.createElement('span');
        badge.className = 'badge bg-primary me-2 mb-2 genre-badge';
        badge.dataset.genreId = genre.id;
        badge.innerHTML = `
            ${genre.nome}
            <button type="button" class="btn-close btn-close-white ms-1" aria-label="Remover gênero"></button>
        `;

        this.attachRemoveHandler(badge);
        this.selectedContainer.appendChild(badge);
    }

    attachRemoveHandler(badge) {
        const removeBtn = badge.querySelector('.btn-close');
        removeBtn.addEventListener('click', () => {
            const genreId = badge.dataset.genreId;
            this.selectedGenres.delete(genreId);
            badge.remove();
            this.updateHiddenField();
        });
    }

    updateHiddenField() {
        const genreIds = Array.from(this.selectedGenres.keys());
        this.hiddenField.value = JSON.stringify(genreIds);
    }

    showDropdown() {
        this.dropdown.style.display = 'block';
    }

    hideDropdown() {
        this.dropdown.style.display = 'none';
    }

    handleOutsideClick(e) {
        if (!this.searchInput.contains(e.target) && !this.dropdown.contains(e.target)) {
            this.hideDropdown();
        }
    }
}

// Poster Upload functionality
class PosterUpload {
    constructor() {
        this.fileInput = document.getElementById('poster-upload-input');
        this.previewContainer = document.getElementById('poster-preview-container');
        this.previewImage = document.getElementById('poster-preview');
        this.removeBtn = document.getElementById('remove-poster-btn');

        this.init();
    }

    init() {
        if (!this.fileInput) return;

        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        if (this.removeBtn) {
            this.removeBtn.addEventListener('click', () => this.removePoster());
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            alert('Por favor, selecione apenas arquivos de imagem.');
            this.fileInput.value = '';
            return;
        }

        // Create preview
        const reader = new FileReader();
        reader.onload = (e) => {
            this.previewImage.src = e.target.result;
            this.previewContainer.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }

    removePoster() {
        this.fileInput.value = '';
        this.previewContainer.style.display = 'none';
        this.previewImage.src = '';
    }
}

// Initialize components when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new GenreAutocomplete();
    new PosterUpload();
});

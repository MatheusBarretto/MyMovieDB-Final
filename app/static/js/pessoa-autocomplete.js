// Autocomplete functionality for person search
let currentSearchRequest;

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Search pessoas via API
async function searchPessoas(query, resultsContainer, onSelect) {
    if (query.length < 3) {
        resultsContainer.innerHTML = '';
        resultsContainer.classList.remove('show');
        return;
    }

    // Cancel previous request if exists
    if (currentSearchRequest) {
        currentSearchRequest.abort();
    }

    try {
        currentSearchRequest = new AbortController();
        const response = await fetch(`/api/pessoas/search?q=${encodeURIComponent(query)}&limit=10`, {
            signal: currentSearchRequest.signal
        });
        
        if (!response.ok) {
            throw new Error('Erro na busca');
        }
        
        const pessoas = await response.json();
        displaySearchResults(pessoas, resultsContainer, onSelect);
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Erro ao buscar pessoas:', error);
            resultsContainer.innerHTML = '<div class="dropdown-item text-danger">Erro ao buscar pessoas</div>';
            resultsContainer.classList.add('show');
        }
    }
}

// Display search results
function displaySearchResults(pessoas, resultsContainer, onSelect) {
    if (pessoas.length === 0) {
        resultsContainer.innerHTML = '<div class="dropdown-item text-muted">Nenhuma pessoa encontrada</div>';
    } else {
        resultsContainer.innerHTML = pessoas.map(pessoa => {
            const nomeDisplay = pessoa.nome_artistico ? 
                `${pessoa.nome} (${pessoa.nome_artistico})` : 
                pessoa.nome;
            return `
                <button type="button" class="dropdown-item d-flex align-items-center" onclick="selectPessoa('${pessoa.id}', '${pessoa.nome.replace(/'/g, "\\'")}', '${pessoa.nome_artistico || ''}')">
                    <img src="/pessoa/${pessoa.id}/foto" alt="${pessoa.nome}" class="rounded me-2" style="width: 32px; height: 32px; object-fit: cover;">
                    <span>${nomeDisplay}</span>
                </button>
            `;
        }).join('');
    }
    resultsContainer.classList.add('show');
}

// Select a person
function selectPessoa(id, nome, nomeArtistico) {
    const pessoaIdField = document.getElementById('pessoa_id');
    const searchInput = document.getElementById('pessoa_search');
    const resultsContainer = document.getElementById('pessoa_search_results');
    const selectedDiv = document.getElementById('selected_pessoa');
    
    if (pessoaIdField) pessoaIdField.value = id;
    if (searchInput) searchInput.value = nomeArtistico || nome;
    if (resultsContainer) resultsContainer.classList.remove('show');
    
    // Show selected person
    if (selectedDiv) {
        const foto = selectedDiv.querySelector('.selected-pessoa-foto');
        const nomeSpan = selectedDiv.querySelector('.selected-pessoa-nome');
        
        if (foto) {
            foto.src = `/pessoa/${id}/foto`;
            foto.alt = nome;
        }
        if (nomeSpan) {
            nomeSpan.textContent = nomeArtistico ? `${nome} (${nomeArtistico})` : nome;
        }
        selectedDiv.style.display = 'block';
    }
}

// Clear person selection
function clearPessoaSelection() {
    const pessoaIdField = document.getElementById('pessoa_id');
    const searchInput = document.getElementById('pessoa_search');
    const resultsContainer = document.getElementById('pessoa_search_results');
    const selectedDiv = document.getElementById('selected_pessoa');
    
    if (pessoaIdField) pessoaIdField.value = '';
    if (searchInput) searchInput.value = '';
    if (resultsContainer) resultsContainer.classList.remove('show');
    if (selectedDiv) selectedDiv.style.display = 'none';
}

// Initialize autocomplete
function initializePessoaAutocomplete() {
    const searchInput = document.getElementById('pessoa_search');
    const resultsContainer = document.getElementById('pessoa_search_results');
    
    if (!searchInput || !resultsContainer) return;

    const debouncedSearch = debounce((query) => {
        searchPessoas(query, resultsContainer, selectPessoa);
    }, 300);

    searchInput.addEventListener('input', (e) => {
        debouncedSearch(e.target.value);
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !resultsContainer.contains(e.target)) {
            resultsContainer.classList.remove('show');
        }
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializePessoaAutocomplete();
});
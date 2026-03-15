// Basic JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('A_Media application loaded successfully!');

    const grid = document.getElementById('product-grid');
    if (!grid) {
        return;
    }

    const emptyState = document.getElementById('empty-state');
    const searchInput = document.getElementById('filter-search');
    const categorySelect = document.getElementById('filter-category');
    const priceSelect = document.getElementById('filter-price');
    const picksCheckbox = document.getElementById('filter-picks');
    const resetButton = document.getElementById('filter-reset');

    const categoryEntries = getCategoryEntries();
    const orderedCategories = categoryEntries.map((entry) => entry.category);

    orderedCategories.forEach((category) => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        categorySelect.appendChild(option);
    });

    function matchesPrice(price, range) {
        if (range === 'all') {
            return true;
        }

        if (typeof price !== 'number') {
            return false;
        }

        if (range === '0-50') {
            return price <= 50;
        }
        if (range === '50-100') {
            return price > 50 && price <= 100;
        }
        if (range === '100-200') {
            return price > 100 && price <= 200;
        }

        return price > 200;
    }

    function applyFilters() {
        const query = (searchInput.value || '').trim().toLowerCase();
        const category = categorySelect.value;
        const priceRange = priceSelect.value;
        const picksOnly = picksCheckbox.checked;

        const filteredProducts = products.filter((product) => {
            const matchesSearch = !query || product.name.toLowerCase().includes(query);
            const matchesCategory = category === 'all' || product.category === category;
            const matchesPick = !picksOnly || product.pick;
            const matchesPriceRange = matchesPrice(product.price, priceRange);

            return matchesSearch && matchesCategory && matchesPick && matchesPriceRange;
        });

        const grouped = orderedCategories
            .map((currentCategory) => ({
                category: currentCategory,
                products: filteredProducts.filter((product) => product.category === currentCategory),
            }))
            .filter((entry) => entry.products.length > 0);

        renderCategorySections(grouped, grid);

        if (emptyState) {
            emptyState.hidden = grouped.length > 0;
        }
    }

    [searchInput, categorySelect, priceSelect, picksCheckbox].forEach((element) => {
        element.addEventListener('input', applyFilters);
        element.addEventListener('change', applyFilters);
    });

    resetButton.addEventListener('click', () => {
        searchInput.value = '';
        categorySelect.value = 'all';
        priceSelect.value = 'all';
        picksCheckbox.checked = false;
        applyFilters();
    });

    applyFilters();
});
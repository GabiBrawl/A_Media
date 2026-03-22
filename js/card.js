const OVERLAY_SVG_PATH = 'M-2 0C23.4125 9.49346 54.6816 15.0937 88.4941 15.0938C121.43 15.0938 151.953 9.7799 177 0.730469V88.417H-2V0Z';
const CARD_IMAGE_FALLBACK = 'assets/temp.jpg';

function formatPrice(price) {
    if (price === null || price === undefined || price === '') {
        return 'TBA';
    }

    return `$${Number(price).toLocaleString()}`;
}

function resolveImagePath(imagePath) {
    if (!imagePath) {
        return CARD_IMAGE_FALLBACK;
    }

    if (/^(https?:|data:|\/)/i.test(imagePath)) {
        return imagePath;
    }

    return encodeURI(imagePath);
}

function flattenGearData(data) {
    if (!data || typeof data !== 'object') {
        return [];
    }

    let nextId = 1;

    return Object.entries(data).flatMap(([category, items]) =>
        items.map((item) => ({
            id: nextId++,
            category,
            name: item.name,
            price: item.price,
            url: item.url,
            pick: Boolean(item.pick),
            image: resolveImagePath(item.image),
        }))
    );
}

const products = typeof gearData !== 'undefined'
    ? flattenGearData(gearData)
    : [];

function getCategoryEntries() {
    if (!gearData || typeof gearData !== 'object') {
        return [];
    }

    return Object.entries(gearData).map(([category, items]) => ({
        category,
        products: items.map((item) => products.find((product) => (
            product.category === category
            && product.name === item.name
            && product.url === item.url
        ))).filter(Boolean),
    })).filter((entry) => entry.products.length > 0);
}

function getFeaturedProducts(limit = 12) {
    const picks = products.filter((product) => product.pick);
    const others = products.filter((product) => !product.pick);

    return [...picks, ...others].slice(0, limit);
}

function getProductById(productId) {
    return products.find((product) => product.id === productId) || products[0] || null;
}

function openProductUrl(product) {
    if (!product || !product.url) {
        return;
    }

    window.open(product.url, '_blank', 'noopener,noreferrer');
}

function shareProduct(product) {
    if (!product || !product.url) {
        return;
    }

    if (navigator.share) {
        navigator.share({
            title: product.name,
            url: product.url,
        }).catch(() => {});
        return;
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(product.url).catch(() => {});
    }
}

/**
 * Builds and returns a .product-card DOM element for a given product object.
 * @param {Object} product
 * @param {number} product.id
 * @param {string} product.name
 * @param {number|null} product.price
 * @param {string} product.image
 * @param {string} product.url
 * @param {boolean} product.pick
 * @param {string} product.category
 * @returns {HTMLElement}
 */
function createProductCard(product) {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.dataset.productId = product.id;
    card.dataset.category = product.category;

    const inner = document.createElement('div');
    inner.className = 'product-inner';

    // Optional badge
    if (product.pick) {
        card.classList.add('is-pick');
    }

    // Image container
    const imageContainer = document.createElement('div');
    imageContainer.className = 'image-container';

    const img = document.createElement('img');
    img.src = product.image;
    img.alt = product.name;
    img.className = 'product-image';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
        if (!img.src.endsWith(CARD_IMAGE_FALLBACK)) {
            img.src = CARD_IMAGE_FALLBACK;
        }
    }, { once: true });
    imageContainer.appendChild(img);

    // SVG wave overlay
    const overlay = document.createElement('div');
    overlay.className = 'overlay';

    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'overlay-shape');
    svg.setAttribute('viewBox', '0 0 177 89');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(svgNS, 'path');
    path.setAttribute('fill-rule', 'evenodd');
    path.setAttribute('clip-rule', 'evenodd');
    path.setAttribute('d', OVERLAY_SVG_PATH);
    svg.appendChild(path);
    overlay.appendChild(svg);

    // Overlay content
    const overlayContent = document.createElement('div');
    overlayContent.className = 'overlay-content';

    const meta = document.createElement('div');
    meta.className = 'product-meta';

    const title = document.createElement('h3');
    title.className = 'product-title';
    title.textContent = product.name;
    title.title = product.name;

    const price = document.createElement('div');
    price.className = 'product-price';
    price.textContent = formatPrice(product.price);

    meta.appendChild(title);
    meta.appendChild(price);

    const buttons = document.createElement('div');
    buttons.className = 'buttons';

    const addToCart = document.createElement('button');
    addToCart.className = 'add-to-cart';
    addToCart.textContent = 'View Product';
    addToCart.addEventListener('click', (e) => {
        e.stopPropagation();
        openProductUrl(product);
    });

    const wishlist = document.createElement('button');
    wishlist.className = 'wishlist';
    wishlist.setAttribute('aria-label', `Save ${product.name}`);
    wishlist.innerHTML = '&#9825;';
    wishlist.addEventListener('click', (e) => {
        e.stopPropagation();
        console.log(`[Save] Product #${product.id}: ${product.name}`);
    });

    const share = document.createElement('button');
    share.className = 'share';
    share.setAttribute('aria-label', `Share ${product.name}`);
    share.innerHTML = '&#8599;';
    share.addEventListener('click', (e) => {
        e.stopPropagation();
        shareProduct(product);
    });

    buttons.appendChild(addToCart);
    buttons.appendChild(wishlist);
    buttons.appendChild(share);

    overlayContent.appendChild(meta);
    overlayContent.appendChild(buttons);
    overlay.appendChild(overlayContent);
    imageContainer.appendChild(overlay);
    inner.appendChild(imageContainer);
    inner.addEventListener('click', () => openProductUrl(product));
    card.appendChild(inner);

    return card;
}

/**
 * Renders a list of product cards into the given container element.
 * @param {Object[]} productList
 * @param {HTMLElement} container
 */
function renderCards(productList, container) {
    container.innerHTML = '';
    productList.forEach((product) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'card-wrapper';
        if (product.pick) {
            wrapper.classList.add('has-pick');
        }
        wrapper.appendChild(createProductCard(product));
        container.appendChild(wrapper);
    });
}

/**
 * Renders grouped product cards by category into the given container element.
 * @param {{ category: string, products: Object[] }[]} categoryEntries
 * @param {HTMLElement} container
 */
function renderCategorySections(categoryEntries, container) {
    container.innerHTML = '';

    categoryEntries.forEach((entry) => {
        const section = document.createElement('section');
        section.className = 'category-section';

        const header = document.createElement('div');
        header.className = 'category-header';

        const title = document.createElement('h3');
        title.className = 'category-title';
        title.textContent = entry.category;

        const count = document.createElement('span');
        count.className = 'category-count';
        count.textContent = `${entry.products.length} item${entry.products.length === 1 ? '' : 's'}`;

        const row = document.createElement('div');
        row.className = 'cards-row';

        header.appendChild(title);
        header.appendChild(count);
        section.appendChild(header);

        entry.products.forEach((product) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'card-wrapper';
            if (product.pick) {
                wrapper.classList.add('has-pick');
            }
            wrapper.appendChild(createProductCard(product));
            row.appendChild(wrapper);
        });

        section.appendChild(row);
        container.appendChild(section);
    });
}

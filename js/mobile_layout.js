function initializeMobileLayout() {
    const sidebar = document.querySelector('.sidebar');
    const shell = document.querySelector('.sidebar-shell');
    const anchor = document.getElementById('sidebar-mobile-anchor');
    const workspace = document.querySelector('.sidebar-workspace');
    const footer = document.querySelector('.sidebar-foot');
    const mobileQuoteSlot = document.getElementById('mobile-quote-slot');

    const mobileFilters = document.querySelector('.mobile-filters');
    const toggleButton = document.getElementById('mobile-filters-toggle');
    const mobilePanel = document.getElementById('mobile-filters-panel');

    if (!shell || !anchor || !workspace || !footer || !mobileQuoteSlot || !mobileFilters || !toggleButton || !mobilePanel) {
        return;
    }

    const mediaQuery = window.matchMedia('(max-width: 768px)');

    function closePanel() {
        mobileFilters.classList.remove('is-open');
        toggleButton.setAttribute('aria-expanded', 'false');
        mobilePanel.hidden = true;
    }

    function openPanel() {
        mobileFilters.classList.add('is-open');
        toggleButton.setAttribute('aria-expanded', 'true');
        mobilePanel.hidden = false;
    }

    function moveToMobilePanel() {
        if (!mobilePanel.contains(workspace)) {
            mobilePanel.appendChild(workspace);
        }

        if (!mobileQuoteSlot.contains(footer)) {
            mobileQuoteSlot.appendChild(footer);
        }

        closePanel();
    }

    function moveBackToSidebar() {
        if (!shell.contains(workspace)) {
            shell.insertBefore(workspace, anchor.nextSibling);
        }

        if (!shell.contains(footer)) {
            shell.appendChild(footer);
        }

        closePanel();
    }

    function syncLayout(event) {
        if (event.matches) {
            moveToMobilePanel();
            if (sidebar) {
                sidebar.setAttribute('aria-hidden', 'true');
            }
            return;
        }

        moveBackToSidebar();
        if (sidebar) {
            sidebar.removeAttribute('aria-hidden');
        }
    }

    toggleButton.addEventListener('click', () => {
        const isOpen = toggleButton.getAttribute('aria-expanded') === 'true';
        if (isOpen) {
            closePanel();
            return;
        }

        openPanel();
    });

    syncLayout(mediaQuery);

    if (typeof mediaQuery.addEventListener === 'function') {
        mediaQuery.addEventListener('change', syncLayout);
    } else if (typeof mediaQuery.addListener === 'function') {
        mediaQuery.addListener(syncLayout);
    }
}

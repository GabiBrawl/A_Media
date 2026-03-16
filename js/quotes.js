const sidebarQuotes = [
    'stolen btw',
    'where are my fucking cables!!!!!',
    'tell usps to deliver them'
];

function renderRandomSidebarQuote() {
    const sidebarQuote = document.getElementById('sidebar-quote');
    if (!sidebarQuote) {
        return;
    }

    if (sidebarQuotes.length > 0) {
        const randomIndex = Math.floor(Math.random() * sidebarQuotes.length);
        sidebarQuote.textContent = '“' + sidebarQuotes[randomIndex] + '”';
        return;
    }

    sidebarQuote.textContent = 'Add quotes to the sidebarQuotes variable in js/quotes.js.';
}

// Site-wide settings. Change values here instead of hunting through pages.
window.WCS_CONFIG = {
    // Where searches go. {q} is replaced with the URL-encoded search terms.
    // When System1 (or another partner) approves you, paste their search URL here.
    // The browser extension and the "add to browser" search engine both go through
    // search.html, so this single line switches every search entry point at once.
    searchUrl: 'https://www.google.com/search?q={q}',

    // Link to a charity's Every.org page. {ein} is the 9-digit IRS EIN (no dash).
    charityUrl: 'https://www.every.org/{ein}',

    // The five donation pools. ids must match scripts/build_charities.py.
    pools: [
        { id: 'humanitarian', emoji: '🌍', title: 'Humanitarian Aid' },
        { id: 'nature',       emoji: '🌳', title: 'Environment & Nature' },
        { id: 'health',       emoji: '🔬', title: 'Medical & Health' },
        { id: 'education',    emoji: '📚', title: 'Education & Youth' },
        { id: 'community',    emoji: '🏘️', title: 'Community Action' }
    ]
};

window.WCS_CONFIG.buildSearchUrl = function (query) {
    return window.WCS_CONFIG.searchUrl.replace('{q}', encodeURIComponent(query));
};

window.WCS_CONFIG.buildCharityUrl = function (ein) {
    return window.WCS_CONFIG.charityUrl.replace('{ein}', encodeURIComponent(ein));
};

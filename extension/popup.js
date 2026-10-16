const SITE = 'https://worldcharitysearchengine.github.io/WorldCharitySearch/';
const api = globalThis.browser || globalThis.chrome;

function openSite(path) {
    api.tabs.create({ url: SITE + path });
    window.close();
}

document.getElementById('search-form').addEventListener('submit', event => {
    event.preventDefault();
    const query = document.getElementById('query').value.trim();
    if (query) openSite('search.html?q=' + encodeURIComponent(query));
});

document.querySelectorAll('nav a').forEach(link => {
    link.addEventListener('click', event => {
        event.preventDefault();
        openSite(link.dataset.path);
    });
});

// Published totals; the popup keeps its defaults if the site can't be reached.
const getJSON = path => fetch(SITE + path, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null);

getJSON('donations.json').then(data => {
    if (!data || !data.pools) return;
    const total = data.pools.reduce((sum, p) => sum + (Number(p.donated) || 0), 0);
    document.getElementById('total').textContent =
        total.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
});

getJSON('charities.json').then(data => {
    if (data && data.charities) {
        document.getElementById('charity-count').textContent =
            `split evenly across ${data.charities.length.toLocaleString()} nonprofits`;
    }
});

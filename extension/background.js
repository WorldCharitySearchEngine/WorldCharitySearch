// Show a short welcome page the first time the extension is installed.
const SITE = 'https://worldcharitysearchengine.github.io/WorldCharitySearch/';
const api = globalThis.browser || globalThis.chrome;

api.runtime.onInstalled.addListener(details => {
    if (details.reason === 'install') {
        api.tabs.create({ url: SITE + 'extension.html?installed=1' });
    }
});

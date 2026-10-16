# World Charity Search

A search engine that donates 90% of its net profits to nonprofits on [Every.org](https://www.every.org), split evenly across five charity pools and then evenly across the charities in each pool.

The site is plain HTML, CSS and JavaScript hosted on GitHub Pages; there is no server or build step.

## What's here

| Path | What it is |
| --- | --- |
| `index.html` | Homepage: search box, donation totals, the five pools |
| `charities.html` | Searchable directory of every charity in the pools |
| `extension.html` | Browser extension page, plus manual "set as default search" steps |
| `transparency.html` | Monthly payouts, what "net profits" means, how charities are chosen |
| `privacy.html`, `terms.html` | Privacy policy and terms of use (have a lawyer review before launch) |
| `search.html` | Every search goes through here and is forwarded to the search partner |
| `config.js` | Search partner URL, charity link format, pool names |
| `donations.json` | Published donation totals and monthly payouts (edit by hand) |
| `charities.json` | The charity list, generated from IRS data (don't edit by hand) |
| `extension/` | Chrome / Edge / Firefox extension |
| `scripts/` | Charity list builder, payout planner, extension packager, tests |

## Common tasks

### Switch search to System1 (or another partner)

Put the partner's search URL in `config.js`, using `{q}` where the search terms go:

```js
searchUrl: 'https://partner.example.com/search?q={q}&id=YOUR_ID',
```

The homepage, the browser extension and the browser search bar all go through `search.html`, so this one line switches all of them, and you never need to republish the extension.

### Refresh the charity list

The **Build charity list** GitHub Action downloads the IRS [Exempt Organizations Business Master File](https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf) on the 2nd of every month and commits an updated `charities.json`. Run it any time from the Actions tab.

It keeps active, tax-deductible 501(c)(3) public charities that filed in the last 3 years with at least $250,000 in revenue, sorts them into pools by NTEE category, and keeps the 500 largest per pool (2,500 total). Hospitals, universities, health plans, donor-advised funds and similar fee-funded organizations are excluded. Tune `PER_POOL`, `MIN_REVENUE` and the exclusions at the top of `scripts/build_charities.py`.

### Pay out a month

1. Work out net profit and take 90% of it.
2. Run the planner, which splits it evenly and writes one row per gift:
   ```sh
   python scripts/payout.py 4500 --month 2026-11 --out payout-2026-11.csv
   ```
   If an even split would make gifts smaller than `--min-gift` (default $10), it gives that month's money to a rotating group of charities, so every charity gets its turn over the following months.
3. Make the donations on Every.org. With hundreds of gifts a month, ask Every.org about bulk or business giving.
4. Update `donations.json`: add each pool's amount to its `donated` total, set `lastUpdated`, and add a row to `payouts`:
   ```json
   { "month": "2026-11", "netProfit": 5000, "donated": 4500, "charities": 450, "receiptsUrl": "https://..." }
   ```

### Publish the browser extension

```sh
scripts/package_extension.sh   # -> dist/world-charity-search-1.0.0.zip
```

Upload the zip to the [Chrome Web Store](https://chrome.google.com/webstore/devconsole) ($5 one-time fee), [Firefox Add-ons](https://addons.mozilla.org/developers/) and [Edge Add-ons](https://partner.microsoft.com/dashboard/microsoftedge). Bump `version` in `extension/manifest.json` for each new upload. Then replace the "coming soon" labels on `extension.html` with the store links.

To try it locally in Chrome: open `chrome://extensions`, turn on Developer mode, click **Load unpacked**, and choose the `extension` folder.

### Moving to your own domain

The site URL `https://worldcharitysearchengine.github.io/WorldCharitySearch/` appears in `opensearch.xml`, `extension/manifest.json`, `extension/background.js` and `extension/popup.js`. Replace it in all four when you connect a custom domain, and publish a new extension version.

## Tests

```sh
python -m unittest discover scripts
```

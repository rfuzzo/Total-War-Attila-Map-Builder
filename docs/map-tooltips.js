(function () {
    // Ensure DOM is ready (script is deferred, but double-guard for safety)
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        const wrap = document.getElementById('wrap');
        const tip = document.getElementById('tip');
        if (!wrap || !tip) return;

        const provinces = Array.from(document.querySelectorAll('path.province'));
        if (!provinces.length) return;

        const cultureSelect = document.getElementById('culture');

        const esc = (s) => String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');

        // Localization helpers (safe fallbacks when loc data is missing)
        function locRegion(id, loc) {
            if (loc && loc.regions && Object.prototype.hasOwnProperty.call(loc.regions, id)) {
                return String(loc.regions[id]);
            }
            return id;
        }

        function locCulture(key, loc) {
            if (loc && loc.factions && Object.prototype.hasOwnProperty.call(loc.factions, key)) {
                return String(loc.factions[key]);
            }
            // Fallback: strip common prefix and prettify
            return key;
        }

        function locUnit(key, loc) {
            if (loc && loc.units && Object.prototype.hasOwnProperty.call(loc.units, key)) {
                return String(loc.units[key]);
            }
            return key;
        }

        function buildTooltipHTML(provinceId, provinceData, locData, filterCulture) {
            const title = locRegion(provinceId, locData);

            // New schema: provinceData is an object of culture -> [units]
            const hasData = provinceData && typeof provinceData === 'object' && Object.keys(provinceData).length > 0;
            if (!hasData) {
                return (
                    '<div>' +
                    '<strong>' + esc(title) + '</strong>' +
                    '<div style="opacity:.8;margin-top:.25rem">No data</div>' +
                    '</div>'
                );
            }

            const active = (filterCulture && String(filterCulture).length > 0) ? String(filterCulture) : '';
            if (active) {
                const label = locCulture(active, locData);
                const units = provinceData ? provinceData[active] : undefined;
                if (Array.isArray(units) && units.length > 0) {
                    const unitItems = units.map((u) => '<li>' + esc(locUnit(u, locData)) + '</li>').join('');
                    return (
                        '<div style="font-weight:700;margin-bottom:.25rem">' + esc(title) + '</div>' +
                        '<div style="margin:.35rem 0 .2rem;font-weight:600">' + esc(label) + '</div>' +
                        '<ul style="margin:.1rem 0 .4rem .9rem;padding:0;list-style:disc">' + unitItems + '</ul>'
                    );
                }
                return (
                    '<div style="font-weight:700;margin-bottom:.25rem">' + esc(title) + '</div>' +
                    '<div style="margin:.35rem 0 .2rem;font-weight:600">' + esc(label) + '</div>' +
                    '<div style="opacity:.8;margin-left:.9rem">(none)</div>'
                );
            }

            const sections = [];
            // Sort sections by localized culture label for readability
            const entries = Object.entries(provinceData).sort(([a], [b]) => {
                const la = locCulture(a, locData);
                const lb = locCulture(b, locData);
                return la.localeCompare(lb);
            });
            for (const [culture, units] of entries) {
                const cultureLabel = locCulture(culture, locData);
                if (Array.isArray(units) && units.length > 0) {
                    const unitItems = units.map((u) => '<li>' + esc(locUnit(u, locData)) + '</li>').join('');
                    sections.push(
                        '<div style="margin:.35rem 0 .2rem;font-weight:600">' + esc(cultureLabel) + '</div>' +
                        '<ul style="margin:.1rem 0 .4rem .9rem;padding:0;list-style:disc">' + unitItems + '</ul>'
                    );
                } else {
                    sections.push(
                        '<div style="margin:.35rem 0 .2rem;font-weight:600">' + esc(cultureLabel) + '</div>' +
                        '<div style="opacity:.8;margin-left:.9rem">(none)</div>'
                    );
                }
            }

            return '<div style="font-weight:700;margin-bottom:.25rem">' + esc(title) + '</div>' + sections.join('');
        }

        function positionTip(evt) {
            const rect = wrap.getBoundingClientRect();
            const x = evt.clientX - rect.left + 10; // small offset
            const y = evt.clientY - rect.top + 10;

            tip.style.left = x + 'px';
            tip.style.top = y + 'px';

            // Optional: keep inside bounds if possible
            const tipRect = tip.getBoundingClientRect();
            const overRight = tipRect.right - rect.right;
            const overBottom = tipRect.bottom - rect.bottom;
            if (overRight > 0) tip.style.left = Math.max(0, x - overRight - 12) + 'px';
            if (overBottom > 0) tip.style.top = Math.max(0, y - overBottom - 12) + 'px';
        }

        function attachHandlers(regionData, hasData, locData) {
            provinces.forEach((path) => {
                const pid = path.id || '';
                const pdata = hasData ? regionData[pid] : undefined;

                path.addEventListener('pointerenter', (evt) => {
                    const html = buildTooltipHTML(pid, pdata, locData, (cultureSelect && cultureSelect.value) || '');
                    tip.innerHTML = html;
                    tip.style.display = 'block';
                    positionTip(evt);
                });

                path.addEventListener('pointermove', (evt) => {
                    if (tip.style.display !== 'block') {
                        tip.innerHTML = buildTooltipHTML(pid, pdata, locData, (cultureSelect && cultureSelect.value) || '');
                        tip.style.display = 'block';
                    }
                    positionTip(evt);
                });

                path.addEventListener('pointerleave', () => {
                    tip.style.display = 'none';
                });
            });
        }

        // Load region and localization data, then attach
        const regionFetch = fetch('region_data.json', { cache: 'no-store' })
            .then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))));

        const locFetch = fetch('loc_data.json', { cache: 'no-store' })
            .then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
            .catch((err) => {
                console.warn('loc_data.json could not be loaded:', err);
                return null; // proceed with fallbacks
            });

        const culturesFetch = fetch('cultures_list.json', { cache: 'no-store' })
            .then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
            .catch((err) => {
                console.warn('cultures_list.json could not be loaded:', err);
                return [];
            });

        function populateCultureSelect(list, locData) {
            if (!cultureSelect) return;
            // Clear existing (keep the first "All" option)
            while (cultureSelect.options.length > 1) cultureSelect.remove(1);
            const opts = Array.isArray(list) ? list.slice() : [];
            opts.sort((a, b) => locCulture(a, locData).localeCompare(locCulture(b, locData)));
            for (const key of opts) {
                const opt = document.createElement('option');
                opt.value = key;
                opt.textContent = locCulture(key, locData);
                cultureSelect.appendChild(opt);
            }
        }

        function setupCultureFilter(regionData, hasData, locData, cultureList) {
            if (!cultureSelect) return;

            // Fallback: if list is empty, derive from dataset
            let options = Array.isArray(cultureList) && cultureList.length ? cultureList : [];
            if (!options.length && hasData) {
                const s = new Set();
                for (const val of Object.values(regionData)) {
                    if (val && typeof val === 'object') {
                        for (const k of Object.keys(val)) s.add(k);
                    }
                }
                options = Array.from(s);
            }
            populateCultureSelect(options, locData);

            function applyFilter(value) {
                const sel = String(value || '');
                const enable = sel.length > 0;
                provinces.forEach((path) => {
                    const pid = path.id || '';
                    const pdata = hasData ? regionData[pid] : undefined;
                    const match = enable && pdata && Object.prototype.hasOwnProperty.call(pdata, sel);
                    path.classList.toggle('is-highlight', !!match);
                });
            }

            cultureSelect.addEventListener('change', () => applyFilter(cultureSelect.value));
            applyFilter('');
        }

        Promise.all([regionFetch, locFetch, culturesFetch])
            .then(([regionData, locData, cultureList]) => {
                attachHandlers(regionData, true, locData);
                setupCultureFilter(regionData, true, locData, cultureList);
            })
            .catch((err) => {
                console.warn('region_data.json could not be loaded:', err);
                attachHandlers({}, false, null);
                setupCultureFilter({}, false, null, []);
            });
    }
})();

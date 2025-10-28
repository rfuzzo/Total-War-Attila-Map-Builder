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

        function locSubculture(key, loc) {
            if (loc && loc.cultures && Object.prototype.hasOwnProperty.call(loc.cultures, key)) {
                return String(loc.cultures[key]);
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

        function buildTooltipHTML(provinceId, provinceData, locData) {
            const title = locRegion(provinceId, locData);

            // New schema: provinceData is an object of subculture -> [units]
            const hasData = provinceData && typeof provinceData === 'object' && Object.keys(provinceData).length > 0;
            if (!hasData) {
                return (
                    '<div>' +
                    '<strong>' + esc(title) + '</strong>' +
                    '<div style="opacity:.8;margin-top:.25rem">No data</div>' +
                    '</div>'
                );
            }

            const sections = [];
            // Sort sections by localized subculture label for readability
            const entries = Object.entries(provinceData).sort(([a], [b]) => {
                const la = locSubculture(a, locData);
                const lb = locSubculture(b, locData);
                return la.localeCompare(lb);
            });
            for (const [subcult, units] of entries) {
                const subcultLabel = locSubculture(subcult, locData);
                if (Array.isArray(units) && units.length > 0) {
                    const unitItems = units.map((u) => '<li>' + esc(locUnit(u, locData)) + '</li>').join('');
                    sections.push(
                        '<div style="margin:.35rem 0 .2rem;font-weight:600">' + esc(subcultLabel) + '</div>' +
                        '<ul style="margin:.1rem 0 .4rem .9rem;padding:0;list-style:disc">' + unitItems + '</ul>'
                    );
                } else {
                    sections.push(
                        '<div style="margin:.35rem 0 .2rem;font-weight:600">' + esc(subcultLabel) + '</div>' +
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
                    const html = buildTooltipHTML(pid, pdata, locData);
                    tip.innerHTML = html;
                    tip.style.display = 'block';
                    positionTip(evt);
                });

                path.addEventListener('pointermove', (evt) => {
                    if (tip.style.display !== 'block') {
                        tip.innerHTML = buildTooltipHTML(pid, pdata, locData);
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

        Promise.all([regionFetch, locFetch])
            .then(([regionData, locData]) => {
                attachHandlers(regionData, true, locData);
            })
            .catch((err) => {
                console.warn('region_data.json could not be loaded:', err);
                attachHandlers({}, false, null);
            });
    }
})();

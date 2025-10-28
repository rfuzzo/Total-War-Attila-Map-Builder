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

        const pretty = (s) => String(s || '')
            .replace(/_/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();

        const esc = (s) => String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');

        function buildTooltipHTML(provinceId, provinceData) {
            const title = pretty(provinceId);
            if (!provinceData || !provinceData.resources) {
                return (
                    '<div>' +
                    '<strong>' + esc(title) + '</strong>' +
                    '<div style="opacity:.8;margin-top:.25rem">No data</div>' +
                    '</div>'
                );
            }

            const sections = [];
            for (const [resource, units] of Object.entries(provinceData.resources)) {
                const resourceName = pretty(resource);
                if (Array.isArray(units) && units.length > 0) {
                    const unitItems = units.map((u) => '<li>' + esc(pretty(u)) + '</li>').join('');
                    sections.push(
                        '<div style="margin:.35rem 0 .2rem;font-weight:600">' + esc(resourceName) + '</div>' +
                        '<ul style="margin:.1rem 0 .4rem .9rem;padding:0;list-style:disc">' + unitItems + '</ul>'
                    );
                } else {
                    sections.push(
                        '<div style="margin:.35rem 0 .2rem;font-weight:600">' + esc(resourceName) + '</div>' +
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

        function attachHandlers(regionData, hasData) {
            provinces.forEach((path) => {
                const pid = path.id || '';
                const pdata = hasData ? regionData[pid] : undefined;

                path.addEventListener('pointerenter', (evt) => {
                    const html = buildTooltipHTML(pid, pdata);
                    tip.innerHTML = html;
                    tip.style.display = 'block';
                    positionTip(evt);
                });

                path.addEventListener('pointermove', (evt) => {
                    if (tip.style.display !== 'block') {
                        tip.innerHTML = buildTooltipHTML(pid, pdata);
                        tip.style.display = 'block';
                    }
                    positionTip(evt);
                });

                path.addEventListener('pointerleave', () => {
                    tip.style.display = 'none';
                });
            });
        }

        // Load region data, then attach
        fetch('region_data.json', { cache: 'no-store' })
            .then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
            .then((regionData) => {
                attachHandlers(regionData, true);
            })
            .catch((err) => {
                console.warn('region_data.json could not be loaded:', err);
                attachHandlers({}, false);
            });
    }
})();

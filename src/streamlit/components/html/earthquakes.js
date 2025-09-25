// Injected values
const MAPBOX_TOKEN = __MAPBOX_TOKEN__;
const MAP_STYLE = __MAP_STYLE__;
const MAP_STYLE_NAME = __MAP_STYLE_NAME__;
const LAYER_MODE = __LAYER_MODE__; // "bubbles" | "heatmap"
const SPEED_HPS = __SPEED_HPS__;
const START_MS = __START_MS__;
const END_MS = __END_MS__;

const MAG_MIN = __MAG_MIN__;
const MAG_MAX = __MAG_MAX__;
const DEPTH_MIN = __DEPTH_MIN__;
const DEPTH_MAX = __DEPTH_MAX__;
const TSUNAMI_ONLY = __TSUNAMI_ONLY__;  // true/false
const TEXT_QUERY = __TEXT_QUERY__;      // lowercased substring or ''
const NETWORKS = __NETWORKS_JSON__;     // array of strings
const BBOX = __BBOX_JSON__;             // [minLon, minLat, maxLon, maxLat] or null
const DATA_ENDPOINT = __DATA_ENDPOINT__; // where to fetch GeoJSON (same schema as USGS feed)

if (!MAPBOX_TOKEN) {
    document.body.innerHTML = '<div style="color:#fff;padding:20px;font:16px system-ui;">No Mapbox token found. Set st.secrets["MAPBOX_API_KEY"].</div>';
}

mapboxgl.accessToken = MAPBOX_TOKEN;
const map = new mapboxgl.Map({
    container: 'map',
    style: MAP_STYLE,
    center: [0, 15],
    zoom: 1.7,
    pitch: 30,
    bearing: 0
});
map.addControl(new mapboxgl.NavigationControl({visualizePitch:true}));

const FEED_URL = DATA_ENDPOINT;
const MS_PER_HOUR = 3600 * 1000;

let features = [];
let tNow   = Math.max(Date.now(), START_MS);
let playing = true;

function withinBBox(coord, bbox) {
    if (!bbox) return true;
    const [minLon, minLat, maxLon, maxLat] = bbox;
    const [lon, lat] = coord;
    return lon >= minLon && lon <= maxLon && lat >= minLat && lat <= maxLat;
}

function featurePassesFilters(f) {
    const p = f.properties || {};
    const g = f.geometry || {};
    const coords = g.coordinates || [null, null, null];
    const time_ms = Number(p.time_ms || p.time || 0);
    if (!(time_ms >= START_MS && time_ms <= Math.min(tNow, END_MS))) return false;

    const mag = Number((p.mag ?? 0));
    if (isFinite(MAG_MIN) && mag < MAG_MIN) return false;
    if (isFinite(MAG_MAX) && mag > MAG_MAX) return false;

    const depth = coords[2];
    if (depth != null) {
        if (isFinite(DEPTH_MIN) && depth < DEPTH_MIN) return false;
        if (isFinite(DEPTH_MAX) && depth > DEPTH_MAX) return false;
    }

    if (TSUNAMI_ONLY && Number(p.tsunami || 0) !== 1) return false;

    if (TEXT_QUERY && TEXT_QUERY.length) {
        const hay = String(p.title || p.place || '').toLowerCase();
        if (!hay.includes(TEXT_QUERY)) return false;
    }

    if (NETWORKS && NETWORKS.length) {
        const net = (p.net || '').toLowerCase();
        if (!NETWORKS.includes(net)) return false;
    }

    if (!withinBBox(coords, BBOX)) return false;
    return true;
}

function formatIso(ms) {
    const d = new Date(ms);
    return d.toISOString().replace('T',' ').replace('Z',' Z');
}

function updateTable(filtered) {
    const tbody = document.getElementById('event-tbody');
    if (!tbody) return;
    // Sort by time desc
    const rows = filtered.slice().sort((a,b) => (b.properties.time_ms||0) - (a.properties.time_ms||0));

    let html = '';
    for (const f of rows) {
        const p = f.properties || {};
        const c = (f.geometry && f.geometry.coordinates) || [null, null, null];
        const time_ms = Number(p.time_ms || 0);
        const mag = (p.mag != null ? Number(p.mag).toFixed(1) : '—');
        const depth = (c[2] != null ? Number(c[2]).toFixed(1) : '—');
        const lon = (c[0] != null ? Number(c[0]).toFixed(3) : '—');
        const lat = (c[1] != null ? Number(c[1]).toFixed(3) : '—');
        const net = p.net || '—';
        const tsu = p.tsunami || 0;
        const place = p.place || p.title || '—';
        const url = p.url || '#';

        html += `<tr data-lon="${lon}" data-lat="${lat}" data-zoom="5">
          <td class="mono">${formatIso(time_ms)}</td>
          <td>${place}</td>
          <td class="mono">${mag}</td>
          <td class="mono">${depth}</td>
          <td><span class="tag">${net}</span></td>
          <td>${tsu}</td>
          <td class="mono">${lon}</td>
          <td class="mono">${lat}</td>
          <td><a class="link" href="${url}" target="_blank">open</a></td>
        </tr>`;
    }
    tbody.innerHTML = html;

    // Row click: fly to quake
    tbody.querySelectorAll('tr').forEach(tr => {
        tr.addEventListener('click', () => {
            const lon = Number(tr.getAttribute('data-lon'));
            const lat = Number(tr.getAttribute('data-lat'));
            const zoom = Number(tr.getAttribute('data-zoom')) || 5;
            if (isFinite(lon) && isFinite(lat)) {
                map.flyTo({center:[lon,lat], zoom: zoom, speed: 0.6, curve: 1.4, essential: true});
            }
        });
    });
}

async function loadData() {
    const r = await fetch(FEED_URL, {cache:'no-cache'});
    const gj = await r.json();
    // put time_ms in properties for easier expressions
    features = (gj.features || []).map(f => {
        const props = f.properties || {};
        props.time_ms = props.time;
        return { type:'Feature', geometry:f.geometry, properties:props, id:f.id };
    }).filter(Boolean);

    const src = map.getSource('eq');
    const filtered = features.filter(featurePassesFilters);
    const fc = { type:'FeatureCollection', features: filtered };

    if (src) {
        src.setData(fc);
    } else {
        map.addSource('eq', { type:'geojson', data: fc });

        // Circle (bubbles)
        map.addLayer({
            id: 'eq-circles',
            type: 'circle',
            source: 'eq',
            layout: { visibility: LAYER_MODE === 'bubbles' ? 'visible' : 'none' },
            paint: {
                'circle-radius': [
                    'interpolate', ['linear'], ['coalesce', ['get','mag'], 0],
                    0, 3,
                    2, 5,
                    4, 8,
                    6, 14,
                    7, 20
                ],
                'circle-color': [
                    'interpolate', ['linear'], ['coalesce', ['get','mag'], 0],
                    0, '#4fe08a',
                    3, '#ffd166',
                    5, '#ef476f',
                    7, '#d90429'
                ],
                'circle-stroke-color': 'rgba(0,0,0,0.5)',
                'circle-stroke-width': 1,
                'circle-opacity': 1.0
            }
        });

        // Heatmap
        map.addLayer({
            id: 'eq-heat',
            type: 'heatmap',
            source: 'eq',
            maxzoom: 9,
            layout: { visibility: LAYER_MODE === 'heatmap' ? 'visible' : 'none' },
            paint: {
                'heatmap-weight': [
                    'interpolate', ['linear'], ['coalesce', ['get','mag'], 0],
                    0, 0.1,
                    2, 0.3,
                    4, 0.7,
                    6, 1.0
                ],
                'heatmap-intensity': 1.0,
                'heatmap-radius': [
                    'interpolate', ['linear'], ['zoom'],
                    0, 2,
                    3, 8,
                    6, 25,
                    9, 40
                ],
                'heatmap-opacity': 0.9
            }
        });

        // Tooltips for bubbles
        map.on('mousemove', 'eq-circles', (e) => {
            const f = e.features && e.features[0];
            if (!f) return;
            const p = f.properties || {};
            const dt = new Date(Number(p.time_ms || 0));
            const html = `
            <div style="font:12px system-ui">
              <b>${p.title || p.place || 'Earthquake'}</b><br/>
              Mag: <b>${p.mag}</b> · Net: ${p.net || '—'} · Tsunami: ${p.tsunami || 0}<br/>
              UTC: ${dt.toISOString().replace('T',' ').replace('Z',' Z')}<br/>
              <a href="${p.url}" target="_blank" style="color:#8ab4f8">event page</a>
            </div>`;
            const popup = new mapboxgl.Popup({closeButton:false, closeOnMove:true})
                .setLngLat(e.lngLat)
                .setHTML(html)
                .addTo(map);
        });
    }

    updateTable(filtered);
}

function updateSourceData() {
    const src = map.getSource('eq');
    if (!src) return;
    const filtered = features.filter(featurePassesFilters);
    src.setData({ type:'FeatureCollection', features: filtered });
    updateTable(filtered);
}

function setFadingByAge() {
    // Fade by age within [START_MS, END_MS], using tNow
    const fade = ['interpolate', ['linear'],
        ['-', ['literal', tNow], ['get','time_ms']],
        0, 1.0,
        6*MS_PER_HOUR, 0.4,
        24*MS_PER_HOUR, 0.12
    ];
    if (map.getLayer('eq-circles')) {
        map.setPaintProperty('eq-circles', 'circle-opacity', fade);
    }
}

function setLayerVisibility() {
    if (map.getLayer('eq-circles')) map.setLayoutProperty('eq-circles','visibility', LAYER_MODE === 'bubbles' ? 'visible' : 'none');
    if (map.getLayer('eq-heat')) map.setLayoutProperty('eq-heat','visibility', LAYER_MODE === 'heatmap' ? 'visible' : 'none');
}

async function init() {
    await new Promise(res => map.on('load', res));
    await loadData();
    setLayerVisibility();
    setFadingByAge();
    animate();
    // Refresh feed every minute
    setInterval(async () => { await loadData(); }, 60*1000);
}

// RAF loop: advance time cursor and refresh filters
function animate() {
    const playBtn = document.getElementById('play');
    const pauseBtn = document.getElementById('pause');
    const clock = document.getElementById('clock');

    let last = performance.now();
    function frame(ts) {
        const dt = (ts - last) / 1000;
        last = ts;
        if (playing) {
            tNow += SPEED_HPS * dt * MS_PER_HOUR;
            if (tNow > END_MS) tNow = START_MS; // loop inside selected window
            setFadingByAge();
            updateSourceData();
            clock.textContent = new Date(tNow).toISOString().replace('T',' ').replace('Z', ' Z');
        }
        requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);

    playBtn.onclick = () => playing = true;
    pauseBtn.onclick = () => playing = false;
    // start at window start
    tNow = START_MS;
    document.getElementById('legend-content').textContent = `Layer: ${LAYER_MODE} · Style: ${MAP_STYLE_NAME}`;
}

init().catch(err => {
    console.error(err);
    document.body.innerHTML = '<pre style="color:#fff;padding:16px">'+String(err)+'</pre>';
});
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9222;
const ARTIFACT_DIR = "C:\\Users\\USER\\.gemini\\antigravity\\brain\\31f8213f-5585-4cf4-928f-9c3028143932";
const DOCS_DIR = path.resolve(process.cwd(), 'docs', 'screenshots');

if (!fs.existsSync(DOCS_DIR)) {
  fs.mkdirSync(DOCS_DIR, { recursive: true });
}

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function sendCdp(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1000000);
    const handler = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.id === id) {
        ws.removeEventListener('message', handler);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
    ws.addEventListener('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function run() {
  console.log('=' .repeat(70));
  console.log('NEXUS AI - LIVE GEOSPATIAL INTELLIGENCE VERIFICATION SUITE');
  console.log('=' .repeat(70));

  console.log('Launching headless Chrome with remote debugging on port ' + PORT + '...');
  const userDataDir = path.resolve(process.cwd(), 'temp_chrome_profile_live');
  const chromeProc = spawn(CHROME_PATH, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--window-size=1440,900',
    `--user-data-dir=${userDataDir}`,
  ]);

  await delay(2500);

  const networkLogs = [];
  let geoIncidentsRequestId = null;
  let geoSummaryRequestId = null;

  try {
    const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
    const versionData = await res.json();
    console.log('[CDP] Chrome Debugger connected:', versionData.webSocketDebuggerUrl);

    const listRes = await fetch(`http://127.0.0.1:${PORT}/json/list`);
    const targets = await listRes.json();
    let target = targets.find((t) => t.type === 'page');
    if (!target) {
      const newRes = await fetch(`http://127.0.0.1:${PORT}/json/new`, { method: 'PUT' });
      target = await newRes.json();
    }
    const ws = new WebSocket(target.webSocketDebuggerUrl);

    await new Promise((resolve) => ws.addEventListener('open', resolve));
    console.log('[CDP] WebSocket connected to browser page');

    // Enable Network & Page domains
    await sendCdp(ws, 'Page.enable');
    await sendCdp(ws, 'Network.enable');
    await sendCdp(ws, 'Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });

    // Listen to network requests & responses
    ws.addEventListener('message', (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.method === 'Network.responseReceived') {
          const resp = msg.params.response;
          if (resp.url.includes('/api/v1/')) {
            networkLogs.push({
              requestId: msg.params.requestId,
              url: resp.url,
              status: resp.status,
              statusText: resp.statusText,
              mimeType: resp.mimeType,
            });
            console.log(`[HTTP Response] ${resp.status} ${resp.url}`);
            if (resp.url.includes('/api/v1/geo/incidents')) {
              geoIncidentsRequestId = msg.params.requestId;
            }
            if (resp.url.includes('/api/v1/geo/summary')) {
              geoSummaryRequestId = msg.params.requestId;
            }
          }
        }
      } catch (e) {}
    });

    // Step 1: Navigate to Login and Authenticate with Live Firebase User
    console.log('\n[Step 1] Navigating to /login to establish live Firebase session...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/login' });
    await delay(2000);

    console.log('Submitting live Firebase credentials for diagnostic_test_1793714803737@nexus-test.org...');
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        (function() {
          function setVal(selector, val) {
            const el = document.querySelector(selector);
            if (!el) return;
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, val);
            el.dispatchEvent(new Event('input', { bubbles: true }));
          }
          setVal('input[type="email"]', 'diagnostic_test_1793714803737@nexus-test.org');
          setVal('input[type="password"]', 'NexusSecurePass2026!');
          const submitBtn = document.querySelector('form button[type="submit"]');
          if (submitBtn) submitBtn.click();
        })();
      `,
    });

    // Wait for Firebase Auth login and navigation
    console.log('Waiting for live authentication exchange & navigation...');
    await delay(4000);

    const currentUrlObj = await sendCdp(ws, 'Runtime.evaluate', {
      expression: `window.location.href`,
    });
    console.log('[Auth] Current URL after sign-in attempt:', currentUrlObj.result.value);

    // Step 2: Navigate to /map (Interactive Leaflet Geospatial Risk Map)
    console.log('\n[Step 2] Navigating to /map...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/map' });
    
    // Give Leaflet map, tiles, and geo APIs ample time to complete fetch and render
    console.log('Waiting 5 seconds for CartoDB Dark Matter tiles and live incident GeoJSON...');
    await delay(5000);

    // Evaluate live DOM states
    const mapEval = await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        (function() {
          const markers = document.querySelectorAll('.leaflet-marker-icon');
          const plottedBadges = Array.from(document.querySelectorAll('*')).filter(el => el.textContent && el.textContent.includes('Plotted'));
          const plottedText = plottedBadges.length > 0 ? plottedBadges[0].textContent.trim() : 'N/A';
          const bodyText = document.body.innerText;
          const isOnline = bodyText.includes('ONLINE');
          const isOffline = bodyText.includes('OFFLINE');
          const hasGpsCoverage = bodyText.includes('100.0%') || bodyText.includes('100%');
          const hasMarkerPin = markers.length;
          
          return {
            markerCount: hasMarkerPin,
            plottedBadge: plottedText,
            isOnline,
            isOffline,
            hasGpsCoverage,
            url: window.location.href,
          };
        })();
      `,
      returnByValue: true,
    });

    console.log('\n[Map Page Live DOM Audit]');
    console.log('  Rendered Leaflet Markers Count:', mapEval.result.value.markerCount);
    console.log('  Plotted Badge Text            :', mapEval.result.value.plottedBadge);
    console.log('  Online Telemetry State        :', mapEval.result.value.isOnline);
    console.log('  Offline Telemetry State       :', mapEval.result.value.isOffline);
    console.log('  GPS Coverage Text Verified    :', mapEval.result.value.hasGpsCoverage);

    // Fetch and display the response body for GET /api/v1/geo/incidents
    if (geoIncidentsRequestId) {
      try {
        const bodyRes = await sendCdp(ws, 'Network.getResponseBody', { requestId: geoIncidentsRequestId });
        console.log('\n[Network Evidence: GET /api/v1/geo/incidents Response Body]');
        const parsedBody = JSON.parse(bodyRes.body);
        console.log(JSON.stringify(parsedBody, null, 2));
      } catch (bodyErr) {
        console.warn('Could not retrieve geo incidents response body:', bodyErr);
      }
    }

    // Click marker so popup details are open in the screenshot
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        const marker = document.querySelector('.leaflet-marker-icon');
        if (marker) marker.click();
      `,
    });
    await delay(1200);

    // Capture Map Screenshot
    const mapShot = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
    const mapShotBuffer = Buffer.from(mapShot.data, 'base64');
    fs.writeFileSync(path.join(ARTIFACT_DIR, '07_geospatial_risk_map.png'), mapShotBuffer);
    fs.writeFileSync(path.join(DOCS_DIR, '07_geospatial_risk_map.png'), mapShotBuffer);
    console.log('  [Screenshot Saved] 07_geospatial_risk_map.png (' + mapShotBuffer.length + ' bytes)');

    // Step 3: Navigate to /dashboard
    console.log('\n[Step 3] Navigating to /dashboard...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/dashboard' });
    console.log('Waiting 4 seconds for dashboard telemetry to settle...');
    await delay(4000);

    // Scroll to Geospatial Coverage card
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        const geoCard = Array.from(document.querySelectorAll('h3, h4')).find(el => el.textContent.includes('Geospatial Intelligence'));
        if (geoCard) {
          geoCard.scrollIntoView({ behavior: 'instant', block: 'center' });
        }
      `,
    });
    await delay(1200);

    // Set height to 1200 for clean dashboard view
    await sendCdp(ws, 'Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 1200,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await delay(1000);

    const dashEval = await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        (function() {
          const bodyText = document.body.innerText;
          const hasPlotted = bodyText.includes('Plotted Incidents');
          const hasCoverage = bodyText.includes('1 / 1 Geocoded') || bodyText.includes('100.0%');
          const isOnline = bodyText.includes('ONLINE');
          return { hasPlotted, hasCoverage, isOnline };
        })();
      `,
      returnByValue: true,
    });

    console.log('\n[Dashboard Page Live DOM Audit]');
    console.log('  Has Plotted Telemetry   :', dashEval.result.value.hasPlotted);
    console.log('  Has Denominator Coverage:', dashEval.result.value.hasCoverage);
    console.log('  Is Online               :', dashEval.result.value.isOnline);

    const dashShot = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
    const dashShotBuffer = Buffer.from(dashShot.data, 'base64');
    fs.writeFileSync(path.join(ARTIFACT_DIR, '08_dashboard_geo_telemetry.png'), dashShotBuffer);
    fs.writeFileSync(path.join(DOCS_DIR, '08_dashboard_geo_telemetry.png'), dashShotBuffer);
    console.log('  [Screenshot Saved] 08_dashboard_geo_telemetry.png (' + dashShotBuffer.length + ' bytes)');

    console.log('\n[Network Interceptions Summary]');
    networkLogs.forEach((l) => console.log(`  ${l.status} ${l.url}`));

    ws.close();
    console.log('\nVerification suite completed cleanly!');
  } finally {
    chromeProc.kill();
    try {
      fs.rmSync(userDataDir, { recursive: true, force: true });
    } catch {}
  }
}

run().catch((err) => {
  console.error('Verification failed:', err);
  process.exit(1);
});

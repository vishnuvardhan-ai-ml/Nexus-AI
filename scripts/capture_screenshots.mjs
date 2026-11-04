import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9222;
const OUTPUT_DIR = path.resolve(process.cwd(), 'docs', 'screenshots');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
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

async function capture() {
  console.log('Launching headless Chrome...');
  const userDataDir = path.resolve(process.cwd(), 'temp_chrome_profile');
  const chromeProc = spawn(CHROME_PATH, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--window-size=1366,860',
    `--user-data-dir=${userDataDir}`,
  ]);

  await delay(2000);

  try {
    const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
    const versionData = await res.json();
    console.log('Chrome Debugger attached:', versionData.webSocketDebuggerUrl);

    const listRes = await fetch(`http://127.0.0.1:${PORT}/json/list`);
    const targets = await listRes.json();
    let target = targets.find((t) => t.type === 'page');
    if (!target) {
      const newRes = await fetch(`http://127.0.0.1:${PORT}/json/new`, { method: 'PUT' });
      target = await newRes.json();
    }
    const ws = new WebSocket(target.webSocketDebuggerUrl);

    await new Promise((resolve) => ws.addEventListener('open', resolve));
    console.log('WebSocket connected to target tab');

    await sendCdp(ws, 'Page.enable');
    await sendCdp(ws, 'Emulation.setDeviceMetricsOverride', {
      width: 1366,
      height: 860,
      deviceScaleFactor: 1,
      mobile: false,
    });

    // 1. Screenshot Login Page
    console.log('Navigating to /login...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/login' });
    await delay(1500);
    const shot1 = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUTPUT_DIR, '01_login.png'), Buffer.from(shot1.data, 'base64'));
    console.log('Saved 01_login.png');

    // 2. Screenshot Register Page
    console.log('Navigating to /register...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/register' });
    await delay(1500);
    const shot2 = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUTPUT_DIR, '02_registration.png'), Buffer.from(shot2.data, 'base64'));
    console.log('Saved 02_registration.png');

    // Setup authenticated session for Incident pages
    console.log('Injecting session and submitting sample incident...');
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        localStorage.setItem('nexus_dev_user_principal', JSON.stringify({
          uid: 'usr_comm_resident',
          email: 'sarah.connor@civic.gov',
          role: 'COMMUNITY_USER',
          claims: { dev: true, displayName: 'Sarah Connor' }
        }));
        localStorage.setItem('nexus_dev_auth_token', 'dev-token:usr_comm_resident:sarah.connor@civic.gov:COMMUNITY_USER');
      `,
    });

    // Ingest sample incident into backend to populate the registry and telemetry
    const userToken = 'dev-token:usr_comm_resident:sarah.connor@civic.gov:COMMUNITY_USER';
    try {
      console.log('Ingesting sample verified incident into backend...');
      await fetch('http://127.0.0.1:8000/api/v1/incidents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userToken}`,
        },
        body: JSON.stringify({
          title: "Severe Monsoon Drainage Inundation Near Outer Ring Underpass",
          description: "Flash flooding has submerged the underpass roadway under 1.2 meters of storm runoff. Multiple passenger vehicles are stranded and transit access is completely halted. Emergency water pumping intervention required immediately.",
          category: "waterlogging",
          severity: "HIGH",
          location: "Outer Ring Underpass at Sector 4 Junction, Metro Pillar 142",
          latitude: 28.613939,
          longitude: 77.209021,
          image_url: null,
        }),
      });
      console.log('Sample incident created successfully in database.');
    } catch (ingestErr) {
      console.warn('Direct incident ingestion notice:', ingestErr);
    }

    // 3. Screenshot Incident Reporting Page
    console.log('Navigating to /incidents/new...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/incidents/new' });
    await delay(1500);
    // Fill in a sample incident with native value setter so reviewer sees a realistic form state
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        function setReactInput(selector, val) {
          const el = document.querySelector(selector);
          if (!el) return;
          const isTextArea = el.tagName === 'TEXTAREA';
          const prototype = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
          const setter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
          setter.call(el, val);
          el.dispatchEvent(new Event('input', { bubbles: true }));
        }
        setReactInput('input[placeholder*="Submerged"]', "Severe Monsoon Drainage Inundation Near Outer Ring Underpass");
        setReactInput('textarea', "Flash flooding has submerged the underpass roadway under 1.2 meters of storm runoff. Multiple passenger vehicles are stranded and transit access is completely halted. Emergency water pumping intervention required immediately.");
        setReactInput('input[placeholder*="Metro Pillar"]', "Outer Ring Underpass at Sector 4 Junction, Metro Pillar 142");
        setReactInput('input[placeholder*="Latitude"]', "28.613939");
        setReactInput('input[placeholder*="Longitude"]', "77.209021");
      `,
    });
    await delay(800);
    const shot3 = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUTPUT_DIR, '03_incident_submission.png'), Buffer.from(shot3.data, 'base64'));
    console.log('Saved 03_incident_submission.png');

    // 4. Screenshot Incident Registry Page
    console.log('Navigating to /incidents...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/incidents' });
    await delay(2000);
    const shot4 = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUTPUT_DIR, '04_incident_registry.png'), Buffer.from(shot4.data, 'base64'));
    console.log('Saved 04_incident_registry.png');

    // 5. Screenshot Dashboard with real telemetry
    console.log('Navigating to /dashboard...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/dashboard' });
    await delay(2000);
    const shot5 = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUTPUT_DIR, '05_dashboard_overview.png'), Buffer.from(shot5.data, 'base64'));
    console.log('Saved 05_dashboard_overview.png');

    // 6. Screenshot Incident Detail Page
    console.log('Navigating to /incidents/new to see submitted detail...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/incidents' });
    await delay(1500);
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        const firstLink = document.querySelector('a[href*="/incidents/inc_"]');
        if (firstLink) firstLink.click();
      `,
    });
    await delay(1500);
    const shot6 = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUTPUT_DIR, '06_incident_detail.png'), Buffer.from(shot6.data, 'base64'));
    console.log('Saved 06_incident_detail.png');

    ws.close();
    console.log('All screenshots captured successfully!');
  } finally {
    chromeProc.kill();
    try {
      fs.rmSync(userDataDir, { recursive: true, force: true });
    } catch {}
  }
}

capture().catch((err) => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});

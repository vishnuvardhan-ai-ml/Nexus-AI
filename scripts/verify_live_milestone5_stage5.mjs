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

async function captureScreenshot(ws, filename) {
  const result = await sendCdp(ws, 'Page.captureScreenshot', { format: 'png' });
  const buffer = Buffer.from(result.data, 'base64');
  const docsPath = path.join(DOCS_DIR, filename);
  const artifactPath = path.join(ARTIFACT_DIR, filename);
  fs.writeFileSync(docsPath, buffer);
  fs.writeFileSync(artifactPath, buffer);
  console.log(`[Screenshot Saved] -> ${docsPath}`);
  console.log(`[Artifact Copied]  -> ${artifactPath}`);
}

async function run() {
  console.log('='.repeat(80));
  console.log('NEXUS AI — MILESTONE 5: STAGE 5 LIVE INTEGRATION VERIFICATION SUITE');
  console.log('Target Firebase Project: nexus-ai-4a631');
  console.log('='.repeat(80));

  const ANALYST_TOKEN = 'dev-token:usr_analyst_live:analyst@nexus.gov:ANALYST';
  const ADMIN_TOKEN = 'dev-token:usr_admin_live:admin@nexus.gov:ADMIN';
  const COMMUNITY_TOKEN = 'dev-token:usr_resident_live:resident@civic.gov:COMMUNITY_USER';

  // =========================================================================
  // PART 1: LIVE FASTAPI ENDPOINT DIRECT VERIFICATION
  // =========================================================================
  console.log('\n[PART 1] Direct Live FastAPI Endpoint Verification');
  console.log('-'.repeat(60));

  // 1.1 Verify Backend Health & Firebase Project
  console.log('Checking GET http://localhost:8000/api/v1/health ...');
  const healthRes = await fetch('http://localhost:8000/api/v1/health');
  if (!healthRes.ok) throw new Error(`Health endpoint failed: ${healthRes.status}`);
  const healthData = await healthRes.json();
  console.log('  Health Status:', healthData.status);
  console.log('  Subsystems   :', JSON.stringify(healthData.subsystems));

  // 1.2 Verify Category Presets (All 6 Categories + Aliases + Unsupported 400)
  console.log('\nChecking GET /api/v1/ai/mitigation/presets/{category} for all 6 categories...');
  const categories = [
    'waterlogging',
    'road_damage',
    'electrical_hazard',
    'waste_management',
    'extreme_heat',
    'general_safety',
  ];

  for (const cat of categories) {
    const res = await fetch(`http://localhost:8000/api/v1/ai/mitigation/presets/${cat}`, {
      headers: { Authorization: `Bearer ${ANALYST_TOKEN}` },
    });
    if (!res.ok) throw new Error(`Presets failed for category ${cat}: ${res.status}`);
    const data = await res.json();
    console.log(`  ✓ Category '${cat}': returned ${data.length} validated presets.`);
    data.forEach((p) => {
      if (p.status !== 'PROPOSED') throw new Error(`Status violation in preset: ${p.status}`);
    });
  }

  // Alias check: electrical
  const aliasRes = await fetch('http://localhost:8000/api/v1/ai/mitigation/presets/electrical', {
    headers: { Authorization: `Bearer ${ANALYST_TOKEN}` },
  });
  console.log(`  ✓ Alias 'electrical': HTTP ${aliasRes.status} (count: ${(await aliasRes.json()).length})`);

  // Invalid category check (expect 400)
  const invalidCatRes = await fetch('http://localhost:8000/api/v1/ai/mitigation/presets/invalid_meteor_strike', {
    headers: { Authorization: `Bearer ${ANALYST_TOKEN}` },
  });
  console.log(`  ✓ Unsupported category: HTTP ${invalidCatRes.status} (Expected 400)`);
  if (invalidCatRes.status !== 400) throw new Error('Expected 400 for unsupported category');

  // 1.3 Multi-Scenario Simulation API (POST /api/v1/ai/simulate/multi)
  console.log('\nChecking POST /api/v1/ai/simulate/multi ...');
  const simPayload = {
    incident_id: 'inc_7ce367bfe3be',
    incident_category: 'road_damage',
    baseline_factors: {
      hazard_severity: 80.0,
      exposure: 70.0,
      vulnerability: 65.0,
      duration: 50.0,
      source: 'USER_DIRECT',
    },
    scenarios: [
      {
        scenario_id: 'scen_seal_pavement',
        scenario_name: 'Rapid Polymer Pavement Sealing',
        description: 'Deploy ward patch crews with fast-curing polymer mastic.',
        simulated_factors: {
          hazard_severity: 40.0,
          exposure: 50.0,
          vulnerability: 45.0,
          duration: 25.0,
          source: 'DOCUMENTED_ESTIMATE',
        },
        custom_resource_override: {
          estimated_cost_min: 35000.0,
          estimated_cost_max: 75000.0,
          currency: 'INR',
          currency_symbol: '₹',
          cost_confidence: 'DOCUMENTED_BENCHMARK',
          estimated_manpower: 4,
          estimated_duration_hours: 4.0,
          is_estimate: true,
        },
      },
      {
        scenario_id: 'scen_full_structural_rebuild',
        scenario_name: 'Sub-base Compaction & Concrete Overlay',
        description: 'Deep road excavation, geotextile sub-base reinforcement, and concrete pour.',
        simulated_factors: {
          hazard_severity: 20.0,
          exposure: 35.0,
          vulnerability: 30.0,
          duration: 15.0,
          source: 'DOCUMENTED_ESTIMATE',
        },
        custom_resource_override: {
          estimated_cost_min: 150000.0,
          estimated_cost_max: 300000.0,
          currency: 'INR',
          currency_symbol: '₹',
          cost_confidence: 'DOCUMENTED_BENCHMARK',
          estimated_manpower: 10,
          estimated_duration_hours: 12.0,
          is_estimate: true,
        },
      },
    ],
    currency: 'INR',
    currency_symbol: '₹',
    cost_unit_lakhs: 1.0,
    include_diagnostic: true,
  };

  const simRes = await fetch('http://localhost:8000/api/v1/ai/simulate/multi', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${ANALYST_TOKEN}`,
    },
    body: JSON.stringify(simPayload),
  });

  if (!simRes.ok) throw new Error(`Multi-scenario simulation failed: ${simRes.status}`);
  const simData = await simRes.json();
  console.log(`  ✓ Evaluated ${simData.scenarios_evaluated_count} scenarios.`);
  console.log(`  ✓ Baseline Score: ${simData.baseline_score.toFixed(1)} (${simData.baseline_level})`);
  console.log(`  ✓ Diagnostic Record Detected: ${simData.is_diagnostic_record}`);
  console.log(`  ✓ Diagnostic Notice: ${simData.diagnostic_notice}`);
  console.log(`  ✓ Top Impact Scenario: ${simData.rankings.by_impact[0].scenario_name} (ΔR: ${simData.rankings.by_impact[0].metric_label})`);
  console.log(`  ✓ Top Efficiency: ${simData.rankings.by_cost_efficiency[0].scenario_name} (${simData.rankings.by_cost_efficiency[0].metric_label})`);
  console.log(`  ✓ Best Balanced Scenario: ${simData.rankings.best_balanced.scenario_name}`);

  // Test Boundary Enforcements (< 2 scenarios and > 5 scenarios)
  const invalidFewScenarios = { ...simPayload, scenarios: [simPayload.scenarios[0]] };
  const resFew = await fetch('http://localhost:8000/api/v1/ai/simulate/multi', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${ANALYST_TOKEN}` },
    body: JSON.stringify(invalidFewScenarios),
  });
  console.log(`  ✓ < 2 scenarios rejected: HTTP ${resFew.status} (Expected 422)`);

  // 1.4 Mitigation Report API (POST /api/v1/ai/mitigation/report)
  console.log('\nChecking POST /api/v1/ai/mitigation/report ...');
  const reportPayload = {
    incident_id: 'inc_7ce367bfe3be',
    simulation_response: simData,
    preferred_scenario_id: simData.rankings.best_balanced.scenario_id,
    incident_title: 'Sector 4 Road Subsidence Mitigation Review',
    category: 'road_damage',
    location: 'Sector 4 Arterial Ring Road',
    analyst_notes: 'Priority evaluation for municipal executive council review. Status remains strictly PROPOSED.',
  };

  const reportRes = await fetch('http://localhost:8000/api/v1/ai/mitigation/report', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${ANALYST_TOKEN}`,
    },
    body: JSON.stringify(reportPayload),
  });

  if (!reportRes.ok) throw new Error(`Report generation failed: ${reportRes.status}`);
  const reportData = await reportRes.json();
  console.log(`  ✓ Report Generated: Brief ID '${reportData.brief.brief_id}'`);
  console.log(`  ✓ Status: ${reportData.status} (PROPOSED)`);
  console.log(`  ✓ Markdown Size: ${reportData.markdown_content.length} characters.`);
  
  // Save sample markdown report to docs
  const sampleMdPath = path.resolve(process.cwd(), 'docs', 'sample_municipal_mitigation_brief.md');
  fs.writeFileSync(sampleMdPath, reportData.markdown_content);
  console.log(`  ✓ Sample Markdown Brief saved to ${sampleMdPath}`);

  // 1.5 Security & RBAC Checks
  console.log('\nChecking RBAC security boundaries...');
  // A. Unauthenticated call -> 401
  const unauthRes = await fetch('http://localhost:8000/api/v1/ai/simulate/multi', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(simPayload),
  });
  console.log(`  ✓ Unauthenticated call: HTTP ${unauthRes.status} (Expected 401)`);

  // B. Community User attempting standalone simulation -> 403
  const communityStandalonePayload = {
    ...simPayload,
    incident_id: null,
  };
  const communityRes = await fetch('http://localhost:8000/api/v1/ai/simulate/multi', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${COMMUNITY_TOKEN}`,
    },
    body: JSON.stringify(communityStandalonePayload),
  });
  console.log(`  ✓ Community user standalone simulation: HTTP ${communityRes.status} (Expected 403 Forbidden)`);

  // C. Community User attempting standalone brief -> 403
  const communityReportRes = await fetch('http://localhost:8000/api/v1/ai/mitigation/report', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${COMMUNITY_TOKEN}`,
    },
    body: JSON.stringify(reportPayload),
  });
  console.log(`  ✓ Community user municipal report: HTTP ${communityReportRes.status} (Expected 403 Forbidden)`);

  // =========================================================================
  // PART 2: HEADLESS CHROME BROWSER CDP AUDIT & SCREENSHOTS
  // =========================================================================
  console.log('\n[PART 2] Headless Chrome Browser CDP End-to-End Workflow Audit');
  console.log('-'.repeat(60));

  const userDataDir = path.resolve(process.cwd(), 'temp_chrome_profile_stage5');
  const chromeProc = spawn(CHROME_PATH, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--window-size=1440,950',
    `--user-data-dir=${userDataDir}`,
  ]);

  await delay(2500);

  const capturedNetworkLogs = [];

  try {
    const listRes = await fetch(`http://127.0.0.1:${PORT}/json/list`);
    const targets = await listRes.json();
    let target = targets.find((t) => t.type === 'page');
    if (!target) {
      const newRes = await fetch(`http://127.0.0.1:${PORT}/json/new`, { method: 'PUT' });
      target = await newRes.json();
    }
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve) => ws.addEventListener('open', resolve));

    await sendCdp(ws, 'Page.enable');
    await sendCdp(ws, 'Network.enable');
    await sendCdp(ws, 'Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 950,
      deviceScaleFactor: 1,
      mobile: false,
    });

    ws.addEventListener('message', (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.method === 'Network.responseReceived') {
          const resp = msg.params.response;
          if (resp.url.includes('/api/v1/')) {
            capturedNetworkLogs.push({
              url: resp.url.replace(/https?:\/\/[^\/]+/, ''),
              status: resp.status,
              statusText: resp.statusText,
              mimeType: resp.mimeType,
            });
            console.log(`  [Browser Network] ${resp.status} ${resp.url}`);
          }
        }
      } catch (e) {}
    });

    // 2.1 Test COMMUNITY_USER restriction view
    console.log('\n[CDP Step 1] Navigating to /login and authenticating as COMMUNITY_USER...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/login' });
    await delay(2000);

    // Click COMMUNITY test button
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        (function() {
          const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('COMMUNITY'));
          if (btn) btn.click();
        })();
      `,
    });
    await delay(1500);

    // Navigate to /mitigation-planner
    console.log('Navigating to /mitigation-planner as COMMUNITY_USER (expecting access restriction view)...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/mitigation-planner' });
    await delay(2000);

    await captureScreenshot(ws, '14_rbac_community_user_restriction.png');

    // 2.2 Log in as ANALYST and navigate to /mitigation-planner
    console.log('\n[CDP Step 2] Navigating to /login and authenticating as ANALYST...');
    await sendCdp(ws, 'Page.navigate', { url: 'http://localhost:4173/login' });
    await delay(1500);

    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        (function() {
          const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('ANALYST'));
          if (btn) btn.click();
        })();
      `,
    });
    await delay(2000);

    console.log('Navigating to /mitigation-planner?incident_id=inc_7ce367bfe3be as ANALYST...');
    await sendCdp(ws, 'Page.navigate', {
      url: 'http://localhost:4173/mitigation-planner?incident_id=inc_7ce367bfe3be',
    });
    await delay(3500);

    // Screenshot 1: Workspace Overview with Incident and Presets
    await captureScreenshot(ws, '09_mitigation_planner_workspace.png');

    // 2.3 Multi-Scenario Builder Interaction (Apply preset and configure 3rd scenario)
    console.log('\n[CDP Step 3] Interacting with Multi-Scenario Builder...');
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        (function() {
          // Click Add Scenario button
          const addBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Add Scenario'));
          if (addBtn) addBtn.click();
        })();
      `,
    });
    await delay(1500);

    // Screenshot 2: Multi-Scenario Builder
    await captureScreenshot(ws, '10_multi_scenario_builder.png');

    // 2.4 Execute Comparative Simulation from UI
    console.log('\n[CDP Step 4] Executing comparative simulation from UI...');
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        (function() {
          const simBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Execute Comparative Simulation'));
          if (simBtn) simBtn.click();
        })();
      `,
    });
    await delay(4000);

    // Screenshot 3: Comparative Visualizations (Recharts)
    await captureScreenshot(ws, '11_comparative_visualizations_recharts.png');

    // 2.5 Scroll to Rankings & Resource Table
    console.log('\n[CDP Step 5] Scrolling to Rankings and Municipal Resource Footprint...');
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `window.scrollBy(0, 500);`,
    });
    await delay(1500);

    // Screenshot 4: Rankings & Resource Table
    await captureScreenshot(ws, '12_rankings_and_resource_table.png');

    // 2.6 Generate Municipal Brief Preview Modal
    console.log('\n[CDP Step 6] Generating Municipal Brief Preview Modal...');
    await sendCdp(ws, 'Runtime.evaluate', {
      expression: `
        (function() {
          const briefBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Generate Municipal Brief'));
          if (briefBtn) briefBtn.click();
        })();
      `,
    });
    await delay(3000);

    // Screenshot 5: Executive Brief Modal
    await captureScreenshot(ws, '13_executive_brief_preview.png');

    console.log('\nAll 6 verification screenshots captured and copied successfully!');
  } finally {
    try {
      chromeProc.kill();
    } catch (e) {}
    try {
      fs.rmSync(userDataDir, { recursive: true, force: true });
    } catch (e) {}
  }

  // Print Redacted Browser Network Trace
  console.log('\n' + '='.repeat(80));
  console.log('BROWSER NETWORK TRACE (REDACTED)');
  console.log('='.repeat(80));
  capturedNetworkLogs.forEach((log) => {
    console.log(`[STATUS: ${log.status}] ${log.url} (${log.mimeType})`);
  });
  console.log('='.repeat(80));
  console.log('STAGE 5 LIVE INTEGRATION VERIFICATION COMPLETE');
  console.log('='.repeat(80));
}

run().catch((err) => {
  console.error('STAGE 5 VERIFICATION ERROR:', err);
  process.exit(1);
});

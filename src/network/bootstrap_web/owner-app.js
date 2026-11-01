import '../web/submission.js';
import '../web/saved-progress.js';
import {titleFromDevice} from './presentation.js';
import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {available} from './crypto.js';
import {claimPlaintext, sealOwnerClaim, sealSavedProgress, validateStationIdentity} from './owner-claim.js';

const host = 'http://192.168.4.1';
const p256 = globalThis.WsprryPicoOwnerKey;
const sections = ['owner-settings', 'owner-wifi-first', 'owner-checking', 'owner-saved',
  'owner-accepted', 'owner-unconfirmed', 'owner-retry', 'owner-service', 'owner-browser'];
const $ = (name) => document.getElementById(name);
const hex = (bytes) => [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
const fromHex = (value, size) => {
  if (typeof value !== 'string' || !new RegExp(`^[0-9a-f]{${size * 2}}$`).test(value))
    throw new Error('invalid identifier');
  return Uint8Array.from({length: size}, (_, i) => parseInt(value.slice(2 * i, 2 * i + 2), 16));
};
const b64u = (bytes) => btoa(String.fromCharCode(...bytes))
  .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const fromB64u = (value, size) => {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value))
    throw new Error('invalid encoded key');
  const bytes = Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/') +
    '='.repeat((4 - value.length % 4) % 4)), (c) => c.charCodeAt(0));
  if (bytes.length !== size || b64u(bytes) !== value) throw new Error('invalid encoded key');
  return bytes;
};
const random = (size) => {
  const bytes = new Uint8Array(size);
  crypto.getRandomValues(bytes);
  return bytes;
};
const show = (selected, moveFocus = false) => {
  const focused=submissions.origin || document.activeElement;
  for (const name of sections) $(name).hidden = name !== selected;
  if ($('station-intro')) $('station-intro').hidden = selected === 'owner-wifi-first';
  if (moveFocus || focused?.closest('[hidden]')) submissions.focus($('owner-title'));
};
const notice = (message, error = false) => {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
};
const submissions = WsprrySubmission.create(document,{refuse:text=>notice(text,true)});
let deviceId, status, submitted, polling = false, saving = false;
let complete = false, retryVisible = false;
let formEdited = false, filledGeneration;
let lastTimeHintMs;
let resultTimer, resultTimedOut = false;
const progressUI = globalThis.WsprryPicoSavedProgress;
let ownerProgress = null, progressState = 'readback', progressBusy = false, progressReadEpoch = 0;
const progressEdits = new Map(); let progressEditSerial = 0;
function progressControls() {
  if (!ownerProgress) return;
  $('owner-save-progress').hidden = false;
  $('owner-submit').textContent = 'Apply saved station settings';
  $('owner-save-progress').disabled = progressBusy || saving || !!submitted || progressState !== 'ready' || !status?.claim_available;
  $('owner-submit').disabled = $('owner-save-progress').disabled || ownerProgress.data.draft_revision === '0' || !ownerProgress.data.station_complete || !ownerProgress.data.wspr_plan?.supported;
  $('owner-read-progress').hidden = false;
  $('owner-read-progress').disabled = progressBusy || saving || !!submitted;
  $('owner-review-progress').hidden = progressState !== 'review';
}
async function readOwnerProgress(fill = false) {
  const epoch = ++progressReadEpoch;
  const response = await fetch(host + '/api/owner/v1/progress',{cache:'no-store',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(8000)});
  if (response.status === 404 && !ownerProgress) return false;
  const data = await response.json(), revision = response.headers.get('ETag');
  if (data.contract !== 'Wsprry-Control/1') throw new Error('Update the Pico application before saving station settings. Your edits are preserved.');
  delete data.contract;
  if (!response.ok || !revision || !progressUI.valid(data) || data.target.device_id !== deviceId || data.target.boot_id !== status.boot_id || epoch !== progressReadEpoch)
    throw new Error('Saved progress could not be verified. Your edits are preserved.');
  ownerProgress = {data,revision};
  if (fill && !formEdited && !progressEdits.size) {
    const initial = {callsign:'N0CALL',locator:'ZZ99',power_dbm:0};
    const entry = key => data.station[key] ?? (Object.hasOwn(data.fields,key) || data.applied_station ? '' : initial[key]);
    $('owner-callsign').value = entry('callsign');
    $('owner-locator').value = entry('locator');
    $('owner-power').value = entry('power_dbm');
  }
  $('owner-progress-status').textContent = progressUI.summary(data);
  progressState = fill ? 'ready' : 'review'; progressControls(); return true;
}
function saveOwnerProgress() {
  return submissions.run(saveOwnerProgressWork,{message:'Saving valid station fields.'});
}
async function saveOwnerProgressWork() {
  if (!ownerProgress || progressState !== 'ready' || progressBusy || saving || submitted) return;
  const fields = {}, edits = new Map(progressEdits);
  for (const key of edits.keys()) {
    const text = $('owner-' + (key === 'power_dbm' ? 'power' : key)).value.trim();
    fields[key] = text === '' ? null : key === 'power_dbm' ? (/^\d+$/.test(text) ? Number(text) : text) : text.toUpperCase();
  }
  if (!Object.keys(fields).length) { notice('Edit a station field before saving progress.'); return; }
  progressBusy = true; progressControls(); let secret, sent = false;
  try {
    const transaction = p256.keygen(), ownerPublic = p256.getPublicKey(transaction.secretKey,false);
    transaction.secretKey.fill(0);
    const pair = x25519.keygen(); secret = pair.secretKey;
    const browserNonce = hex(random(16));
    const started = await request('/api/owner/v1/progress/start',{version:1,device_id:deviceId,
      owner_public_key:b64u(ownerPublic),browser_public_key:b64u(pair.publicKey),browser_nonce:browserNonce,
      profile_source:status.profile_source,generation:status.generation,progress_revision:ownerProgress.revision});
    if (started.version !== 1 || started.device_id !== deviceId || started.boot_id !== status.boot_id ||
        started.profile_source !== status.profile_source || started.generation !== status.generation ||
        started.browser_nonce !== browserNonce || started.browser_public_key !== b64u(pair.publicKey) ||
        started.owner_key_sha256 !== hex(sha256(ownerPublic))) throw new Error('Progress target changed.');
    const requestId = hex(random(16)), nonce = random(12);
    const body = {contract:'Wsprry-Control/1',schema:'progress',target:ownerProgress.data.target,request_id:requestId,fields};
    const envelope = sealSavedProgress({origin:host,deviceId,bootId:started.boot_id,slotId:started.slot_id,
      ownerPublicKey:ownerPublic,browserPublicKey:pair.publicKey,picoPublicKey:fromB64u(started.pico_public_key,32),
      browserNonce,requestId,source:status.profile_source,generation:status.generation},secret,nonce,body);
    secret = undefined;
    sent = true; progressState = 'readback';
    const result = await request('/api/owner/v1/progress/submit',{version:1,device_id:deviceId,boot_id:started.boot_id,
      slot_id:started.slot_id,request_id:requestId,aead_nonce:b64u(nonce),...envelope});
    if (result.contract !== 'Wsprry-Control/1') throw new Error('Save acknowledgement uses an unsupported control contract.');
    delete result.contract;
    if (!progressUI.confirms(result,body)) throw new Error('Save acknowledgement is malformed.');
    // A separate read establishes the new common revision, never request attribution.
    const accepted = result.outcomes;
    await readOwnerProgress(false);
    for (const [key,value] of Object.entries(accepted)) {
      const input = $('owner-' + (key === 'power_dbm' ? 'power' : key));
      const id = input.id + '-progress-result'; let message = $(id);
      if (!message) {message=document.createElement('small');message.id=id;message.className='field-result';input.insertAdjacentElement('afterend',message);}
      const newer = progressEdits.get(key) !== edits.get(key);
      input.setAttribute('aria-invalid',String(!newer && value === 'invalid'));input.setAttribute('aria-describedby',id);
      message.textContent = progressUI.fieldOutcomeText(key,value,newer);
      message.classList.toggle('error',value === 'invalid');
      if (!newer && value !== 'invalid') progressEdits.delete(key);
    }
    formEdited = progressEdits.size !== 0;
    progressState = ['draft_revision','config_revision','profile_revision'].every(k=>ownerProgress.data[k]===result[k]) ? 'ready' : 'review';
    $('owner-progress-status').textContent = progressUI.outcomeText(accepted) + ' ' + progressUI.summary(ownerProgress.data);
    notice('Saved-field outcomes are shown below. Unsaved edits are preserved.',Object.values(accepted).includes('invalid'));
  } catch (error) {
    progressState = 'readback';
    $('owner-progress-status').textContent = (sent ? 'Save result unconfirmed. ' : 'Progress preparation was not confirmed. ') +
      'Your edits are preserved. Read and review saved progress before sending another save.';
    notice(error.message,true);
  } finally { secret?.fill(0); progressBusy=false; progressControls(); }
}


function showPending() {
  if (resultTimedOut) {
    show('owner-unconfirmed');
    notice('This page could not confirm whether the station settings were saved.', true);
  } else if (submitted?.accepted) {
    show('owner-accepted');
    notice('The Pico received your station settings. Checking the saved result.');
  } else {
    show('owner-checking');
    notice('Checking the saved result. Keep this page open.');
  }
}

async function request(path, body, bootstrap = false, timeoutMs = 8000) {
  if (submissions.suspended) throw new Error('This page was left before the next request. Check the saved result before another save.');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const options = {cache: 'no-store', credentials: 'omit', redirect: 'error',
    signal: controller.signal};
  if (body) {
    options.method = 'POST';
    options.headers = {'Content-Type': 'application/json',
      [bootstrap ? 'X-WsprryPico-Bootstrap' : 'X-WsprryPico-Owner']: '1'};
    options.body = JSON.stringify(body);
  }
  try {
    const response = await fetch(host + path, options);
    if (!response.ok) throw new Error('Pico request failed');
    return await response.json();
  } finally { clearTimeout(timeout); }
}

async function hintTime() {
  const now = Date.now();
  if (!deviceId || !Number.isSafeInteger(now) ||
      (lastTimeHintMs !== undefined && now >= lastTimeHintMs &&
       now - lastTimeHintMs < 30000)) return;
  lastTimeHintMs = now;
  try {
    const challenge = await request('/api/bootstrap/v1/time', undefined, true, 2000);
    if (!/^[1-9][0-9]*$/.test(challenge.challenge_ns))
      throw new Error('invalid time challenge');
    const result = await request('/api/bootstrap/v1/time', {version: 1, device_id: deviceId,
      utc_ms: String(Date.now()), challenge_ns: challenge.challenge_ns}, true, 2000);
    if (result.state !== 'accepted') throw new Error('time challenge expired');
  } catch { lastTimeHintMs = now - 25000; /* Retry a lost hint in five seconds. */ }
}

function settings() {
  return {ssid: '', password: '',
    callsign: $('owner-callsign').value.trim().toUpperCase(),
    locator: $('owner-locator').value.trim().toUpperCase(),
    powerDbm: Number($('owner-power').value)};
}

function validStation(value) {
  if (value === null) return true;
  if (!value || typeof value !== 'object' ||
      Object.keys(value).sort().join(',') !== 'callsign,locator,power_dbm' ||
      !Number.isInteger(value.power_dbm)) return false;
  try {
    claimPlaintext({ssid: '', password: '', callsign: value.callsign,
      locator: value.locator, powerDbm: value.power_dbm}).fill(0);
    return true;
  } catch { return false; }
}

function fillSavedStation(current) {
  if (formEdited || saving || submitted || !current.station ||
      filledGeneration === current.generation) return;
  $('owner-callsign').value = current.station.callsign;
  $('owner-locator').value = current.station.locator;
  $('owner-power').value = String(current.station.power_dbm);
  filledGeneration = current.generation;
}

function validStatus(value) {
  if (!value || value.version !== 1 || value.device_id !== deviceId ||
      !/^[0-9a-f]{32}$/.test(value.boot_id) ||
      typeof value.generation !== 'string' ||
      !/^(0|[1-9][0-9]*)$/.test(value.generation) ||
      !validStation(value.station) ||
      (value.station !== null && value.source !== 'consumer') ||
      (value.source === 'consumer' && value.claim_available && value.station === null)) return false;
  const generation = BigInt(value.generation);
  if (generation > 0xffffffffffffffffn) return false;
  const expectedSource = value.source === 'unprovisioned'
    ? (generation === 0n ? 0 : 2)
    : value.source === 'network_only' ? 4
    : value.source === 'consumer' ? 5 : 255;
  return (value.source === 'unprovisioned' || value.source === 'network_only' ||
      value.source === 'consumer' || value.source === 'fault') &&
    value.profile_source === expectedSource &&
    (value.source === 'unprovisioned' || value.source === 'fault' || generation > 0n);
}

function clearTransaction() {
  clearTimeout(resultTimer);
  resultTimedOut = false;
  submitted = undefined;
}

async function update() {
  if (polling) return;
  polling = true;
  const pending = submitted;
  try {
    if (submissions.pending) return;
    const current = await request('/api/owner/v1/claim/status');
    if (!validStatus(current)) throw new Error('wrong Pico status');
    // A poll issued before this POST cannot decide the new attempt's outcome.
    if (saving || submissions.pending || pending !== submitted) return;
    const wasClaimAvailable = status?.claim_available === true;
    status = current;
    if (complete || retryVisible) return;
    fillSavedStation(current);
    if (current.source === 'fault') {
      clearTransaction();
      complete = true;
      show('owner-service');
      notice('The Pico could not verify its setup state.', true);
    } else if (submitted) {
      const saved = current.source === 'consumer' && current.slot_state !== 'reconcile' &&
        BigInt(current.generation) >= submitted.expectedGeneration &&
        current.request_id_digest === submitted.requestDigest;
      if (saved) {
        clearTransaction();
        complete = true;
        show('owner-saved');
        notice(current.tls_ready === false ? 'The Pico saved your station settings. Readiness is pending trustworthy time or valid TLS.' : 'The Pico saved your station settings.');
      } else if (current.source === 'consumer' &&
                 BigInt(current.generation) >= submitted.expectedGeneration &&
                 current.request_id_digest !== submitted.requestDigest) {
        clearTransaction();
        complete = true;
        show('owner-service');
        notice('The saved result changed. Reload this page to check the Pico.', true);
      } else if (current.slot_state === 'terminal' ||
                 (current.slot_state === 'none' &&
                  BigInt(current.generation) < submitted.expectedGeneration)) {
        clearTransaction();
        retryVisible = true;
        show('owner-retry');
        notice('Setup was not saved. Check your settings and try again.', true);
      } else {
        showPending();
      }
    } else if (current.source === 'unprovisioned') {
      $('owner-submit').disabled = true;
      $('owner-identify').disabled = true;
      show('owner-wifi-first');
      notice('Connect the Pico to Wi-Fi before setting station details.');
    } else if (current.claim_available) {
      $('owner-submit').disabled = false;
      $('owner-identify').disabled = false;
      if (!$('owner-settings').hidden && wasClaimAvailable) return;
      show('owner-settings');
      notice(current.source === 'consumer' ?
        'Ready to update this Pico’s station details.' :
        'Ready to set this Pico’s station details.');
    } else {
      $('owner-submit').disabled = true;
      $('owner-identify').disabled = true;
      if (current.slot_state !== 'none') {
        show('owner-settings');
        notice(current.slot_state === 'terminal' ?
          'The previous setup attempt is finishing. This page will be ready shortly.' :
          'Setup is busy. This page will be ready when it finishes.');
      } else {
        show('owner-service');
        notice('Setup is temporarily unavailable on this Pico.', true);
      }
    }
  } catch {
    if (submitted && !saving && pending === submitted) showPending();
  } finally {
    if (!saving && !submitted && !submissions.pending) await hintTime();
    polling = false;
    progressControls();
    setTimeout(update, 1000);
  }
}

function identify() {
  return submissions.run(identifyWork,{message:'Identifying the Pico with its LED.'});
}
async function identifyWork() {
  if (!status?.claim_available || saving || submitted || complete) return;
  $('owner-identify').disabled = true;
  try {
    const result = await request('/api/owner/v1/identify', {version: 1,
      device_id: deviceId, boot_id: status.boot_id, request_id: hex(random(16))});
    if (result.version !== 1 || result.device_id !== deviceId ||
        result.pattern !== 'three_short_flashes') throw new Error('wrong Pico');
    notice('Watch for three quick LED flashes, repeated for about 10 seconds.');
  } catch {
    notice('Could not blink the LED. You can still save setup.', true);
  } finally {
    $('owner-identify').disabled = Boolean(saving || submitted || complete || retryVisible || !status?.claim_available);
  }
}

function submit(event) {
  event.preventDefault();
  return submissions.run(()=>submitWork(event),{message:'Applying saved station settings.'});
}
async function submitWork(event) {
  event.preventDefault();
  if (!status?.claim_available || status.source === 'unprovisioned' || saving ||
      submitted || complete || retryVisible) return;
  if (ownerProgress && progressState !== 'ready') return;
  const proposed = ownerProgress ? {ssid:'',password:'',callsign:ownerProgress.data.station.callsign,locator:ownerProgress.data.station.locator,powerDbm:ownerProgress.data.station.power_dbm} : settings();
  try { claimPlaintext(proposed).fill(0); validateStationIdentity(proposed.callsign, proposed.locator); }
  catch (error) {
    notice(error.message || 'Check the callsign, locator and reported WSPR power.', true);
    return;
  }
  const formHadFocus=document.activeElement?.closest('form')===$('owner-form');
  saving = true;
  $('owner-submit').disabled = true;
  $('owner-identify').disabled = true;
  let browserSecret;
  try {
    if (/[<>/]/.test(proposed.callsign)) {
      let support;
      try { support = await request('/api/owner/v1/wspr-support'); } catch {}
      if (!support || Object.keys(support).sort().join(',') !== 'max_station_token,planning,schema,station_encoding' || support.schema !== 'wspr-support/1' || support.station_encoding !== 'wspr_type123_auto' ||
          support.max_station_token !== 12 || support.planning !== 'automatic')
      {
        notice('This firmware has not confirmed Type 2/3 support. Your station draft is preserved.', true);
        return;
      }
    }
    // The P-256 point binds this one exchange and is never stored as an owner.
    const transaction = p256.keygen();
    const transactionPublic = p256.getPublicKey(transaction.secretKey, false);
    transaction.secretKey.fill(0);
    const pair = x25519.keygen();
    browserSecret = pair.secretKey;
    const browserNonce = hex(random(16));
    show('owner-checking',formHadFocus && (!document.activeElement || document.activeElement===document.body));
    notice('Saving station settings.');
    const started = await request(ownerProgress ? '/api/owner/v1/claim/progress/start' : '/api/owner/v1/claim/start', {
      version: 1, device_id: deviceId, owner_public_key: b64u(transactionPublic),
      browser_public_key: b64u(pair.publicKey), browser_nonce: browserNonce,
      profile_source: status.profile_source, generation: status.generation,
      ...(ownerProgress ? {progress_revision:ownerProgress.revision} : {}),
    });
    if (started.version !== 1 || started.device_id !== deviceId ||
        !/^[0-9a-f]{32}$/.test(started.boot_id) ||
        !/^[0-9a-f]{32}$/.test(started.slot_id) ||
        started.profile_source !== status.profile_source ||
        started.generation !== status.generation ||
        started.owner_key_sha256 !== hex(sha256(transactionPublic)) ||
        started.browser_public_key !== b64u(pair.publicKey) ||
        started.browser_nonce !== browserNonce ||
        fromB64u(started.pico_public_key, 32).length !== 32)
      throw new Error('start binding changed');
    const requestId = hex(random(16));
    const nonce = random(12);
    const fields = {
      origin: host, deviceId, bootId: started.boot_id, slotId: started.slot_id,
      ownerPublicKey: transactionPublic, browserPublicKey: pair.publicKey,
      picoPublicKey: fromB64u(started.pico_public_key, 32),
      browserNonce, requestId, source: started.profile_source,
      generation: started.generation,
    };
    const envelope = sealOwnerClaim(fields, browserSecret, nonce, proposed);
    browserSecret = undefined;
    submitted = {requestDigest: hex(sha256(fromHex(requestId, 16))),
      expectedGeneration: BigInt(started.generation) + 1n, accepted: false};
    resultTimedOut = false;
    // 90 s station trial + 60 s lost-result restart, with room for fetches.
    resultTimer = setTimeout(() => {
      resultTimedOut = true;
      if (submitted) showPending();
    }, 180000);
    // The result may be lost when station association changes; reconcile by
    // status without replaying this one encrypted POST.
    const result = await request('/api/owner/v1/claim/submit', {
      version: 1, device_id: deviceId, boot_id: started.boot_id,
      slot_id: started.slot_id, request_id: requestId, aead_nonce: b64u(nonce),
      ciphertext: envelope.ciphertext, tag: envelope.tag,
    });
    if (result.version === 1 && result.state === 'failed') {
      clearTransaction();
      retryVisible = true;
      show('owner-retry');
      notice('The Pico rejected these settings. Check them and try again.', true);
    } else if (result.version === 1 && result.state === 'checking' &&
               result.request_id_digest === submitted.requestDigest) {
      submitted.accepted = true;
      showPending();
    } else {
      throw new Error('unconfirmed submit reply');
    }
  } catch {
    if (submitted) {
      showPending();
    } else {
      retryVisible = true;
      show('owner-retry');
      notice('Could not start setup. Wait a moment, then try again.', true);
    }
  } finally {
    browserSecret?.fill(0);
    saving = false;
    $('owner-submit').disabled = Boolean(submitted || complete || retryVisible || !status?.claim_available);
    progressControls();
    $('owner-identify').disabled = Boolean(submitted || complete || retryVisible || !status?.claim_available);
  }
}

async function boot() {
  globalThis.addEventListener?.('beforeunload',event=>{if(progressEdits.size || submitted){event.preventDefault();event.returnValue='';}});
  $('owner-save-progress').onclick = saveOwnerProgress;
  $('owner-read-progress').onclick = () => submissions.run(async () => {
    if (progressBusy || saving || submitted) return;
    progressBusy=true;progressControls();
    try {await readOwnerProgress(false);notice('Review saved progress. Matching values do not identify which earlier request committed.');}
    catch(error) {progressState='readback';notice(error.message,true);}
    finally {progressBusy=false;progressControls();}
  },{message:'Reading saved station fields.'});
  $('owner-review-progress').onclick = () => {if(progressState==='review'){progressState='ready';progressControls();}};
  $('owner-form').addEventListener('input', event => {
    const key = {'owner-callsign':'callsign','owner-locator':'locator','owner-power':'power_dbm'}[event.target.id];
    if (key) {
      progressEdits.set(key,++progressEditSerial);
      const message=$(event.target.id+'-progress-result');
      if(message){message.textContent='Unsaved edit.';message.classList.toggle('error',false);event.target.setAttribute('aria-invalid','false');}
    }
  });
  for (const name of ['owner-callsign', 'owner-locator', 'owner-power']) {
    $(name).addEventListener('input', () => { formEdited = true; });
    $(name).addEventListener('change', () => { formEdited = true; });
  }
  $('owner-identify').addEventListener('click', identify);
  $('owner-retry-button').addEventListener('click', () => {
    if (submissions.pending) { notice('Wait for the current Pico request to finish. No additional action was sent.',true); return; }
    clearTransaction();
    retryVisible = false;
    // Recheck the slot before permitting a new POST; the old status may predate rejection.
    if (status) status = {...status, claim_available: false};
    $('owner-submit').disabled = true;
    $('owner-identify').disabled = true;
    show('owner-settings');
    notice('Checking when this Pico is ready.');
    update();
  });
  $('owner-form').addEventListener('submit', submit);
  if (location.origin !== host || !available() || !p256 ||
      typeof AbortController !== 'function') {
    show('owner-browser');
    notice('This window cannot run encrypted setup. Open the Pico page in a regular browser.', true);
    return;
  }
  try {
    // The document's last TCP acknowledgement may still occupy the AP slot.
    // Retry this initial read only; station submissions are never replayed.
    let publicStatus;
    for (let attempt = 0; attempt < 3; attempt++) {
      try { publicStatus = await request('/api/owner/v1/public-status'); break; }
      catch (error) {
        if (attempt === 2) throw error;
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
    }
    if (!publicStatus || !/^[0-9a-f]{32}$/.test(publicStatus.device_id))
      throw new Error('invalid Pico identity');
    deviceId = publicStatus.device_id;
    if (!validStatus(publicStatus)) throw new Error('invalid Pico state');
    status = publicStatus;
    await titleFromDevice('Station setup', deviceId);
    fillSavedStation(status);
    if (status.claim_available) await readOwnerProgress(true);
    $('device').textContent = 'Pico ' + deviceId.slice(-6);
    if (status.source === 'unprovisioned') {
      show('owner-wifi-first');
      notice('Connect the Pico to Wi-Fi before setting station details.');
    } else if (status.claim_available) {
      $('owner-submit').disabled = false;
      $('owner-identify').disabled = false;
      show('owner-settings');
      notice(status.source === 'consumer' ?
        'Ready to update this Pico’s station details.' :
        'Ready to set this Pico’s station details.');
    } else {
      show('owner-service');
      notice('Setup is temporarily unavailable on this Pico.', true);
    }
    progressControls();
    update();
  } catch {
    notice('Could not verify this Pico. Reconnect to its Wi-Fi and reload.', true);
  }
}
boot();

// Cross-document commissioning links must not silently discard edited fields.
globalThis.addEventListener?.('beforeunload', event => {
  if (formEdited) { event.preventDefault(); event.returnValue = ''; }
});

globalThis.addEventListener?.('pagehide',()=>submissions.suspend());
globalThis.addEventListener?.('pageshow',()=>submissions.resume());

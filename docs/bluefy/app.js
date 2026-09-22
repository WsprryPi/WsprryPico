"use strict";
const form = document.querySelector("#provisioning");
const fields = form.querySelector("fieldset");
const status = document.querySelector("#status");
const connect = document.querySelector("#connect");
const cancel = document.querySelector("#cancel");
const authorize = document.querySelector("#authorize");
const showAccessPassword = document.querySelector("#show-access-password");
const releaseLabel = document.querySelector("#release");
const releaseMeta = document.querySelector('meta[name="wsprry-bluefy-release"]');
const releaseFiles = Object.freeze([
  "app.js", "bluefy.js", "manifest.webmanifest", "style.css", "sw.js"
]);
let client = null;
let active = false;
let releaseReady = false;

function releaseFailure(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}
function hexadecimal(bytes) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
async function verifyAsset(name, record) {
  if (!record || !Number.isSafeInteger(record.bytes) || record.bytes < 1 ||
      !/^[0-9a-f]{64}$/.test(record.sha256)) releaseFailure("release_manifest_invalid");
  const response = await fetch(`./${name}`, {cache: "reload", credentials: "omit"});
  if (!response.ok) releaseFailure("release_asset_unavailable");
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (bytes.byteLength !== record.bytes) releaseFailure("release_asset_size");
  const digest = hexadecimal(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)));
  bytes.fill(0);
  if (digest !== record.sha256) releaseFailure("release_asset_integrity");
}
async function waitForWorker(registration, release) {
  const worker = registration.installing || registration.waiting || registration.active;
  if (!worker) releaseFailure("offline_cache_unavailable");
  for (let attempt = 0;
       worker.state !== "activated" && worker.state !== "redundant" && attempt < 200;
       ++attempt)
    await new Promise((resolve) => setTimeout(resolve, 50));
  if (worker.state !== "activated") releaseFailure("offline_cache_unavailable");
  const ready = await navigator.serviceWorker.ready;
  if (!ready.active ||
      new URL(ready.active.scriptURL).searchParams.get("release") !== release)
    releaseFailure("offline_cache_revision");
}
async function prepareOfflineCache(release) {
  if (!("serviceWorker" in navigator))
    return {ready: false, code: "offline_cache_unavailable"};
  try {
    const serviceWorker = navigator.serviceWorker;
    if (!serviceWorker)
      return {ready: false, code: "offline_cache_unavailable"};
    const attempt = async () => {
      const registration = await serviceWorker.register(
        `./sw.js?release=${release}`, {scope: "./", updateViaCache: "none"});
      await waitForWorker(registration, release);
      return {ready: true, code: null};
    };
    return await Promise.race([attempt(), new Promise((resolve) =>
      setTimeout(() => resolve({ready: false, code: "offline_cache_timeout"}), 12000))]);
  } catch (error) {
    return {ready: false, code: message(error)};
  }
}
async function prepareRelease() {
  if (location.protocol !== "https:") releaseFailure("https_required");
  if (typeof crypto !== "object" || !crypto.subtle)
    releaseFailure("release_integrity_unavailable");
  const response = await fetch("./release-manifest.json", {
    cache: "no-store", credentials: "omit"
  });
  if (!response.ok) releaseFailure("release_manifest_unavailable");
  const manifest = await response.json();
  if (!manifest || manifest.version !== 1 || manifest.protocol !== 1 ||
      !/^[0-9a-f]{64}$/.test(manifest.release) ||
      !releaseMeta || releaseMeta.content !== manifest.release ||
      !manifest.files || Object.keys(manifest.files).sort().join(",") !== releaseFiles.join(","))
    releaseFailure("release_manifest_invalid");
  for (const name of releaseFiles) await verifyAsset(name, manifest.files[name]);
  const offline = await prepareOfflineCache(manifest.release);
  releaseLabel.textContent = offline.ready
    ? `${manifest.release.slice(0, 12)} · protocol 1 · offline ready`
    : `${manifest.release.slice(0, 12)} · protocol 1 · online verified`;
  releaseReady = true;
  connect.disabled = false;
  status.value = offline.ready
    ? "Release verified. Ready to select the identified Pico."
    : `Release verified for online use. Offline cache unavailable (${offline.code}); ` +
      "keep Internet access until this session is finished.";
}

function values() {
  const data = new FormData(form);
  return Object.fromEntries(data.entries());
}
function setAccessPasswordVisible(visible) {
  form.elements.access_password.type = visible ? "text" : "password";
  showAccessPassword.textContent = visible ? "Hide local password" : "Show local password";
  showAccessPassword.setAttribute("aria-pressed", visible ? "true" : "false");
}
function setAccessPasswordEnabled(enabled) {
  form.elements.access_password.disabled = !enabled;
  showAccessPassword.disabled = !enabled;
  if (!enabled) setAccessPasswordVisible(false);
}
function clearSecrets() {
  for (const name of ["access_password", "password", "server_certificate", "server_private_key", "client_ca"])
    form.elements[name].value = "";
  setAccessPasswordVisible(false);
}
function message(error) {
  return error && error.code ? error.code : "operation_failed";
}
showAccessPassword.addEventListener("click", () => {
  if (!showAccessPassword.disabled)
    setAccessPasswordVisible(form.elements.access_password.type === "password");
});
connect.addEventListener("click", async () => {
  if (active || !releaseReady) return;
  if (client) client.disconnect();
  client = null;
  fields.disabled = true;
  clearSecrets();
  form.elements.device_id.value = "";
  setAccessPasswordEnabled(false);
  authorize.disabled = true;
  active = true;
  connect.disabled = true;
  status.value = "Waiting for Bluefy device selection…";
  try {
    client = new WsprryBluefy.Client(navigator.bluetooth, crypto);
    const identity = await client.connect();
    form.elements.device_id.value = identity.device_id;
    setAccessPasswordEnabled(true);
    authorize.disabled = false;
    connect.disabled = false;
    status.value = `Selected ${identity.device_id}; generation ${identity.generation}. Confirm before authorizing.`;
  } catch (error) {
    if (client) client.disconnect();
    client = null;
    form.elements.device_id.value = "";
    setAccessPasswordEnabled(false);
    authorize.disabled = true;
    status.value = `Connection failed: ${message(error)}.`;
    connect.disabled = !releaseReady;
  } finally {
    active = false;
  }
});
authorize.addEventListener("click", async () => {
  if (!client || active || !validDeviceSelection()) return;
  active = true;
  connect.disabled = true;
  authorize.disabled = true;
  status.value = `Authorizing the explicitly selected Pico ${form.elements.device_id.value}…`;
  try {
    await client.authorize(form.elements.access_password.value);
    form.elements.access_password.value = "";
    setAccessPasswordEnabled(false);
    fields.disabled = false;
    status.value = `Authorized on ${form.elements.device_id.value}; generation ${client.generation}.`;
  } catch (error) {
    client.disconnect();
    client = null;
    form.elements.device_id.value = "";
    clearSecrets();
    setAccessPasswordEnabled(false);
    connect.disabled = !releaseReady;
    status.value = `Authorization failed: ${message(error)}.`;
  } finally {
    active = false;
  }
});

function validDeviceSelection() {
  return /^[0-9a-f]{32}$/.test(form.elements.device_id.value);
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!client || active) return;
  const operationClient = client;
  active = true;
  fields.disabled = true;
  status.value = "Validating and transferring the replacement profile…";
  try {
    const result = await operationClient.provision(values());
    if (client !== operationClient) return;
    status.value = `Profile generation ${result.generation} committed.`;
    clearSecrets();
  } catch (error) {
    if (client === operationClient)
      status.value = `Provisioning failed: ${message(error)}.`;
  } finally {
    if (client === operationClient) {
      fields.disabled = false;
      active = false;
    }
  }
});
cancel.addEventListener("click", () => {
  if (client) client.disconnect();
  client = null;
  active = false;
  fields.disabled = true;
  connect.disabled = !releaseReady;
  authorize.disabled = true;
  form.elements.device_id.value = "";
  setAccessPasswordEnabled(false);
  clearSecrets();
  status.value = "Cancelled and disconnected.";
});
window.addEventListener("pagehide", () => {
  clearSecrets();
  if (client) client.disconnect();
});

prepareRelease().catch((error) => {
  authorize.disabled = true;
  setAccessPasswordEnabled(false);
  releaseReady = false;
  connect.disabled = true;
  fields.disabled = true;
  clearSecrets();
  status.value = `Release unavailable: ${message(error)}.`;
});

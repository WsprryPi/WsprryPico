"use strict";
const form = document.querySelector("#provisioning");
const fields = form.querySelector("fieldset");
const status = document.querySelector("#status");
const connect = document.querySelector("#connect");
const cancel = document.querySelector("#cancel");
let client = null;
let active = false;

function values() {
  const data = new FormData(form);
  return Object.fromEntries(data.entries());
}
function clearSecrets() {
  for (const name of ["access_password", "password", "server_certificate", "server_private_key", "client_ca"])
    form.elements[name].value = "";
}
function message(error) {
  return error && error.code ? error.code : "operation_failed";
}
connect.addEventListener("click", async () => {
  if (active) return;
  active = true;
  connect.disabled = true;
  status.value = "Waiting for Bluefy device selection…";
  try {
    client = new WsprryBluefy.Client(navigator.bluetooth, crypto);
    const identity = await client.connect(form.elements.device_id.value);
    await client.authorize(form.elements.access_password.value);
    form.elements.access_password.value = "";
    fields.disabled = false;
    status.value = `Authorized on ${identity.device_id}; generation ${identity.generation}.`;
  } catch (error) {
    if (client) client.disconnect();
    client = null;
    status.value = `Connection failed: ${message(error)}.`;
    connect.disabled = false;
  } finally {
    active = false;
  }
});
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
  connect.disabled = false;
  clearSecrets();
  status.value = "Cancelled and disconnected.";
});
window.addEventListener("pagehide", () => {
  clearSecrets();
  if (client) client.disconnect();
});

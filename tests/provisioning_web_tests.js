"use strict";
const assert = require("assert");
const {canonicalProfile, Client, FRAGMENT_BYTES, GATT_FRAME_BYTES, MAX_COMMAND_BYTES,
  MAX_STATUS_BYTES, frames, FrameReceiver} = require("../src/provisioning/web/bluefy.js");
const device = "a".repeat(32);

function profile(change) {
  return Object.assign({
    device_id: device,
    ssid: "test-network",
    password: "test-password",
    time_server: "pool.ntp.org",
    hostname: "WsprryPico-010203.LOCAL.",
    port: 18443,
    server_certificate: "-----BEGIN CERTIFICATE-----\nSERVER\n-----END CERTIFICATE-----\n",
    server_private_key: "-----BEGIN PRIVATE KEY-----\nKEY\n-----END PRIVATE KEY-----\n",
    client_ca: "-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----\n"
  }, change || {});
}
function cryptoFixture() {
  let next = 1;
  return {getRandomValues(bytes) { bytes.fill(0); bytes[bytes.length - 1] = next++; return bytes; }};
}
class Characteristic {
  constructor(value) {
    this.value = value;
    this.listeners = [];
    this.commands = [];
    this.writtenSizes = [];
    this.emittedSizes = [];
    this.respond = true;
    this.receiver = new FrameReceiver(MAX_COMMAND_BYTES);
  }
  async readValue() { const bytes = new TextEncoder().encode(JSON.stringify(this.value)); return new DataView(bytes.buffer); }
  async startNotifications() { return this; }
  addEventListener(_, callback) { this.listeners.push(callback); }
  removeEventListener(_, callback) { this.listeners = this.listeners.filter((item) => item !== callback); }
  emitBytes(bytes) {
    this.emittedSizes.push(bytes.byteLength);
    const value = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (const listener of this.listeners) listener({target: {value}});
  }
  emit(value) {
    const encoded = new TextEncoder().encode(JSON.stringify(value));
    for (const frame of frames(encoded)) this.emitBytes(frame);
    encoded.fill(0);
  }
  async writeValueWithResponse(bytes) {
    this.writtenSizes.push(bytes.byteLength);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const encoded = this.receiver.receive(view);
    if (!encoded) return false;
    const command = JSON.parse(new TextDecoder().decode(encoded)); encoded.fill(0);
    this.commands.push(command);
    if (!this.respond) return true;
    const response = {request_id: command.request_id, ok: true};
    if (command.operation === "apply")
      response.generation = this.applyGeneration === undefined
        ? command.expected_generation + 1
        : this.applyGeneration;
    queueMicrotask(() => this.peer.emit(response));
    return true;
  }
}
function bluetoothFixture(observedDevice = device, generation = 0) {
  const identity = new Characteristic({device_id: observedDevice, generation});
  const command = new Characteristic();
  const status = new Characteristic();
  command.peer = status;
  const characteristics = new Map();
  const api = require("../src/provisioning/web/bluefy.js");
  characteristics.set(api.UUIDS.identity, identity);
  characteristics.set(api.UUIDS.command, command);
  characteristics.set(api.UUIDS.status, status);
  const gatt = {connected: false, async connect() { this.connected = true; return this; },
    disconnect() { this.connected = false; },
    async getPrimaryService() { return {getCharacteristic: async (uuid) => characteristics.get(uuid)}; }};
  const deviceObject = {
    gatt,
    listeners: new Map(),
    addEventListener(name, callback) { this.listeners.set(name, callback); },
    removeEventListener(name, callback) {
      if (this.listeners.get(name) === callback) this.listeners.delete(name);
    },
    emit(name) {
      const callback = this.listeners.get(name);
      if (callback) callback({target: this});
    }
  };
  return {bluetooth: {requestDevice: async () => deviceObject}, identity, command, status, gatt,
    device: deviceObject};
}
async function rejectsCode(callback, code) {
  try { await callback(); assert.fail("expected rejection"); }
  catch (error) { assert.strictEqual(error.code, code); }
}

async function run() {
  const canonical = canonicalProfile(profile());
  assert(canonical.value.includes('"hostname":"wsprrypico-010203.local"'));
  canonical.bytes.fill(0);
  for (const changed of [
    {device_id: "A".repeat(32)}, {ssid: ""}, {password: "short"},
    {time_server: "127.0.0.1"}, {hostname: "evil.example"}, {port: 0},
    {server_certificate: "bad"}, {server_private_key: "bad"}, {client_ca: "bad"}
  ]) assert.throws(() => canonicalProfile(profile(changed)));
  assert.throws(() => canonicalProfile(profile({server_certificate:
    "-----BEGIN CERTIFICATE-----\n" + "A".repeat(7100) + "\n-----END CERTIFICATE-----\n"})),
  (error) => error.code === "server_certificate");
  const largeCertificate = "-----BEGIN CERTIFICATE-----\n" + "A".repeat(2940) +
    "\n-----END CERTIFICATE-----\n";
  const largeKey = "-----BEGIN PRIVATE KEY-----\n" + "B".repeat(1900) +
    "\n-----END PRIVATE KEY-----\n";
  assert.throws(() => canonicalProfile(profile({server_certificate: largeCertificate,
    server_private_key: largeKey, client_ca: largeCertificate})),
  (error) => error.code === "profile_oversize");
  for (const time_server of ["1.01.1.1", "224.0.0.1", "0x7f.0.0.1", "1..example"])
    assert.throws(() => canonicalProfile(profile({time_server})));

  await rejectsCode(() => new Client(null, cryptoFixture()).connect(device),
                    "web_bluetooth_unavailable");
  const wrong = bluetoothFixture("b".repeat(32));
  await rejectsCode(() => new Client(wrong.bluetooth, cryptoFixture()).connect(device),
                    "wrong_device");
  assert.strictEqual(wrong.gatt.connected, false);
  const badIdentity = bluetoothFixture();
  badIdentity.identity.readValue = async () => {
    const bytes = new TextEncoder().encode("{not-json");
    return new DataView(bytes.buffer);
  };
  await rejectsCode(() => new Client(badIdentity.bluetooth, cryptoFixture()).connect(device),
                    "identity_format");
  assert.strictEqual(badIdentity.gatt.connected, false);

  const fixture = bluetoothFixture();
  const client = new Client(fixture.bluetooth, cryptoFixture(), {timeoutMs: 50});
  assert.deepStrictEqual(await client.connect(), {device_id: device, generation: 0});
  await rejectsCode(() => client.provision(profile()), "authentication_required");
  assert.deepStrictEqual(await client.authorize("wspr-0a60df"), {authorized: true});
  const result = await client.provision(profile());
  assert.deepStrictEqual(result, {generation: 1});
  assert.strictEqual(client.pending.size, 0);
  const writes = fixture.command.commands.filter((command) => command.operation === "write");
  assert(writes.length > 1);
  let offset = 0;
  for (let i = 0; i < writes.length; ++i) {
    assert.strictEqual(writes[i].offset, offset);
    const count = Buffer.from(writes[i].payload, "base64").length;
    assert(count <= FRAGMENT_BYTES && count > 0);
    offset += count;
    assert.strictEqual(writes[i].final, i === writes.length - 1);
  }
  assert.strictEqual(fixture.command.commands[0].operation, "authorize");
  assert.strictEqual(fixture.command.commands[1].operation, "open");
  assert.strictEqual(fixture.command.commands.at(-1).operation, "apply");
  assert(fixture.command.commands.every((command) => command.device_id === device));
  const commandSizes = fixture.command.commands.map((command) =>
    new TextEncoder().encode(JSON.stringify(command)).length);
  assert(commandSizes.every((size) => size <= MAX_COMMAND_BYTES));
  assert(commandSizes.some((size) => size > 20),
    "mock GATT must not be mistaken for default-ATT-MTU command evidence");
  assert(fixture.command.writtenSizes.every((size) => size <= GATT_FRAME_BYTES));
  assert(fixture.status.emittedSizes.every((size) => size <= GATT_FRAME_BYTES));
  assert(fixture.status.emittedSizes.some((size) => size > 20),
    "mock GATT must not be mistaken for default-ATT-MTU status evidence");

  const oversizedFixture = bluetoothFixture();
  const oversizedClient = new Client(
    oversizedFixture.bluetooth, cryptoFixture(), {timeoutMs: 10});
  await oversizedClient.connect(device);
  await oversizedClient.authorize("wspr-0a60df");
  oversizedFixture.command.respond = false;
  const oversizedRequest = "d".repeat(32);
  const pendingOversizedStatus = oversizedClient.exchange({
    version: 1, operation: "cancel", request_id: oversizedRequest,
    session_id: "e".repeat(32), device_id: device
  });
  const oversizedStatus = new TextEncoder().encode(JSON.stringify({
    request_id: oversizedRequest, ok: true, padding: "x".repeat(MAX_STATUS_BYTES)
  }));
  assert(oversizedStatus.byteLength > MAX_STATUS_BYTES);
  for (const frame of frames(oversizedStatus)) oversizedFixture.status.emitBytes(frame);
  await rejectsCode(() => pendingOversizedStatus, "timeout");
  assert.strictEqual(oversizedClient.pending.size, 0);
  oversizedClient.disconnect();

  const unchangedFixture = bluetoothFixture(device, 1);
  unchangedFixture.command.applyGeneration = 1;
  const unchangedClient = new Client(unchangedFixture.bluetooth, cryptoFixture(), {timeoutMs: 50});
  await unchangedClient.connect(device);
  await unchangedClient.authorize("wspr-0a60df");
  assert.deepStrictEqual(await unchangedClient.provision(profile()), {generation: 1});

  const duplicateFixture = bluetoothFixture();
  const duplicateClient = new Client(duplicateFixture.bluetooth, cryptoFixture(), {timeoutMs: 50});
  await duplicateClient.connect(device);
  await duplicateClient.authorize("wspr-0a60df");
  const originalWrite = duplicateFixture.command.writeValueWithResponse.bind(duplicateFixture.command);
  duplicateFixture.command.writeValueWithResponse = async (bytes) => {
    const before = duplicateFixture.command.commands.length;
    await originalWrite(bytes);
    if (duplicateFixture.command.commands.length !== before) {
      const command = duplicateFixture.command.commands.at(-1);
      queueMicrotask(() => duplicateFixture.status.emit({request_id: command.request_id, ok: true,
        replayed: true}));
    }
  };
  await duplicateClient.cancel("1".repeat(32));
  assert.strictEqual(duplicateClient.pending.size, 0);

  const timeoutFixture = bluetoothFixture();
  const timeoutClient = new Client(timeoutFixture.bluetooth, cryptoFixture(), {timeoutMs: 5});
  await timeoutClient.connect(device);
  await timeoutClient.authorize("wspr-0a60df");
  timeoutFixture.command.respond = false;
  await rejectsCode(() => timeoutClient.cancel("1".repeat(32)), "timeout");
  assert.strictEqual(timeoutClient.pending.size, 0);

  const invalidResponseFixture = bluetoothFixture();
  const invalidResponseClient = new Client(invalidResponseFixture.bluetooth, cryptoFixture(),
                                           {timeoutMs: 5});
  await invalidResponseClient.connect(device);
  await invalidResponseClient.authorize("wspr-0a60df");
  invalidResponseFixture.command.respond = false;
  const invalidResponse = invalidResponseClient.cancel("3".repeat(32));
  await new Promise((resolve) => setImmediate(resolve));
  const invalidRequest = invalidResponseFixture.command.commands.at(-1).request_id;
  invalidResponseFixture.status.emit({request_id: invalidRequest, ok: "true"});
  await rejectsCode(() => invalidResponse, "timeout");

  const disconnectFixture = bluetoothFixture();
  const disconnectClient = new Client(disconnectFixture.bluetooth, cryptoFixture(),
                                      {timeoutMs: 50});
  await disconnectClient.connect(device);
  await disconnectClient.authorize("wspr-0a60df");
  disconnectFixture.command.respond = false;
  const disconnected = disconnectClient.cancel("4".repeat(32));
  disconnectClient.disconnect();
  await rejectsCode(() => disconnected, "disconnected");
  assert.strictEqual(disconnectClient.pending.size, 0);

  const nativeDisconnectFixture = bluetoothFixture();
  const nativeDisconnectClient = new Client(nativeDisconnectFixture.bluetooth, cryptoFixture(),
                                            {timeoutMs: 50});
  await nativeDisconnectClient.connect(device);
  await nativeDisconnectClient.authorize("wspr-0a60df");
  nativeDisconnectFixture.command.respond = false;
  const nativeDisconnected = nativeDisconnectClient.cancel("5".repeat(32));
  await new Promise((resolve) => setImmediate(resolve));
  nativeDisconnectFixture.gatt.connected = false;
  nativeDisconnectFixture.device.emit("gattserverdisconnected");
  await rejectsCode(() => nativeDisconnected, "bluetooth_disconnected");
  assert.strictEqual(nativeDisconnectClient.pending.size, 0);

  const malformedFixture = bluetoothFixture();
  const malformedClient = new Client(malformedFixture.bluetooth, cryptoFixture(), {timeoutMs: 5});
  await malformedClient.connect(device);
  await malformedClient.authorize("wspr-0a60df");
  malformedFixture.command.respond = false;
  const pending = malformedClient.cancel("2".repeat(32));
  malformedFixture.status.emit("not-json-object");
  await rejectsCode(() => pending, "timeout");
  malformedClient.disconnect();
  assert.strictEqual(malformedFixture.gatt.connected, false);
  assert.strictEqual(malformedClient.pending.size, 0);
  console.log("provisioning web tests passed");
}
run().catch((error) => { console.error(error); process.exit(1); });

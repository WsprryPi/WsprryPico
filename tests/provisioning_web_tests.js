"use strict";
const assert = require("assert");
const {canonicalProfile, Client, FRAGMENT_BYTES, GATT_FRAME_BYTES, MAX_COMMAND_BYTES,
  MAX_STATUS_BYTES, WTP_SEGMENT_BYTES, frames, FrameReceiver, crc32c, wtpFrame,
  WtpReceiver} = require("../src/provisioning/web/bluefy.js");
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
    if (command.operation === "identify") response.identified = true;
    if (command.operation === "time_challenge") {
      response.nonce = command.nonce;
      response.sampled_monotonic_ns = "1000000000";
    }
    if (command.operation === "time_submit") response.accepted = true;
    if (command.operation === "field_status") {
      response.time_source = "controller";
      response.time_age_ns = "0";
      response.time_uncertainty_ns = "251000000";
      response.time_disagreement = false;
      response.indicator = "off";
      response.indicator_fault = false;
    }
    queueMicrotask(() => this.peer.emit(response));
    return true;
  }
}
class WtpCharacteristic extends Characteristic {
  constructor() {
    super();
    this.receiver = new WtpReceiver();
  }
  emitWtp(value) {
    const encoded = wtpFrame(value);
    for (let offset = 0; offset < encoded.length; offset += 13)
      this.emitBytes(encoded.subarray(offset, Math.min(encoded.length, offset + 13)));
    encoded.fill(0);
  }
  async writeValueWithResponse(bytes) {
    this.writtenSizes.push(bytes.byteLength);
    for (const command of this.receiver.receive(
      new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength))) {
      this.commands.push(command);
      if (!this.respond) continue;
      const body = command.op === "HELLO"
        ? {selected_version: "WTP/1", device_id: device, boot_id: "b".repeat(32),
          product: "WsprryPico", firmware_version: "test"}
        : {state: "empty", output_active: false};
      queueMicrotask(() => this.peer.emitWtp({type: "response", protocol: "WTP/1",
        session_id: command.session_id, request_id: command.request_id,
        op: command.op, ok: true, body}));
    }
    return true;
  }
}
function bluetoothFixture(observedDevice = device, generation = 0) {
  const identity = new Characteristic({device_id: observedDevice, generation});
  const command = new Characteristic();
  const status = new Characteristic();
  const wtpCommand = new WtpCharacteristic();
  const wtpStatus = new WtpCharacteristic();
  command.peer = status;
  wtpCommand.peer = wtpStatus;
  const characteristics = new Map();
  const api = require("../src/provisioning/web/bluefy.js");
  characteristics.set(api.UUIDS.identity, identity);
  characteristics.set(api.UUIDS.command, command);
  characteristics.set(api.UUIDS.status, status);
  characteristics.set(api.UUIDS.wtpCommand, wtpCommand);
  characteristics.set(api.UUIDS.wtpStatus, wtpStatus);
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
  return {bluetooth: {requestDevice: async () => deviceObject}, identity, command, status,
    wtpCommand, wtpStatus, gatt, device: deviceObject};
}
async function rejectsCode(callback, code) {
  try { await callback(); assert.fail("expected rejection"); }
  catch (error) { assert.strictEqual(error.code, code); }
}

async function run() {
  assert.strictEqual(crc32c(new TextEncoder().encode("123456789")), 0xe3069283);
  const combinedReceiver = new WtpReceiver();
  const firstFrame = wtpFrame({one: 1}), secondFrame = wtpFrame({two: 2});
  const combined = new Uint8Array(firstFrame.length + secondFrame.length);
  combined.set(firstFrame); combined.set(secondFrame, firstFrame.length);
  assert.deepStrictEqual(combinedReceiver.receive(new DataView(combined.buffer)),
    [{one: 1}, {two: 2}]);
  const corrupt = wtpFrame({corrupt: true});
  corrupt[corrupt.length - 1] ^= 1;
  assert.throws(() => new WtpReceiver().receive(new DataView(corrupt.buffer)),
    (error) => error.code === "wtp_crc");
  firstFrame.fill(0); secondFrame.fill(0); combined.fill(0);
  corrupt.fill(0);

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
  assert.deepStrictEqual(await client.identify(), {identified: true});
  assert.deepStrictEqual(await client.synchronizeTime(1800000000000), {accepted: true});
  assert.strictEqual((await client.fieldStatus()).time_source, "controller");
  const hello = await client.enableLocalControl();
  assert.strictEqual(hello.device_id, device);
  assert.deepStrictEqual(await client.wtpExchange("STATUS", {}),
    {state: "empty", output_active: false});
  assert.deepStrictEqual(fixture.wtpCommand.commands.map((item) => item.op), ["HELLO", "STATUS"]);
  assert(fixture.wtpCommand.writtenSizes.every((size) => size <= WTP_SEGMENT_BYTES));
  fixture.wtpCommand.respond = false;
  const pendingWtp = client.wtpExchange("PING", {token: "one-at-a-time"});
  await new Promise((resolve) => setImmediate(resolve));
  await rejectsCode(() => client.wtpExchange("CAPS", {}), "wtp_busy");
  const pendingCommand = fixture.wtpCommand.commands.at(-1);
  fixture.wtpStatus.emitWtp({type: "response", protocol: "WTP/1",
    session_id: pendingCommand.session_id, request_id: pendingCommand.request_id,
    op: pendingCommand.op, ok: true, body: {token: "one-at-a-time"}});
  assert.deepStrictEqual(await pendingWtp, {token: "one-at-a-time"});
  fixture.wtpCommand.respond = true;
  fixture.command.respond = false;
  const invalidFieldStatus = client.fieldStatus();
  await new Promise((resolve) => setImmediate(resolve));
  const fieldRequest = fixture.command.commands.at(-1);
  fixture.status.emit({request_id: fieldRequest.request_id, ok: true});
  await rejectsCode(() => invalidFieldStatus, "field_status_response");
  fixture.command.respond = true;
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
  assert(fixture.command.commands.findIndex((command) => command.operation === "open") > 0);
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

  const corruptWtpFixture = bluetoothFixture();
  const corruptWtpClient = new Client(corruptWtpFixture.bluetooth, cryptoFixture(), {timeoutMs: 50});
  await corruptWtpClient.connect(device);
  await corruptWtpClient.authorize("wspr-0a60df");
  await corruptWtpClient.enableLocalControl();
  corruptWtpFixture.wtpCommand.respond = false;
  const corruptWtpPending = corruptWtpClient.wtpExchange("STATUS", {});
  await new Promise((resolve) => setImmediate(resolve));
  const badWtpResponse = wtpFrame({invalid: true});
  badWtpResponse[badWtpResponse.length - 1] ^= 1;
  corruptWtpFixture.wtpStatus.emitBytes(badWtpResponse);
  badWtpResponse.fill(0);
  await rejectsCode(() => corruptWtpPending, "wtp_crc");
  assert.strictEqual(corruptWtpFixture.gatt.connected, false);

  const returnedStatusFixture = bluetoothFixture();
  const returnedStatus = new Characteristic();
  returnedStatusFixture.status.startNotifications = async () => returnedStatus;
  returnedStatusFixture.command.peer = returnedStatus;
  const returnedStatusClient = new Client(returnedStatusFixture.bluetooth, cryptoFixture(),
                                          {timeoutMs: 50});
  await returnedStatusClient.connect(device);
  assert.deepStrictEqual(await returnedStatusClient.authorize("wspr-0a60df"),
                         {authorized: true});
  assert.strictEqual(returnedStatusClient.trace.events, 1);
  assert.strictEqual(returnedStatusFixture.status.listeners.length, 0);
  returnedStatusClient.disconnect();
  assert.strictEqual(returnedStatus.listeners.length, 0);

  const silentFixture = bluetoothFixture();
  silentFixture.command.respond = false;
  const silentClient = new Client(silentFixture.bluetooth, cryptoFixture(), {timeoutMs: 5});
  await silentClient.connect(device);
  await assert.rejects(() => silentClient.authorize("wspr-0a60df"), (error) => {
    assert.strictEqual(error.code, "timeout");
    assert.match(error.detail,
      /^writes [0-9]+\/[0-9]+; events 0; frames 0; messages 0; matched 0; last none$/);
    assert(!error.detail.includes("wspr-0a60df"));
    return true;
  });
  silentClient.disconnect();

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

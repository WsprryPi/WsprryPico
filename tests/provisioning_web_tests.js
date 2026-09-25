"use strict";
const assert = require("assert");
const {canonicalProfile, Client, FRAGMENT_BYTES, GATT_FRAME_BYTES, MAX_COMMAND_BYTES,
  MAX_STATUS_BYTES, WTP_SEGMENT_BYTES, frames, FrameReceiver, crc32c, wtpFrame,
  WtpReceiver} = require("../src/provisioning/web/bluefy.js");
const device = "a".repeat(32);

function profile(change) {
  return Object.assign({
    device_id: device,
    access_password: "wspr-0a60df",
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
  constructor(value, label = "", notificationLog = []) {
    this.value = value;
    this.label = label;
    this.notificationLog = notificationLog;
    this.notificationStarts = 0;
    this.notificationStops = 0;
    this.notificationsActive = false;
    this.listeners = [];
    this.commands = [];
    this.writtenSizes = [];
    this.writtenBufferSizes = [];
    this.writtenOffsets = [];
    this.writeKinds = [];
    this.emittedSizes = [];
    this.respond = true;
    this.rejectEmptyAuthorization = false;
    this.rejectWtpCarrier = false;
    this.wtpCarrier = "field_status";
    this.wtpCommandCarrier = "field_command";
    this.onWtpCarrier = null;
    this.receiver = new FrameReceiver(MAX_COMMAND_BYTES);
    this.wtpReceiver = new WtpReceiver();
    this.wtpMode = false;
    this.wtpRespond = true;
    this.wtpCommands = [];
  }
  async readValue() { const bytes = new TextEncoder().encode(JSON.stringify(this.value)); return new DataView(bytes.buffer); }
  async startNotifications() {
    ++this.notificationStarts;
    this.notificationsActive = true;
    this.notificationLog.push(`${this.label}:start`);
    return this;
  }
  async stopNotifications() {
    ++this.notificationStops;
    this.notificationsActive = false;
    this.notificationLog.push(`${this.label}:stop`);
    return this;
  }
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
  async write(bytes, kind) {
    this.writtenSizes.push(bytes.byteLength);
    this.writtenBufferSizes.push(bytes.buffer.byteLength);
    this.writtenOffsets.push(bytes.byteOffset);
    this.writeKinds.push(kind);
    if (this.wtpMode) {
      for (const command of this.wtpReceiver.receive(
        new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength))) {
        this.wtpCommands.push(command);
        if (!this.wtpRespond) continue;
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
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const encoded = this.receiver.receive(view);
    if (!encoded) return false;
    const command = JSON.parse(new TextDecoder().decode(encoded)); encoded.fill(0);
    this.commands.push(command);
    if (!this.respond) return true;
    const response = {request_id: command.request_id, ok: true};
    if (command.operation === "authorize" && command.password === "" &&
        this.rejectEmptyAuthorization) {
      response.ok = false;
      response.error = "authentication_required";
    }
    if (command.operation === "apply")
      response.generation = this.applyGeneration === undefined
        ? command.expected_generation + 1
        : this.applyGeneration;
    if (command.operation === "profile_step_up" ||
        command.operation === "profile_step_up_status") {
      response.confirmation_required = Boolean(this.confirmationRequired);
      response.ready = !this.confirmationRequired || Boolean(this.confirmationReady);
    }
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
    if (command.operation === "select_wtp_status_carrier") {
      if (this.rejectWtpCarrier) {
        response.ok = false;
        response.error = "invalid_request";
      } else {
        response.carrier = this.wtpCarrier;
        response.command_carrier = this.wtpCommandCarrier;
        if (this.onWtpCarrier) this.onWtpCarrier();
      }
    }
    queueMicrotask(() => this.peer.emit(response));
    return true;
  }
  async writeValueWithResponse(bytes) { return this.write(bytes, "with-response"); }
  async writeValueWithoutResponse(bytes) { return this.write(bytes, "without-response"); }
  emitWtp(value) {
    const encoded = wtpFrame(value);
    for (let offset = 0; offset < encoded.length; offset += 13)
      this.emitBytes(encoded.subarray(offset, Math.min(encoded.length, offset + 13)));
    encoded.fill(0);
  }
}
class WtpCharacteristic extends Characteristic {
  constructor(label = "", notificationLog = []) {
    super(undefined, label, notificationLog);
    this.receiver = new WtpReceiver();
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
  const notificationLog = [];
  const identity = new Characteristic({device_id: observedDevice, generation}, "identity",
                                      notificationLog);
  const command = new Characteristic(undefined, "command", notificationLog);
  const status = new Characteristic(undefined, "status", notificationLog);
  const wtpCommand = new WtpCharacteristic("wtp-command", notificationLog);
  const wtpStatus = new WtpCharacteristic("wtp-status", notificationLog);
  command.peer = status;
  wtpCommand.peer = wtpStatus;
  command.onWtpCarrier = () => { command.wtpMode = true; };
  const characteristics = new Map();
  const api = require("../src/provisioning/web/bluefy.js");
  characteristics.set(api.UUIDS.identity, identity);
  characteristics.set(api.UUIDS.command, command);
  characteristics.set(api.UUIDS.status, status);
  characteristics.set(api.UUIDS.wtpCommand, wtpCommand);
  characteristics.set(api.UUIDS.wtpStatus, wtpStatus);
  const gatt = {connected: false, connections: 0, disconnections: 0,
    async connect() { ++this.connections; this.connected = true; return this; },
    disconnect() {
      if (this.connected) ++this.disconnections;
      this.connected = false;
      status.notificationsActive = false;
      wtpStatus.notificationsActive = false;
      wtpCommand.peer = wtpStatus;
      command.wtpMode = false;
      command.wtpReceiver.reset();
    },
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
  const bluetooth = {requests: 0, async requestDevice() { ++this.requests; return deviceObject; }};
  return {bluetooth, identity, command, status, wtpCommand, wtpStatus, notificationLog,
    gatt, device: deviceObject};
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

  const lostDuringSubscription = bluetoothFixture();
  const originalStart = lostDuringSubscription.status.startNotifications.bind(
    lostDuringSubscription.status);
  lostDuringSubscription.status.startNotifications = async () => {
    const result = await originalStart();
    lostDuringSubscription.gatt.disconnect();
    return result;
  };
  await rejectsCode(
    () => new Client(lostDuringSubscription.bluetooth, cryptoFixture()).connect(device),
    "bluetooth_disconnected");
  assert.strictEqual(lostDuringSubscription.status.listeners.length, 0);
  assert.strictEqual(lostDuringSubscription.gatt.connected, false);

  const fixture = bluetoothFixture();
  const client = new Client(
    fixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  assert.deepStrictEqual(await client.connect(), {device_id: device, generation: 0});
  await rejectsCode(() => client.provision(profile()), "authentication_required");
  assert.deepStrictEqual(await client.authorize(""), {authorized: true});
  assert.strictEqual(fixture.command.commands[0].password, "");
  await rejectsCode(() => client.authorize("short"), "local_password");
  assert.strictEqual(fixture.command.commands.length, 1);
  assert.deepStrictEqual(await client.identify(), {identified: true});
  assert.deepStrictEqual(await client.synchronizeTime(1800000000000), {accepted: true});
  const submitIndex = fixture.command.commands.findIndex(
    (command) => command.operation === "time_submit");
  assert(submitIndex > 0);
  const submitFrameCount = frames(new TextEncoder().encode(
    JSON.stringify(fixture.command.commands[submitIndex]))).length;
  assert(submitFrameCount > 1);
  const submitKinds = fixture.command.writeKinds.slice(
    fixture.command.writeKinds.length - submitFrameCount);
  assert.deepStrictEqual(submitKinds,
    Array(submitFrameCount - 1).fill("without-response").concat("with-response"));
  assert.strictEqual((await client.fieldStatus()).time_source, "controller");

  const provisionalFixture = bluetoothFixture();
  provisionalFixture.command.rejectEmptyAuthorization = true;
  const provisionalClient = new Client(
    provisionalFixture.bluetooth, cryptoFixture(), {timeoutMs: 50});
  await provisionalClient.connect(device);
  await rejectsCode(() => provisionalClient.authorize(""), "authentication_required");
  assert.strictEqual(provisionalClient.authorized, false);
  assert.strictEqual(provisionalFixture.command.commands[0].password, "");
  provisionalClient.disconnect();

  const acknowledgedOnlyFixture = bluetoothFixture();
  acknowledgedOnlyFixture.command.writeValueWithoutResponse = undefined;
  const acknowledgedOnlyClient = new Client(
    acknowledgedOnlyFixture.bluetooth, cryptoFixture(), {timeoutMs: 50});
  await acknowledgedOnlyClient.connect(device);
  await acknowledgedOnlyClient.authorize("wspr-0a60df");
  await acknowledgedOnlyClient.synchronizeTime(1800000000000);
  const acknowledgedSubmit = acknowledgedOnlyFixture.command.commands.find(
    (command) => command.operation === "time_submit");
  const acknowledgedSubmitFrames = frames(new TextEncoder().encode(
    JSON.stringify(acknowledgedSubmit))).length;
  assert(acknowledgedSubmitFrames > 1);
  assert.deepStrictEqual(
    acknowledgedOnlyFixture.command.writeKinds.slice(-acknowledgedSubmitFrames),
    Array(acknowledgedSubmitFrames).fill("with-response"));

  const droppedLeadingFixture = bluetoothFixture();
  const droppedLeadingClient = new Client(
    droppedLeadingFixture.bluetooth, cryptoFixture(), {timeoutMs: 50});
  await droppedLeadingClient.connect(device);
  await droppedLeadingClient.authorize("wspr-0a60df");
  const originalUnacknowledged =
    droppedLeadingFixture.command.writeValueWithoutResponse.bind(droppedLeadingFixture.command);
  let droppedLeading = false;
  droppedLeadingFixture.command.writeValueWithoutResponse = async (bytes) => {
    if (!droppedLeading) {
      droppedLeading = true;
      droppedLeadingFixture.command.writtenSizes.push(bytes.byteLength);
      droppedLeadingFixture.command.writeKinds.push("without-response-dropped");
      return true;
    }
    return originalUnacknowledged(bytes);
  };
  await rejectsCode(() => droppedLeadingClient.synchronizeTime(1800000000000), "frame_order");
  assert.strictEqual(droppedLeading, true);
  assert.strictEqual(droppedLeadingFixture.command.commands.some(
    (command) => command.operation === "time_submit"), false);
  assert.strictEqual(droppedLeadingClient.pending.size, 0);

  const hello = await client.enableLocalControl();
  assert.strictEqual(hello.device_id, device);
  assert.deepStrictEqual(fixture.notificationLog, ["status:start"]);
  assert.strictEqual(fixture.bluetooth.requests, 1);
  assert.strictEqual(fixture.gatt.connections, 1);
  assert.strictEqual(fixture.gatt.disconnections, 0);
  assert.strictEqual(fixture.status.notificationsActive, true);
  assert.strictEqual(fixture.wtpStatus.notificationsActive, false);
  assert.strictEqual(fixture.status.listeners.length, 1);
  assert.strictEqual(fixture.wtpStatus.listeners.length, 0);
  assert.strictEqual(fixture.wtpStatus.notificationStarts, 0);
  assert.strictEqual(fixture.command.commands.at(-1).operation,
                     "select_wtp_status_carrier");
  assert.deepStrictEqual(await client.wtpExchange("STATUS", {}),
    {state: "empty", output_active: false});
  assert.deepStrictEqual(fixture.command.wtpCommands.map((item) => item.op), ["HELLO", "STATUS"]);
  assert.strictEqual(fixture.wtpCommand.commands.length, 0);
  assert(fixture.command.writtenSizes.every((size) => size <= WTP_SEGMENT_BYTES));
  assert(fixture.command.writtenSizes.every(
    (size, index) => size === fixture.command.writtenBufferSizes[index] &&
      fixture.command.writtenOffsets[index] === 0),
  "Bluefy writes must use compact buffers rather than views into larger frames");
  fixture.command.wtpRespond = false;
  const pendingWtp = client.wtpExchange("PING", {token: "one-at-a-time"});
  await new Promise((resolve) => setImmediate(resolve));
  await rejectsCode(() => client.wtpExchange("CAPS", {}), "wtp_busy");
  const pendingCommand = fixture.command.wtpCommands.at(-1);
  fixture.status.emitWtp({type: "response", protocol: "WTP/1",
    session_id: pendingCommand.session_id, request_id: pendingCommand.request_id,
    op: pendingCommand.op, ok: true, body: {token: "one-at-a-time"}});
  assert.deepStrictEqual(await pendingWtp, {token: "one-at-a-time"});
  fixture.command.wtpRespond = true;
  await client.selectFieldChannel();
  assert.strictEqual(fixture.command.commands.at(-1).operation, "authorize");
  assert.strictEqual(fixture.command.commands.at(-1).password, "");
  fixture.command.respond = false;
  const invalidFieldStatus = client.fieldStatus();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepStrictEqual(fixture.notificationLog.slice(-1), ["status:start"]);
  assert.strictEqual(fixture.bluetooth.requests, 1);
  assert.strictEqual(fixture.gatt.connections, 2);
  assert.strictEqual(fixture.gatt.disconnections, 1);
  assert.strictEqual(fixture.status.notificationsActive, true);
  assert.strictEqual(fixture.wtpStatus.notificationsActive, false);
  assert.strictEqual(fixture.status.listeners.length, 1);
  assert.strictEqual(fixture.wtpStatus.listeners.length, 0);
  const fieldRequest = fixture.command.commands.at(-1);
  fixture.status.emit({request_id: fieldRequest.request_id, ok: true});
  await rejectsCode(() => invalidFieldStatus, "field_status_response");
  fixture.command.respond = true;
  const submittedProfile = profile();
  const result = await client.provision(submittedProfile);
  assert.deepStrictEqual(result, {generation: 1});
  for (const field of ["access_password", "password", "server_certificate",
    "server_private_key", "client_ca"])
    assert.strictEqual(submittedProfile[field], "");
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
  assert(fixture.command.commands.findIndex((command) => command.operation === "profile_step_up") >
    fixture.command.commands.findIndex((command) => command.operation === "write"));
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

  const noSwitchFixture = bluetoothFixture();
  const noSwitchClient = new Client(
    noSwitchFixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  await noSwitchClient.connect(device);
  await noSwitchClient.authorize("wspr-0a60df");
  noSwitchFixture.status.stopNotifications = undefined;
  assert.strictEqual((await noSwitchClient.enableLocalControl()).device_id, device);
  assert.strictEqual(noSwitchFixture.gatt.connected, true);
  assert.strictEqual(noSwitchFixture.status.notificationsActive, true);
  assert.strictEqual(noSwitchFixture.wtpStatus.notificationStarts, 0);
  assert.strictEqual(noSwitchFixture.bluetooth.requests, 1);
  assert.strictEqual(noSwitchFixture.gatt.connections, 1);
  assert.strictEqual(noSwitchFixture.gatt.disconnections, 0);

  const stableListenerFixture = bluetoothFixture();
  const stableListenerClient = new Client(
    stableListenerFixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  await stableListenerClient.connect(device);
  await stableListenerClient.authorize("wspr-0a60df");
  const stableListener = stableListenerFixture.status.listeners[0];
  stableListenerFixture.status.addEventListener = () => {
    throw new Error("native listener replacement failure");
  };
  stableListenerFixture.status.removeEventListener = () => {
    throw new Error("native listener replacement failure");
  };
  assert.strictEqual((await stableListenerClient.enableLocalControl()).device_id, device);
  assert.strictEqual(stableListenerFixture.status.listeners.length, 1);
  assert.strictEqual(stableListenerFixture.status.listeners[0], stableListener);
  assert.strictEqual(stableListenerFixture.gatt.connected, true);
  assert.strictEqual(stableListenerFixture.command.wtpCommands[0].op, "HELLO");
  assert.strictEqual(stableListenerFixture.wtpCommand.commands.length, 0);

  const stopFailureFixture = bluetoothFixture();
  const stopFailureClient = new Client(
    stopFailureFixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  await stopFailureClient.connect(device);
  await stopFailureClient.authorize("wspr-0a60df");
  stopFailureFixture.status.stopNotifications = async () => {
    throw new Error("native stop failure");
  };
  assert.strictEqual((await stopFailureClient.enableLocalControl()).device_id, device);
  assert.strictEqual(stopFailureFixture.gatt.connected, true);
  assert.strictEqual(stopFailureFixture.status.notificationsActive, true);
  assert.strictEqual(stopFailureFixture.status.notificationStops, 0);
  assert.strictEqual(stopFailureClient.wtpListening, true);
  assert.strictEqual(stopFailureFixture.wtpStatus.notificationStarts, 0);

  const failedSwitchFixture = bluetoothFixture();
  const failedSwitchClient = new Client(
    failedSwitchFixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  await failedSwitchClient.connect(device);
  await failedSwitchClient.authorize("wspr-0a60df");
  failedSwitchFixture.command.rejectWtpCarrier = true;
  await rejectsCode(() => failedSwitchClient.enableLocalControl(), "invalid_request");
  assert.strictEqual(failedSwitchFixture.gatt.connected, false);
  assert.strictEqual(failedSwitchFixture.status.notificationsActive, false);
  assert.strictEqual(failedSwitchClient.device, null);
  assert.strictEqual(failedSwitchClient.fieldListening, false);
  assert.strictEqual(failedSwitchClient.wtpListening, false);
  assert.deepStrictEqual(failedSwitchFixture.notificationLog, ["status:start"]);

  const wrongCarrierFixture = bluetoothFixture();
  const wrongCarrierClient = new Client(
    wrongCarrierFixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  await wrongCarrierClient.connect(device);
  await wrongCarrierClient.authorize("wspr-0a60df");
  wrongCarrierFixture.command.wtpCarrier = "unexpected";
  await rejectsCode(() => wrongCarrierClient.selectWtpChannel(), "wtp_status_carrier");
  assert.strictEqual(wrongCarrierFixture.gatt.connected, false);
  assert.strictEqual(wrongCarrierClient.device, null);
  assert.strictEqual(wrongCarrierFixture.wtpStatus.notificationStarts, 0);

  const wrongCommandCarrierFixture = bluetoothFixture();
  const wrongCommandCarrierClient = new Client(
    wrongCommandCarrierFixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  await wrongCommandCarrierClient.connect(device);
  await wrongCommandCarrierClient.authorize("wspr-0a60df");
  wrongCommandCarrierFixture.command.wtpCommandCarrier = "unexpected";
  await rejectsCode(() => wrongCommandCarrierClient.selectWtpChannel(), "wtp_status_carrier");
  assert.strictEqual(wrongCommandCarrierFixture.gatt.connected, false);
  assert.strictEqual(wrongCommandCarrierClient.device, null);

  const failedFieldResumeFixture = bluetoothFixture();
  const failedFieldResumeClient = new Client(
    failedFieldResumeFixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  await failedFieldResumeClient.connect(device);
  await failedFieldResumeClient.authorize("wspr-0a60df");
  await failedFieldResumeClient.enableLocalControl();
  failedFieldResumeFixture.command.rejectEmptyAuthorization = true;
  await rejectsCode(() => failedFieldResumeClient.fieldStatus(), "authentication_required");
  assert.strictEqual(failedFieldResumeFixture.gatt.connected, false);
  assert.strictEqual(failedFieldResumeClient.device, null);
  assert.strictEqual(failedFieldResumeClient.authorized, false);

  const invalidProfile = profile({port: 0});
  await rejectsCode(() => client.provision(invalidProfile), "port");
  for (const field of ["access_password", "password", "server_certificate",
    "server_private_key", "client_ca"])
    assert.strictEqual(invalidProfile[field], "");

  const confirmationFixture = bluetoothFixture();
  confirmationFixture.command.confirmationRequired = true;
  let confirmationRequests = 0;
  const confirmationClient = new Client(
    confirmationFixture.bluetooth, cryptoFixture(), {
      timeoutMs: 50,
      confirmationTimeoutMs: 2000,
      onConfirmationRequired() {
        ++confirmationRequests;
        confirmationFixture.command.confirmationReady = true;
      }
    });
  await confirmationClient.connect(device);
  await confirmationClient.authorize("wspr-0a60df");
  assert.deepStrictEqual(await confirmationClient.provision(profile()), {generation: 1});
  assert.strictEqual(confirmationRequests, 1);
  assert(confirmationFixture.command.commands.some(
    (command) => command.operation === "profile_step_up_status"));

  const corruptWtpFixture = bluetoothFixture();
  const corruptWtpClient = new Client(
    corruptWtpFixture.bluetooth, cryptoFixture(), {timeoutMs: 50, reconnectDelayMs: 0});
  await corruptWtpClient.connect(device);
  await corruptWtpClient.authorize("wspr-0a60df");
  await corruptWtpClient.enableLocalControl();
  corruptWtpFixture.command.wtpRespond = false;
  const corruptWtpPending = corruptWtpClient.wtpExchange("STATUS", {});
  await new Promise((resolve) => setImmediate(resolve));
  const badWtpResponse = wtpFrame({invalid: true});
  badWtpResponse[badWtpResponse.length - 1] ^= 1;
  corruptWtpFixture.status.emitBytes(badWtpResponse);
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
      /^writes [0-9]+\/[0-9]+; events 0; frames 0; messages 0; matched 0; wtp writes 0\/0; last none$/);
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
  await new Promise((resolve) => setImmediate(resolve));
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

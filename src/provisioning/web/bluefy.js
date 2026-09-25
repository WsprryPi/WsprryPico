(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WsprryBluefy = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  const UUIDS = Object.freeze({
    service: "7d6b0001-5bf1-4f21-a486-3e8f70c12201",
    identity: "7d6b0002-5bf1-4f21-a486-3e8f70c12201",
    command: "7d6b0003-5bf1-4f21-a486-3e8f70c12201",
    status: "7d6b0004-5bf1-4f21-a486-3e8f70c12201",
    wtpCommand: "7d6b0005-5bf1-4f21-a486-3e8f70c12201",
    wtpStatus: "7d6b0006-5bf1-4f21-a486-3e8f70c12201"
  });
  const MAX_PROFILE_BYTES = 7168;
  const FRAGMENT_BYTES = 64;
  // Fixed framing and bounded reassembly in both directions are part of the wire contract.
  const GATT_FRAME_BYTES = 64;
  const GATT_FRAME_HEADER_BYTES = 4;
  const GATT_FRAME_PAYLOAD_BYTES = GATT_FRAME_BYTES - GATT_FRAME_HEADER_BYTES;
  const GATT_FRAME_COUNT = 16;
  const MAX_COMMAND_BYTES = 512;
  const MAX_STATUS_BYTES = 256;
  const WTP_HEADER_BYTES = 16;
  const WTP_MAX_PAYLOAD_BYTES = 65536;
  const WTP_SEGMENT_BYTES = 64;
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  function fail(code) {
    const error = new Error(code);
    error.code = code;
    throw error;
  }
  function printable(value, minimum, maximum) {
    return typeof value === "string" && value.length >= minimum && value.length <= maximum &&
      Array.from(value).every((c) => c.codePointAt(0) >= 32 && c.codePointAt(0) < 127);
  }
  function validDeviceId(value) {
    return typeof value === "string" && /^[0-9a-f]{32}$/.test(value);
  }
  function canonicalHostname(value) {
    if (typeof value !== "string") fail("hostname");
    let name = value.endsWith(".") ? value.slice(0, -1) : value;
    name = name.toLowerCase();
    const label = name.endsWith(".local") ? name.slice(0, -6) : "";
    if (!label || label.length > 63 || !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(label))
      fail("hostname");
    return name;
  }
  function validTimeServer(value) {
    if (!printable(value, 1, 253) || /[:/\s]/.test(value)) return false;
    const ipv4Parts = value.split(".");
    if (ipv4Parts.length === 4 && ipv4Parts.every((part) => /^(?:0|[1-9][0-9]{0,2})$/.test(part))) {
      const octets = ipv4Parts.map(Number);
      return octets.every((octet) => octet <= 255) && octets[0] > 0 &&
        octets[0] < 224 && octets[0] !== 127;
    }
    const numeric = ipv4Parts.every((part) => {
      const digits = /^0[xX]/.test(part) ? part.slice(2) : part;
      return digits.length > 0 && (/^0[xX]/.test(part) ? /^[0-9a-fA-F]+$/ : /^[0-9]+$/).test(digits);
    });
    if (numeric) return false;
    const name = value.endsWith(".") ? value.slice(0, -1) : value;
    if (!name) return false;
    return name.split(".").every((label) => label.length >= 1 && label.length <= 63 &&
      /^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(label));
  }
  function pem(value, begin, end, maximum) {
    if (typeof value !== "string" || value.length > maximum || !value.startsWith(begin))
      return false;
    const trimmed = value.replace(/[\r\n]+$/, "");
    return trimmed.endsWith(end) && Array.from(value).every((c) => {
      const code = c.codePointAt(0);
      return c === "\r" || c === "\n" || (code >= 32 && code < 127);
    });
  }
  function canonicalProfile(input) {
    if (!input || !validDeviceId(input.device_id)) fail("device_id");
    if (!printable(input.ssid, 1, 32)) fail("ssid");
    if (!printable(input.password, 8, 63)) fail("password");
    if (!validTimeServer(input.time_server)) fail("time_server");
    const hostname = canonicalHostname(input.hostname);
    const port = Number(input.port);
    if (!Number.isInteger(port) || port < 1 || port > 65535) fail("port");
    if (!pem(input.server_certificate, "-----BEGIN CERTIFICATE-----",
             "-----END CERTIFICATE-----", 3072)) fail("server_certificate");
    if (!(pem(input.server_private_key, "-----BEGIN PRIVATE KEY-----",
              "-----END PRIVATE KEY-----", 2048) ||
          pem(input.server_private_key, "-----BEGIN EC PRIVATE KEY-----",
              "-----END EC PRIVATE KEY-----", 2048))) fail("server_private_key");
    if (!pem(input.client_ca, "-----BEGIN CERTIFICATE-----",
             "-----END CERTIFICATE-----", 3072)) fail("client_ca");
    const value = JSON.stringify({
      version: 1,
      device_id: input.device_id,
      wifi: {ssid: input.ssid, password: input.password, time_server: input.time_server},
      tls: {hostname, port, server_certificate: input.server_certificate,
        server_private_key: input.server_private_key, client_ca: input.client_ca}
    });
    const bytes = encoder.encode(value);
    if (bytes.length > MAX_PROFILE_BYTES) {
      bytes.fill(0);
      fail("profile_oversize");
    }
    return {value, bytes};
  }
  function randomId(cryptoObject) {
    if (!cryptoObject || typeof cryptoObject.getRandomValues !== "function") fail("secure_random");
    const bytes = new Uint8Array(16);
    cryptoObject.getRandomValues(bytes);
    const value = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
    bytes.fill(0);
    return value;
  }
  function base64(bytes) {
    if (typeof Buffer === "function") return Buffer.from(bytes).toString("base64");
    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary);
  }
  function text(value) {
    return decoder.decode(new Uint8Array(value.buffer, value.byteOffset || 0, value.byteLength));
  }
  function crc32c(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) {
      crc = (crc ^ byte) >>> 0;
      for (let bit = 0; bit < 8; ++bit)
        crc = ((crc >>> 1) ^ ((crc & 1) ? 0x82f63b78 : 0)) >>> 0;
    }
    return (crc ^ 0xffffffff) >>> 0;
  }
  function wtpFrame(message) {
    const payload = encoder.encode(JSON.stringify(message));
    if (!payload.length || payload.length > WTP_MAX_PAYLOAD_BYTES) {
      payload.fill(0); fail("wtp_payload_oversize");
    }
    const frame = new Uint8Array(WTP_HEADER_BYTES + payload.length);
    frame.set([0x57, 0x54, 0x50, 0x46, 1, 1, 0, 0]);
    const view = new DataView(frame.buffer);
    view.setUint32(8, payload.length);
    view.setUint32(12, crc32c(payload));
    frame.set(payload, WTP_HEADER_BYTES);
    payload.fill(0);
    return frame;
  }
  class WtpReceiver {
    constructor() { this.reset(); }
    reset() { if (this.buffer) this.buffer.fill(0); this.buffer = new Uint8Array(0); }
    receive(value) {
      const bytes = new Uint8Array(value.buffer, value.byteOffset || 0, value.byteLength);
      if (!bytes.length || this.buffer.length + bytes.length > 131072) {
        this.reset(); fail("wtp_frame_oversize");
      }
      const joined = new Uint8Array(this.buffer.length + bytes.length);
      joined.set(this.buffer); joined.set(bytes, this.buffer.length); this.buffer.fill(0);
      this.buffer = joined;
      const messages = [];
      while (this.buffer.length >= WTP_HEADER_BYTES) {
        const view = new DataView(this.buffer.buffer, this.buffer.byteOffset, this.buffer.byteLength);
        const valid = this.buffer[0] === 0x57 && this.buffer[1] === 0x54 &&
          this.buffer[2] === 0x50 && this.buffer[3] === 0x46 && this.buffer[4] === 1 &&
          this.buffer[5] === 1 && this.buffer[6] === 0 && this.buffer[7] === 0;
        const length = view.getUint32(8);
        if (!valid || !length || length > WTP_MAX_PAYLOAD_BYTES) {
          this.reset(); fail("wtp_frame_invalid");
        }
        const frameBytes = WTP_HEADER_BYTES + length;
        if (this.buffer.length < frameBytes) break;
        const payload = this.buffer.slice(WTP_HEADER_BYTES, frameBytes);
        const expected = view.getUint32(12);
        const remaining = this.buffer.slice(frameBytes);
        this.buffer.fill(0); this.buffer = remaining;
        if (crc32c(payload) !== expected) { payload.fill(0); this.reset(); fail("wtp_crc"); }
        let message;
        try { message = JSON.parse(decoder.decode(payload)); }
        catch (_) { payload.fill(0); this.reset(); fail("wtp_json"); }
        payload.fill(0);
        messages.push(message);
      }
      return messages;
    }
  }

  function frames(bytes) {
    if (!(bytes instanceof Uint8Array) || !bytes.length ||
        bytes.length > GATT_FRAME_PAYLOAD_BYTES * GATT_FRAME_COUNT) fail("frame_oversize");
    const result = [];
    for (let offset = 0, sequence = 0; offset < bytes.length; ++sequence) {
      const count = Math.min(GATT_FRAME_PAYLOAD_BYTES, bytes.length - offset);
      const frame = new Uint8Array(GATT_FRAME_HEADER_BYTES + count);
      frame[0] = 1;
      frame[1] = (offset === 0 ? 1 : 0) | (offset + count === bytes.length ? 2 : 0);
      frame[2] = sequence;
      frame[3] = count;
      frame.set(bytes.subarray(offset, offset + count), GATT_FRAME_HEADER_BYTES);
      result.push(frame);
      offset += count;
    }
    return result;
  }
  class FrameReceiver {
    constructor(maximum) { this.maximum = maximum; this.reset(); }
    reset() { if (this.message) this.message.fill(0); this.message = new Uint8Array(0); this.next = 0; this.active = false; }
    receive(value) {
      const frame = new Uint8Array(value.buffer, value.byteOffset || 0, value.byteLength);
      if (frame.length < GATT_FRAME_HEADER_BYTES || frame.length > GATT_FRAME_BYTES ||
          frame[0] !== 1 || (frame[1] & ~3) || frame[3] !== frame.length - GATT_FRAME_HEADER_BYTES) {
        this.reset(); fail("frame_invalid");
      }
      const first = Boolean(frame[1] & 1), last = Boolean(frame[1] & 2);
      if ((first && (this.active || frame[2] !== 0)) || (!first && !this.active) ||
          frame[2] !== this.next || frame[2] >= GATT_FRAME_COUNT) {
        this.reset(); fail("frame_order");
      }
      if (first) { this.reset(); this.active = true; }
      const payload = frame.subarray(GATT_FRAME_HEADER_BYTES);
      if (!payload.length || this.message.length + payload.length > this.maximum) {
        this.reset(); fail("frame_oversize");
      }
      const joined = new Uint8Array(this.message.length + payload.length);
      joined.set(this.message); joined.set(payload, this.message.length); this.message.fill(0);
      this.message = joined; ++this.next;
      if (!last) return null;
      const complete = this.message;
      this.message = new Uint8Array(0); this.next = 0; this.active = false;
      return complete;
    }
  }

  class Client {
    constructor(bluetooth, cryptoObject, options) {
      this.bluetooth = bluetooth;
      this.crypto = cryptoObject;
      this.timeoutMs = options && options.timeoutMs ? options.timeoutMs : 30000;
      this.confirmationTimeoutMs = options && options.confirmationTimeoutMs
        ? options.confirmationTimeoutMs : 25000;
      this.onConfirmationRequired = options &&
        typeof options.onConfirmationRequired === "function"
        ? options.onConfirmationRequired : null;
      this.device = null;
      this.command = null;
      this.status = null;
      this.identity = null;
      this.wtpCommand = null;
      this.wtpStatus = null;
      this.pending = new Map();
      this.wtpPending = new Map();
      this.expectedDeviceId = "";
      this.generation = 0;
      this.authorized = false;
      this.fieldSession = "";
      this.wtpSession = "";
      this.fieldListening = false;
      this.wtpListening = false;
      this.wtpHello = null;
      this.lastWtpEvent = null;
      this.statusReceiver = new FrameReceiver(MAX_STATUS_BYTES);
      this.wtpReceiver = new WtpReceiver();
      // Counts and fixed error codes only; never retain a command, reply or secret.
      this.trace = {writes: 0, written: 0, events: 0, frames: 0,
        messages: 0, matched: 0, last: "none"};
      this.onStatus = this.onStatus.bind(this);
      this.onWtpStatus = this.onWtpStatus.bind(this);
      this.onDisconnected = this.onDisconnected.bind(this);
    }
    async connect(expectedDeviceId) {
      const verifyExpected = expectedDeviceId !== undefined && expectedDeviceId !== "";
      if (verifyExpected && !validDeviceId(expectedDeviceId)) fail("device_id");
      if (!this.bluetooth || typeof this.bluetooth.requestDevice !== "function")
        fail("web_bluetooth_unavailable");
      if (this.device || this.command) fail("already_connected");
      const device = await this.bluetooth.requestDevice({filters: [{services: [UUIDS.service]}]});
      let status = null;
      let listenerAdded = false;
      let disconnectListenerAdded = false;
      try {
        if (typeof device.addEventListener === "function") {
          device.addEventListener("gattserverdisconnected", this.onDisconnected);
          disconnectListenerAdded = true;
        }
        const server = await device.gatt.connect();
        const service = await server.getPrimaryService(UUIDS.service);
        const identity = await service.getCharacteristic(UUIDS.identity);
        const command = await service.getCharacteristic(UUIDS.command);
        status = await service.getCharacteristic(UUIDS.status);
        const wtpCommand = await service.getCharacteristic(UUIDS.wtpCommand);
        const wtpStatus = await service.getCharacteristic(UUIDS.wtpStatus);
        let observed;
        try {
          observed = JSON.parse(text(await identity.readValue()));
        } catch (_) {
          fail("identity_format");
        }
        if (!observed || typeof observed !== "object" ||
            Object.keys(observed).sort().join(",") !== "device_id,generation" ||
            !validDeviceId(observed.device_id) || (verifyExpected && observed.device_id !== expectedDeviceId) ||
            !Number.isSafeInteger(observed.generation) || observed.generation < 0)
          fail("wrong_device");
        const notifying = await status.startNotifications();
        // Web Bluetooth returns the characteristic; use that returned event source
        // when an implementation provides a distinct wrapper.
        if (notifying && typeof notifying.addEventListener === "function")
          status = notifying;
        status.addEventListener("characteristicvaluechanged", this.onStatus);
        listenerAdded = true;
        this.device = device;
        this.identity = identity;
        this.command = command;
        this.status = status;
        this.wtpCommand = wtpCommand;
        this.wtpStatus = wtpStatus;
        this.expectedDeviceId = observed.device_id;
        this.generation = observed.generation;
        this.fieldListening = true;
        return {device_id: observed.device_id, generation: observed.generation};
      } catch (error) {
        if (listenerAdded && status)
          status.removeEventListener("characteristicvaluechanged", this.onStatus);
        if (disconnectListenerAdded)
          device.removeEventListener("gattserverdisconnected", this.onDisconnected);
        if (device.gatt && device.gatt.connected) device.gatt.disconnect();
        this.device = this.command = this.status = this.identity = null;
        this.wtpCommand = this.wtpStatus = null;
        this.expectedDeviceId = "";
        this.generation = 0;
        this.authorized = false;
        this.fieldSession = this.wtpSession = "";
        this.fieldListening = false;
        this.wtpListening = false;
        this.wtpHello = null;
        this.statusReceiver.reset();
        this.wtpReceiver.reset();
        throw error;
      }
    }
    diagnosticSummary() {
      const t = this.trace;
      return `writes ${t.written}/${t.writes}; events ${t.events}; frames ${t.frames}; ` +
        `messages ${t.messages}; matched ${t.matched}; last ${t.last}`;
    }
    onStatus(event) {
      ++this.trace.events;
      const value = event && event.target && event.target.value;
      if (!value) { this.trace.last = "status_value_missing"; return; }
      let encoded;
      try {
        encoded = this.statusReceiver.receive(value);
        ++this.trace.frames;
      } catch (error) {
        this.trace.last = error && error.code ? error.code : "frame_decode";
        return;
      }
      if (!encoded) return;
      ++this.trace.messages;
      let response;
      try { response = JSON.parse(text(encoded)); }
      catch (_) { encoded.fill(0); this.trace.last = "status_json"; return; }
      encoded.fill(0);
      if (!response || !validDeviceId(response.request_id)) {
        this.trace.last = "response_id_invalid";
        return;
      }
      const pending = this.pending.get(response.request_id);
      if (!pending) { this.trace.last = "response_unmatched"; return; }
      if (typeof response.ok !== "boolean") {
        this.trace.last = "response_invalid";
        return;
      }
      ++this.trace.matched;
      this.trace.last = "matched";
      clearTimeout(pending.timer);
      this.pending.delete(response.request_id);
      if (response.ok) pending.resolve(response);
      else {
        const error = new Error(response.error || "device_rejected");
        error.code = response.error || "device_rejected";
        pending.reject(error);
      }
    }
    onWtpStatus(event) {
      const value = event && event.target && event.target.value;
      if (!value) return;
      let responses;
      try { responses = this.wtpReceiver.receive(value); }
      catch (error) {
        for (const entry of this.wtpPending.values()) {
          clearTimeout(entry.timer); entry.reject(error);
        }
        this.wtpPending.clear();
        this.disconnect();
        return;
      }
      for (const response of responses) {
        if (response.type === "event") {
          this.lastWtpEvent = response;
          continue;
        }
        if (response.type !== "response" || response.protocol !== "WTP/1" ||
            response.session_id !== this.wtpSession || !validDeviceId(response.request_id) ||
            typeof response.op !== "string" || typeof response.ok !== "boolean") continue;
        const pending = this.wtpPending.get(response.request_id);
        if (!pending || pending.op !== response.op) continue;
        clearTimeout(pending.timer);
        this.wtpPending.delete(response.request_id);
        if (response.ok && response.body && typeof response.body === "object")
          pending.resolve(response.body);
        else {
          const code = response.error && typeof response.error.code === "string"
            ? response.error.code : "device_rejected";
          const error = new Error(code); error.code = code; pending.reject(error);
        }
      }
    }
    onDisconnected(event) {
      for (const entry of this.pending.values()) {
        clearTimeout(entry.timer);
        const error = new Error("bluetooth_disconnected");
        error.code = "bluetooth_disconnected";
        error.detail = this.diagnosticSummary();
        entry.reject(error);
      }
      this.pending.clear();
      for (const entry of this.wtpPending.values()) {
        clearTimeout(entry.timer);
        const error = new Error("bluetooth_disconnected");
        error.code = "bluetooth_disconnected";
        entry.reject(error);
      }
      this.wtpPending.clear();
      if (this.status)
        this.status.removeEventListener("characteristicvaluechanged", this.onStatus);
      if (this.wtpStatus && this.wtpListening)
        this.wtpStatus.removeEventListener("characteristicvaluechanged", this.onWtpStatus);
      const device = event && event.target ? event.target : this.device;
      if (device && typeof device.removeEventListener === "function")
        device.removeEventListener("gattserverdisconnected", this.onDisconnected);
      this.device = this.command = this.status = this.identity = null;
      this.wtpCommand = this.wtpStatus = null;
      this.expectedDeviceId = "";
      this.generation = 0;
      this.authorized = false;
      this.fieldSession = this.wtpSession = "";
      this.fieldListening = false;
      this.wtpListening = false;
      this.wtpHello = null;
      this.statusReceiver.reset();
      this.wtpReceiver.reset();
    }
    async selectFieldChannel() {
      if (!this.status) fail("not_connected");
      if (this.fieldListening) return;
      if (this.wtpPending.size) fail("wtp_busy");
      if (this.wtpStatus && this.wtpListening) {
        if (typeof this.wtpStatus.stopNotifications !== "function")
          fail("notification_switch_unavailable");
        const activeWtpStatus = this.wtpStatus;
        await activeWtpStatus.stopNotifications();
        activeWtpStatus.removeEventListener("characteristicvaluechanged", this.onWtpStatus);
        this.wtpListening = false;
        this.wtpSession = "";
        this.wtpHello = null;
        this.lastWtpEvent = null;
        this.wtpReceiver.reset();
      }
      let notifying = await this.status.startNotifications();
      if (notifying && typeof notifying.addEventListener === "function")
        this.status = notifying;
      this.status.addEventListener("characteristicvaluechanged", this.onStatus);
      this.fieldListening = true;
    }
    async selectWtpChannel() {
      if (!this.status || !this.wtpStatus) fail("not_connected");
      if (this.wtpListening) return;
      if (this.pending.size) fail("field_busy");
      if (this.fieldListening) {
        if (typeof this.status.stopNotifications !== "function")
          fail("notification_switch_unavailable");
        const activeStatus = this.status;
        await activeStatus.stopNotifications();
        activeStatus.removeEventListener("characteristicvaluechanged", this.onStatus);
        this.fieldListening = false;
        this.statusReceiver.reset();
      }
      try {
        if (!this.wtpStatus) fail("not_connected");
        let notifying = await this.wtpStatus.startNotifications();
        if (notifying && typeof notifying.addEventListener === "function")
          this.wtpStatus = notifying;
        this.wtpListening = true;
        this.wtpStatus.addEventListener("characteristicvaluechanged", this.onWtpStatus);
      } catch (error) {
        if (this.wtpStatus && this.wtpListening) {
          const activeWtpStatus = this.wtpStatus;
          try {
            if (typeof activeWtpStatus.stopNotifications === "function")
              await activeWtpStatus.stopNotifications();
          } catch (_) { /* best-effort rollback */ }
          activeWtpStatus.removeEventListener("characteristicvaluechanged", this.onWtpStatus);
          this.wtpListening = false;
        }
        try { await this.selectFieldChannel(); } catch (_) { /* preserve original failure */ }
        throw error;
      }
    }
    async exchange(message, acceleratedTail = false) {
      if (!this.command) fail("not_connected");
      if (!this.fieldListening) {
        await this.selectFieldChannel();
        if (!this.command || !this.status) fail("not_connected");
      }
      if (!validDeviceId(message.request_id) || this.pending.has(message.request_id))
        fail("request_id");
      const encoded = encoder.encode(JSON.stringify(message));
      if (encoded.length > MAX_COMMAND_BYTES) { encoded.fill(0); fail("command_oversize"); }
      const outbound = frames(encoded);
      this.trace.writes += outbound.length;
      let settle;
      const result = new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          this.pending.delete(message.request_id);
          const error = new Error("timeout");
          error.code = "timeout";
          error.detail = this.diagnosticSummary();
          reject(error);
        }, this.timeoutMs);
        settle = {resolve, reject, timer}; this.pending.set(message.request_id, settle);
      });
      try {
        const command = this.command;
        const acknowledgedWrite = command.writeValueWithResponse || command.writeValue;
        const unacknowledgedWrite = acceleratedTail && command.writeValueWithoutResponse;
        for (let index = 0; index < outbound.length; ++index) {
          const write = unacknowledgedWrite && index + 1 < outbound.length
            ? unacknowledgedWrite : acknowledgedWrite;
          await write.call(command, outbound[index]);
          ++this.trace.written;
        }
      } catch (error) {
        clearTimeout(settle.timer);
        this.pending.delete(message.request_id);
        if (error && typeof error === "object") error.detail = this.diagnosticSummary();
        throw error;
      } finally {
        encoded.fill(0); for (const frame of outbound) frame.fill(0);
      }
      return result;
    }
    async authorize(password) {
      if (!printable(password, 8, 63)) fail("local_password");
      const sessionId = randomId(this.crypto);
      try {
        await this.exchange({version: 1, operation: "authorize",
          request_id: randomId(this.crypto), session_id: sessionId,
          device_id: this.expectedDeviceId, password});
        this.authorized = true;
        this.fieldSession = sessionId;
        return {authorized: true};
      } finally { password = ""; }
    }
    async cancel(sessionId) {
      return this.exchange({version: 1, operation: "cancel", request_id: randomId(this.crypto),
        session_id: sessionId, device_id: this.expectedDeviceId});
    }
    async identify() {
      if (!this.authorized) fail("authentication_required");
      const response = await this.exchange({version: 1, operation: "identify",
        request_id: randomId(this.crypto), session_id: this.fieldSession,
        device_id: this.expectedDeviceId});
      if (response.identified !== true) fail("identify_response");
      return {identified: true};
    }
    async fieldStatus() {
      if (!this.authorized) fail("authentication_required");
      const response = await this.exchange({version: 1, operation: "field_status",
        request_id: randomId(this.crypto), session_id: this.fieldSession,
        device_id: this.expectedDeviceId});
      if (!["none", "sntp", "controller", "disagreement"].includes(response.time_source) ||
          !/^(0|[1-9][0-9]*)$/.test(response.time_age_ns) ||
          !/^(0|[1-9][0-9]*)$/.test(response.time_uncertainty_ns) ||
          typeof response.time_disagreement !== "boolean" ||
          !["off", "softap_ready", "identify"].includes(response.indicator) ||
          typeof response.indicator_fault !== "boolean") fail("field_status_response");
      return response;
    }
    async synchronizeTime(nowMilliseconds) {
      if (!this.authorized) fail("authentication_required");
      const nonce = randomId(this.crypto);
      const challenge = await this.exchange({version: 1, operation: "time_challenge",
        request_id: randomId(this.crypto), session_id: this.fieldSession,
        device_id: this.expectedDeviceId, nonce});
      if (challenge.nonce !== nonce) fail("time_challenge_binding");
      const sampled = nowMilliseconds === undefined ? Date.now() : nowMilliseconds;
      if (!Number.isSafeInteger(sampled) || sampled < 0) fail("controller_time");
      // The command characteristic preserves ATT ordering. Queue leading
      // fragments as write commands, then use one acknowledged tail fragment
      // so the complete authenticated sample remains ordered and loss-detecting
      // without spending the controller-time budget on one round trip per frame.
      const response = await this.exchange({version: 1, operation: "time_submit",
        request_id: randomId(this.crypto), session_id: this.fieldSession,
        device_id: this.expectedDeviceId, nonce,
        utc_ns: (BigInt(sampled) * 1000000n).toString()}, true);
      if (response.accepted !== true) fail("controller_time_response");
      return {accepted: true};
    }
    async wtpExchange(op, body) {
      if (!this.authorized || !this.wtpListening || !this.wtpCommand || !this.wtpSession)
        fail("wtp_unavailable");
      if (this.wtpPending.size) fail("wtp_busy");
      if (typeof op !== "string" || !/^[A-Z][A-Z0-9_]{0,63}$/.test(op) ||
          !body || typeof body !== "object" || Array.isArray(body)) fail("wtp_request");
      const requestId = randomId(this.crypto);
      const frame = wtpFrame({type: "request", protocol: "WTP/1",
        session_id: this.wtpSession, request_id: requestId, op, body});
      let settle;
      const result = new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          this.wtpPending.delete(requestId);
          const error = new Error("wtp_timeout"); error.code = "wtp_timeout"; reject(error);
        }, this.timeoutMs);
        settle = {resolve, reject, timer, op}; this.wtpPending.set(requestId, settle);
      });
      try {
        const write = this.wtpCommand.writeValueWithResponse || this.wtpCommand.writeValue;
        for (let offset = 0; offset < frame.length; offset += WTP_SEGMENT_BYTES)
          await write.call(this.wtpCommand, frame.subarray(
            offset, Math.min(frame.length, offset + WTP_SEGMENT_BYTES)));
      } catch (error) {
        clearTimeout(settle.timer); this.wtpPending.delete(requestId); throw error;
      } finally { frame.fill(0); }
      return result;
    }
    async enableLocalControl() {
      if (!this.authorized || !this.wtpStatus) fail("authentication_required");
      if (this.wtpHello) return this.wtpHello;
      await this.selectWtpChannel();
      this.wtpSession = randomId(this.crypto);
      try {
        const hello = await this.wtpExchange("HELLO", {versions: ["WTP/1"],
          client_name: "WsprryPico Bluefy", client_version: "1"});
        if (hello.selected_version !== "WTP/1" || hello.device_id !== this.expectedDeviceId ||
            !validDeviceId(hello.boot_id) || !printable(hello.product, 1, 64) ||
            !printable(hello.firmware_version, 1, 64)) fail("wtp_wrong_device");
        this.wtpHello = hello;
        return hello;
      } catch (error) {
        this.disconnect();
        throw error;
      }
    }
    async provision(input) {
      let profile = null;
      let accessPassword = input && typeof input.access_password === "string"
        ? input.access_password : "";
      let sessionId = "";
      let opened = false;
      try {
        if (!this.command || !input || input.device_id !== this.expectedDeviceId)
          fail("wrong_device");
        if (!this.authorized) fail("authentication_required");
        if (!printable(accessPassword, 8, 63)) fail("local_password");
        profile = canonicalProfile(input);
        sessionId = randomId(this.crypto);
        await this.exchange({version: 1, operation: "open", request_id: randomId(this.crypto),
          session_id: sessionId, device_id: this.expectedDeviceId});
        opened = true;
        for (let offset = 0; offset < profile.bytes.length; offset += FRAGMENT_BYTES) {
          const end = Math.min(offset + FRAGMENT_BYTES, profile.bytes.length);
          await this.exchange({version: 1, operation: "write", request_id: randomId(this.crypto),
            session_id: sessionId, device_id: this.expectedDeviceId, offset,
            final: end === profile.bytes.length, payload: base64(profile.bytes.subarray(offset, end))});
        }
        const applyRequestId = randomId(this.crypto);
        let stepUp = await this.exchange({version: 1, operation: "profile_step_up",
          request_id: randomId(this.crypto), session_id: this.fieldSession,
          device_id: this.expectedDeviceId, profile_session_id: sessionId,
          apply_request_id: applyRequestId, expected_generation: this.generation,
          password: accessPassword});
        if (typeof stepUp.confirmation_required !== "boolean" ||
            typeof stepUp.ready !== "boolean") fail("profile_step_up_response");
        if (stepUp.confirmation_required && !stepUp.ready) {
          if (this.onConfirmationRequired) this.onConfirmationRequired();
          const deadline = Date.now() + this.confirmationTimeoutMs;
          do {
            await new Promise((resolve) => setTimeout(resolve, 500));
            stepUp = await this.exchange({version: 1, operation: "profile_step_up_status",
              request_id: randomId(this.crypto), session_id: this.fieldSession,
              device_id: this.expectedDeviceId, apply_request_id: applyRequestId});
            if (typeof stepUp.confirmation_required !== "boolean" ||
                typeof stepUp.ready !== "boolean") fail("profile_step_up_response");
          } while (!stepUp.ready && Date.now() < deadline);
          if (!stepUp.ready) fail("confirmation_timeout");
        }
        const response = await this.exchange({version: 1, operation: "apply",
          request_id: applyRequestId, session_id: sessionId,
          device_id: this.expectedDeviceId, expected_generation: this.generation});
        if (!Number.isSafeInteger(response.generation) || response.generation < this.generation)
          fail("generation");
        this.generation = response.generation;
        return {generation: response.generation};
      } catch (error) {
        if (opened) {
          try { await this.cancel(sessionId); } catch (_) { /* best-effort bounded cleanup */ }
        }
        throw error;
      } finally {
        accessPassword = "";
        if (input && typeof input === "object") {
          for (const field of ["access_password", "password", "server_certificate",
            "server_private_key", "client_ca"])
            try { input[field] = ""; } catch (_) { /* immutable caller input */ }
        }
        if (profile) {
          profile.bytes.fill(0);
          profile.value = "";
        }
      }
    }
    disconnect() {
      for (const entry of this.pending.values()) {
        clearTimeout(entry.timer);
        const error = new Error("disconnected");
        error.code = "disconnected";
        entry.reject(error);
      }
      this.pending.clear();
      for (const entry of this.wtpPending.values()) {
        clearTimeout(entry.timer);
        const error = new Error("disconnected"); error.code = "disconnected";
        entry.reject(error);
      }
      this.wtpPending.clear();
      if (this.status) this.status.removeEventListener("characteristicvaluechanged", this.onStatus);
      if (this.wtpStatus && this.wtpListening)
        this.wtpStatus.removeEventListener("characteristicvaluechanged", this.onWtpStatus);
      if (this.device && typeof this.device.removeEventListener === "function")
        this.device.removeEventListener("gattserverdisconnected", this.onDisconnected);
      if (this.device && this.device.gatt.connected) this.device.gatt.disconnect();
      this.device = this.command = this.status = this.identity = null;
      this.wtpCommand = this.wtpStatus = null;
      this.expectedDeviceId = "";
      this.generation = 0;
      this.authorized = false;
      this.fieldSession = this.wtpSession = "";
      this.fieldListening = false;
      this.wtpListening = false;
      this.wtpHello = null;
      this.statusReceiver.reset();
      this.wtpReceiver.reset();
    }
  }

  return {UUIDS, MAX_PROFILE_BYTES, FRAGMENT_BYTES, GATT_FRAME_BYTES,
    GATT_FRAME_HEADER_BYTES, GATT_FRAME_PAYLOAD_BYTES, GATT_FRAME_COUNT, MAX_COMMAND_BYTES,
    MAX_STATUS_BYTES, WTP_HEADER_BYTES, WTP_MAX_PAYLOAD_BYTES, WTP_SEGMENT_BYTES,
    validDeviceId, canonicalProfile, frames, FrameReceiver, crc32c, wtpFrame, WtpReceiver, Client};
});

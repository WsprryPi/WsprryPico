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
    status: "7d6b0004-5bf1-4f21-a486-3e8f70c12201"
  });
  const MAX_PROFILE_BYTES = 7168;
  const FRAGMENT_BYTES = 64;
  // Commands and status notifications can exceed a default ATT value. A future
  // GATT adapter must negotiate a sufficient payload or provide bounded framing
  // and reassembly in both directions; these are wire bounds, not atomic-MTU claims.
  const MAX_COMMAND_BYTES = 512;
  const MAX_STATUS_BYTES = 256;
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

  class Client {
    constructor(bluetooth, cryptoObject, options) {
      this.bluetooth = bluetooth;
      this.crypto = cryptoObject;
      this.timeoutMs = options && options.timeoutMs ? options.timeoutMs : 30000;
      this.device = null;
      this.command = null;
      this.status = null;
      this.identity = null;
      this.pending = new Map();
      this.expectedDeviceId = "";
      this.generation = 0;
      this.onStatus = this.onStatus.bind(this);
    }
    async connect(expectedDeviceId) {
      if (!validDeviceId(expectedDeviceId)) fail("device_id");
      if (!this.bluetooth || typeof this.bluetooth.requestDevice !== "function")
        fail("web_bluetooth_unavailable");
      if (this.device || this.command) fail("already_connected");
      const device = await this.bluetooth.requestDevice({filters: [{services: [UUIDS.service]}]});
      let status = null;
      let listenerAdded = false;
      try {
        const server = await device.gatt.connect();
        const service = await server.getPrimaryService(UUIDS.service);
        const identity = await service.getCharacteristic(UUIDS.identity);
        const command = await service.getCharacteristic(UUIDS.command);
        status = await service.getCharacteristic(UUIDS.status);
        let observed;
        try {
          observed = JSON.parse(text(await identity.readValue()));
        } catch (_) {
          fail("identity_format");
        }
        if (!observed || typeof observed !== "object" ||
            Object.keys(observed).sort().join(",") !== "device_id,generation" ||
            !validDeviceId(observed.device_id) || observed.device_id !== expectedDeviceId ||
            !Number.isSafeInteger(observed.generation) || observed.generation < 0)
          fail("wrong_device");
        await status.startNotifications();
        status.addEventListener("characteristicvaluechanged", this.onStatus);
        listenerAdded = true;
        this.device = device;
        this.identity = identity;
        this.command = command;
        this.status = status;
        this.expectedDeviceId = expectedDeviceId;
        this.generation = observed.generation;
        return {device_id: observed.device_id, generation: observed.generation};
      } catch (error) {
        if (listenerAdded && status)
          status.removeEventListener("characteristicvaluechanged", this.onStatus);
        if (device.gatt && device.gatt.connected) device.gatt.disconnect();
        this.device = this.command = this.status = this.identity = null;
        this.expectedDeviceId = "";
        this.generation = 0;
        throw error;
      }
    }
    onStatus(event) {
      const value = event && event.target && event.target.value;
      if (!value || value.byteLength > MAX_STATUS_BYTES) return;
      let response;
      try {
        response = JSON.parse(text(value));
      } catch (_) {
        return;
      }
      if (!response || !validDeviceId(response.request_id)) return;
      const pending = this.pending.get(response.request_id);
      if (!pending) return;
      if (typeof response.ok !== "boolean") return;
      clearTimeout(pending.timer);
      this.pending.delete(response.request_id);
      if (response.ok) pending.resolve(response);
      else {
        const error = new Error(response.error || "device_rejected");
        error.code = response.error || "device_rejected";
        pending.reject(error);
      }
    }
    async exchange(message) {
      if (!this.command) fail("not_connected");
      if (!validDeviceId(message.request_id) || this.pending.has(message.request_id))
        fail("request_id");
      const encoded = encoder.encode(JSON.stringify(message));
      if (encoded.length > MAX_COMMAND_BYTES) {
        encoded.fill(0);
        fail("command_oversize");
      }
      let settle;
      const result = new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          this.pending.delete(message.request_id);
          const error = new Error("timeout");
          error.code = "timeout";
          reject(error);
        }, this.timeoutMs);
        settle = {resolve, reject, timer};
        this.pending.set(message.request_id, settle);
      });
      try {
        const write = this.command.writeValueWithResponse || this.command.writeValue;
        await write.call(this.command, encoded);
      } catch (error) {
        clearTimeout(settle.timer);
        this.pending.delete(message.request_id);
        throw error;
      } finally {
        encoded.fill(0);
      }
      return result;
    }
    async cancel(sessionId) {
      return this.exchange({version: 1, operation: "cancel", request_id: randomId(this.crypto),
        session_id: sessionId, device_id: this.expectedDeviceId});
    }
    async provision(input) {
      if (!this.command || input.device_id !== this.expectedDeviceId) fail("wrong_device");
      const profile = canonicalProfile(input);
      const sessionId = randomId(this.crypto);
      let opened = false;
      try {
        await this.exchange({version: 1, operation: "open", request_id: randomId(this.crypto),
          session_id: sessionId, device_id: this.expectedDeviceId});
        opened = true;
        for (let offset = 0; offset < profile.bytes.length; offset += FRAGMENT_BYTES) {
          const end = Math.min(offset + FRAGMENT_BYTES, profile.bytes.length);
          await this.exchange({version: 1, operation: "write", request_id: randomId(this.crypto),
            session_id: sessionId, device_id: this.expectedDeviceId, offset,
            final: end === profile.bytes.length, payload: base64(profile.bytes.subarray(offset, end))});
        }
        const response = await this.exchange({version: 1, operation: "apply",
          request_id: randomId(this.crypto), session_id: sessionId,
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
        profile.bytes.fill(0);
        profile.value = "";
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
      if (this.status) this.status.removeEventListener("characteristicvaluechanged", this.onStatus);
      if (this.device && this.device.gatt.connected) this.device.gatt.disconnect();
      this.device = this.command = this.status = this.identity = null;
      this.expectedDeviceId = "";
      this.generation = 0;
    }
  }

  return {UUIDS, MAX_PROFILE_BYTES, FRAGMENT_BYTES, MAX_COMMAND_BYTES, MAX_STATUS_BYTES,
    validDeviceId, canonicalProfile, Client};
});

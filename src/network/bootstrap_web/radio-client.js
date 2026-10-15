import {begin,authenticate,seal,open,clear,unhex} from './radio-crypto.js';
import {prepareNetwork,prepareStation,submitSetup,checkSetup} from './radio-setup.js';

export class RadioClient {
  constructor(fetcher = globalThis.fetch?.bind(globalThis), now = () => Date.now()) {
    this.fetcher = fetcher; this.now = now; this.state = null; this.busy = false;
  }
  clear() { clear(this.state); this.state = null; }
  get authenticated() {
    if (this.state && (this.now() < this.seen || this.now()-this.started >= 900000 || this.now()-this.seen >= 300000)) this.clear();
    return Boolean(this.state);
  }
  async post(path, body, binary, timeout) {
    const response = await this.fetcher('/api/consumer/v1/' + path, {method:'POST',credentials:'omit',redirect:'error',cache:'no-store',
      headers:{'Content-Type':binary ? 'application/octet-stream' : 'application/json','X-WsprryPico-Radio':'1'},
      body:binary ? body : JSON.stringify(body),signal:AbortSignal.timeout(timeout)});
    if (!response.ok) {
      let code; try { code = (await response.json()).error?.code; } catch {}
      const messages = {
        radio_session_capacity:'All three radio sessions are in use. Log out another client or wait up to five idle minutes, then log in again.',
        radio_login_pending:'Another login is in progress. Wait up to 30 seconds, then try again.',
        radio_login_rate_limited:'Logins must be at least one second apart. Wait a second, then try again.'
      };
      const error = new Error(messages[code] || (response.status === 401 ? 'Wi-Fi password rejected or this radio session expired. Log in again.' : 'Radio request rejected'));
      error.code = messages[code] ? code : 'radio_authentication_required'; throw error;
    }
    if (binary) {
      if (response.headers.get('Content-Type') !== 'application/octet-stream') throw new Error('Unexpected radio response');
      return new Uint8Array(await response.arrayBuffer());
    }
    return response.json();
  }
  async identity() {
    const response = await this.fetcher('/api/consumer/v1/identity', {credentials:'omit',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(5000)});
    if (!response.ok) throw new Error('Consumer radio access is unavailable');
    const id = await response.json();
    unhex(id.device_id,16); unhex(id.boot_id,16);
    if (id.version !== 1 || id.authentication !== 'saved_wifi_passphrase' || !/^[1-9][0-9]*$/.test(id.generation) || BigInt(id.generation) > 0xffffffffffffffffn) throw new Error('Invalid Pico identity');
    return id;
  }
  async login(password, identity) {
    if (this.busy) throw new Error('A radio request is already in progress');
    this.clear(); this.busy = true;
    const pending = begin(); let state;
    try {
      const grant = await this.post('start',{version:1,...identity,authentication:undefined,public_key:pending.public_key,nonce:pending.nonce},false,30000);
      state = authenticate(pending,grant,password,identity);
      const ack = open(state,0n,await this.post('finish',state.finish,true,30000));
      state.finish.fill(0); delete state.finish;
      if (ack.authenticated !== true || ack.device_id !== identity.device_id || ack.boot_id !== identity.boot_id) throw new Error('Radio login was not confirmed');
      this.state = state; this.sequence = 1n; this.started = this.seen = this.now();
    } catch (error) { clear(state); throw error; }
    finally { pending.secret.fill(0); this.busy = false; }
  }
  async request(path, method = 'GET', body, etag, timeout = 30000) {
    if (this.busy) throw new Error('A radio request is already in progress');
    if (!this.authenticated) { const error = new Error('Log in with the saved Wi-Fi password'); error.code='radio_authentication_required'; throw error; }
    this.busy = true;
    try {
      const sequence = this.sequence++;
      const packet = seal(this.state,sequence,{method,path:'/api/v1/' + path,if_match:etag || null,body:body === undefined ? null : body});
      const result = open(this.state,sequence,await this.post('request',packet,true,timeout));
      this.seen = this.now();
      if (!Number.isInteger(result.status) || result.status < 100 || result.status > 599 ||
          (result.etag !== null && typeof result.etag !== 'string') || !result.body || typeof result.body !== 'object') throw new Error('Invalid radio API response');
      return {ok:result.status >= 200 && result.status < 300,status:result.status,headers:{get:name => name.toLowerCase() === 'etag' ? result.etag : null},json:async () => result.body};
    } catch (error) { this.clear(); error.code='radio_authentication_required'; throw error; }
    finally { this.busy = false; }
  }
  async logout() {
    try { if (this.authenticated) await this.request('consumer/logout','POST',{}); }
    finally { this.clear(); }
  }
  prepareNetwork(identity,settings) { return prepareNetwork(this,identity,settings); }
  prepareStation(identity,settings) { return prepareStation(this,identity,settings); }
  submitSetup(attempt) { return submitSetup(this,attempt); }
  checkSetup(attempt) { return checkSetup(this,attempt); }
}
globalThis.WsprryPicoConsumerRadio = Object.freeze({createClient:() => new RadioClient()});

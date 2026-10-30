import '../web/control-contract.js';
import {begin,authenticate,seal,open,clear,unhex,retirementSelector} from './radio-crypto.js';
import {prepareNetwork,prepareStation,submitSetup,checkSetup} from './radio-setup.js';

const publicReadResources = globalThis.WsprryControl.publicResources;

function publicDiscovery(text) {
  if(text.length>4096) throw new Error('Public read discovery exceeds its bound');
  const value=JSON.parse(text), stack=[];
  // JSON.parse validates grammar but discards duplicate keys. Inspect original
  // string tokens, including escaped key spellings, before trusting the shape.
  for(let at=0;at<text.length;at++) {
    const c=text[at];
    if(c==='{' || c==='[') {
      stack.push(c==='{'?new Set():null);
      if(stack.length>3) throw new Error('Public read discovery is too deeply nested');
    } else if(c==='}' || c===']') stack.pop();
    else if(c==='"') {
      const start=at++;
      while(at<text.length && text[at]!=='"') {if(text[at]==='\\') at++;at++;}
      let next=at+1;while(/\s/.test(text[next]||'') && next<text.length) next++;
      if(text[next]===':') {
        const key=JSON.parse(text.slice(start,at+1)),keys=stack.at(-1);
        if(!keys || keys.has(key)) throw new Error('Duplicate public read discovery field');
        keys.add(key);
      }
    }
  }
  return value;
}

const idleMs = 30 * 60 * 1000, absoluteMs = 8 * 60 * 60 * 1000;

export class RadioClient {
  constructor(fetcher = globalThis.fetch?.bind(globalThis), now = () => Date.now(), context) {
    this.fetcher = fetcher; this.now = now; this.state = null; this.busy = false; this.lostSession = null;
    this.idleMs=idleMs;this.absoluteMs=absoluteMs;
    this.context = context || (globalThis.location?.host ? {authority:globalThis.location.host,interface:globalThis.location.hostname === '192.168.4.1' ? 'ap' : 'station'} : null);
  }
  clear() { clear(this.state); this.state = null; }
  get authenticated() {
    if (this.state && (this.now() < this.seen || this.now()-this.started >= this.absoluteMs || this.now()-this.seen >= this.idleMs)) this.clear();
    return Boolean(this.state);
  }
  async post(path, body, binary, timeout) {
    const response = await this.fetcher('/api/consumer/v1/' + path, {method:'POST',credentials:'omit',redirect:'error',cache:'no-store',
      headers:{'Content-Type':binary ? 'application/octet-stream' : 'application/json','X-WsprryPico-Radio':'1'},
      body:binary ? body : JSON.stringify(body),signal:AbortSignal.timeout(timeout)});
    if (!response.ok) {
      let code; try { code = (await response.json()).error?.code; } catch {}
      const messages = {
        radio_session_capacity:'All three radio sessions are in use. Inspect occupied logins and explicitly retire the affected login before trying again.',
        radio_login_pending:'Another login is in progress. Wait up to 30 seconds, then try again.',
        radio_login_rate_limited:'Logins must be at least one second apart. Wait a second, then try again.',
        radio_recovery_pending:'A retirement proof is pending for at most five seconds. Check again before another explicit attempt.',
        radio_recovery_rate_limited:'Retirement attempts must be at least one second apart.',
        radio_recovery_rejected:'Retirement authentication was rejected. Verify the current Pico password.',
        radio_recovery_unavailable:'Retirement could not be confirmed. Keep the same selected login for another explicit check.'
      };
      const error = new Error(messages[code] || (response.status === 401 ? 'Pico password rejected or this radio session expired. Log in again.' : 'Radio request rejected'));
      error.code = typeof code === 'string' && /^[a-z0-9_]{1,80}$/.test(code) ? code : 'radio_response_unconfirmed'; throw error;
    }
    if (binary) {
      if (response.headers.get('Content-Type') !== 'application/octet-stream') throw new Error('Unexpected radio response');
      return new Uint8Array(await response.arrayBuffer());
    }
    return response.json();
  }
  async identity(timeout = 5000) {
    const response = await this.fetcher('/api/consumer/v1/identity', {credentials:'omit',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(timeout)});
    if (!response.ok) throw new Error('Consumer radio access is unavailable');
    const id = await response.json();
    unhex(id.device_id,16); unhex(id.boot_id,16);
    if (Object.keys(id).sort().join(',') !== 'authentication,boot_id,device_id,generation,version' ||
        id.version !== 1 || !['saved_wifi_passphrase','pico_password'].includes(id.authentication) || typeof id.generation !== 'string' ||
        !/^[1-9][0-9]{0,19}$/.test(id.generation) || BigInt(id.generation) > 0xffffffffffffffffn) throw new Error('Invalid Pico identity');
    this.publicIdentity = id;
    this.publicReads = null;
    return id;
  }
  async publicStatus(timeout = 5000) {
    const response = await this.fetcher('/api/consumer/v1/status', {credentials:'omit',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(timeout)});
    if (!response.ok) throw new Error('Transmitter status is unavailable');
    const value = await response.json();
    const decimal = text => typeof text === 'string' && /^(0|[1-9][0-9]{0,19})$/.test(text) && BigInt(text) <= 0xffffffffffffffffn;
    unhex(value.device_id,16); unhex(value.boot_id,16);
    if (Object.keys(value).sort().join(',') !== 'boot_id,clock_state,device_id,engine,output_active,owned,schema,state,uncertainty_ns,utc_now_ns' ||
        value.schema !== 'public-status' || !['empty','loaded','armed','running','complete','aborted','missed','failed'].includes(value.state) ||
        typeof value.output_active !== 'boolean' || typeof value.owned !== 'boolean' ||
        !['unsynchronized','synchronized','holdover'].includes(value.clock_state) ||
        (value.utc_now_ns !== null && !decimal(value.utc_now_ns)) || !decimal(value.uncertainty_ns) ||
        typeof value.engine !== 'string' || !/^[\x20-\x7e]{1,80}$/.test(value.engine)) throw new Error('Invalid transmitter status');
    return value;
  }
  async publicRead(path, timeout = 5000) {
    const discovery=globalThis.WsprryControl.publicPrefix.replace(/\/$/,'');
    if (!publicReadResources.includes(path)) throw new Error('This resource has no public read authority');
    const options = {method:'GET',credentials:'omit',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(timeout)};
    if (!this.publicReads) {
      const reply = await this.fetcher(discovery,options);
      if (!reply.ok) throw new Error('Public settings reads are unavailable on this firmware');
      const value = publicDiscovery(await reply.text()), target = value?.target;
      if (Object.keys(value || {}).sort().join(',') !== 'contract,prefix,resources,schema,target' ||
          value.contract !== globalThis.WsprryControl.contract || value.schema !== 'public-read' || value.prefix !== discovery+'/' ||
          Object.keys(target || {}).sort().join(',') !== 'boot_id,device_id,scope' || target.scope !== 'member' ||
          !this.publicIdentity || target.device_id !== this.publicIdentity.device_id || target.boot_id !== this.publicIdentity.boot_id ||
          !Array.isArray(value.resources) || value.resources.length > 64 ||
          value.resources.some(v=>typeof v !== 'string' || v.length > 128 || !/^[a-z0-9][a-z0-9/-]*$/.test(v)) ||
          new Set(value.resources).size !== value.resources.length || !value.resources.includes(path))
        throw new Error('Public read discovery does not match this Pico or supported contract');
      this.publicReads = value;
    }
    if (!this.publicReads.resources.includes(path)) throw new Error('This Pico has not advertised public read authority for this resource');
    // No login, ownership, sequence consumption or session lifetime renewal.
    return this.fetcher(this.publicReads.prefix + path,{...options,signal:AbortSignal.timeout(timeout)});
  }
  async login(password, identity) {
    if (this.busy) throw new Error('A radio request is already in progress');
    if (typeof password !== 'string' || !/^[\x20-\x7e]{8,63}$/.test(password)) throw new Error('Use the Pico password, 8–63 ASCII characters');
    unhex(identity.device_id,16);unhex(identity.boot_id,16);
    this.busy = true; let pending,state;
    try {
      pending = begin();
      if (this.state) this.lostSession = {selector:retirementSelector(this.identityContext,this.state.session),...this.identityContext};
      this.clear();
      const grant = await this.post('start',{version:1,device_id:identity.device_id,boot_id:identity.boot_id,generation:identity.generation,public_key:pending.public_key,nonce:pending.nonce},false,30000);
      unhex(grant.session_id,16);
      this.lostSession = {selector:retirementSelector(identity,grant.session_id),device_id:identity.device_id,boot_id:identity.boot_id,generation:identity.generation};
      state = authenticate(pending,grant,password,identity);
      const ack = open(state,0n,await this.post('finish',state.finish,true,30000));
      state.finish.fill(0); delete state.finish;
      if (ack.authenticated !== true || ack.device_id !== identity.device_id || ack.boot_id !== identity.boot_id) throw new Error('Radio login was not confirmed');
      this.state = state; this.sequence = 1n; this.started = this.seen = this.now();
      this.identityContext = {device_id:identity.device_id,boot_id:identity.boot_id,generation:identity.generation};
      this.lostSession = null;
    } catch (error) { clear(state); throw error; }
    finally { pending?.secret.fill(0); this.busy = false; }
  }
  async readPolicy() {
    try {
      const result=await this.request('management'),value=await result.json();
      const identity=this.identityContext,target=value?.target,limits=value?.limits;
      const maximum={http_body:32768,consumer_plaintext:32724,config:1800,update:2048,login_ms:60000,idle_ms:86400000,absolute_ms:86400000,consumer_sessions:16,consumer_pending_logins:16};
      const selected=value.selected;
      const knownCarriers=['engineering_mtls','engineering_field','consumer_station','consumer_ap','usb_physical'];
      if(!result.ok || value.contract!==globalThis.WsprryControl.contract || value.schema!=='management' ||
          Object.keys(value).sort().join(',')!=='carriers,contract,limits,operations,preclock,profile,profile_generation,schema,selected,target,unsupported' ||
          !target || Object.keys(target).sort().join(',')!=='boot_id,device_id,scope' || target.scope!=='member' ||
          target.device_id!==identity.device_id || target.boot_id!==identity.boot_id || value.profile_generation!==identity.generation ||
          value.profile!=='consumer' || typeof value.preclock!=='boolean' || !['consumer_station','consumer_ap'].includes(selected) ||
          !limits || Object.keys(limits).sort().join(',')!==Object.keys(maximum).sort().join(',') ||
          Object.entries(maximum).some(([key,max])=>!Number.isSafeInteger(limits[key]) || limits[key]<1 || limits[key]>max) ||
          limits.consumer_pending_logins>limits.consumer_sessions || limits.idle_ms>limits.absolute_ms || limits.update>limits.consumer_plaintext || limits.consumer_plaintext>=limits.http_body ||
          !Array.isArray(value.carriers) || value.carriers.length!==knownCarriers.length || new Set(value.carriers.map(v=>v?.carrier)).size!==knownCarriers.length ||
          !value.carriers.some(v=>v.carrier===selected && v.built_in===true && v.available===true) ||
          value.carriers.some(v=>!v || Object.keys(v).sort().join(',')!=='available,built_in,carrier' || !knownCarriers.includes(v.carrier) || typeof v.built_in!=='boolean' || typeof v.available!=='boolean' || v.available && !v.built_in) ||
          !value.operations || Object.keys(value.operations).sort().join(',')!=='GET,POST,PUT' ||
          Object.values(value.operations).some(v=>!Array.isArray(v) || v.length>64 || new Set(v).size!==v.length || v.some(path=>typeof path!=='string' || path.length>128 || !(path==='jobs/{id}/abort' || /^[a-z0-9-]+(?:\/[a-z0-9-]+)*$/.test(path)))) ||
          !Array.isArray(value.unsupported) || value.unsupported.length>16 || new Set(value.unsupported).size!==value.unsupported.length || value.unsupported.some(v=>typeof v!=='string' || v.length>64))
        throw new Error('Authenticated control policy is unsupported. Update both applications before changing settings.');
      this.idleMs=limits.idle_ms;this.absoluteMs=limits.absolute_ms;
      // This is the authenticated interface of the existing session, never a
      // request to select or fall back to another transport.
      if(this.context)this.context={...this.context,interface:selected==='consumer_ap'?'ap':'station'};
    } catch(error) {
      if(this.state)this.lostSession={selector:retirementSelector(this.identityContext,this.state.session),...this.identityContext};
      this.clear();throw error;
    }
  }
  async request(path, method = 'GET', body, etag, timeout = 30000) {
    if(path!=='consumer/logout' && !(path==='management' && method==='GET') && this.requestAllowed && !this.requestAllowed()) {
      const error=new Error('Controls were locked before this request was submitted'); error.local=true; throw error;
    }
    if (this.busy) throw new Error('A radio request is already in progress');
    if (!this.authenticated) { const error = new Error('Log in with the Pico password'); error.code='radio_authentication_required'; throw error; }
    // Validate/encode before consuming a sequence or changing authentication.
    const sequence = this.sequence;
    let packet;
    if (method !== 'GET') body = {...(body || {}),contract:globalThis.WsprryControl.contract};
    try {packet = seal(this.state,sequence,{method,path:globalThis.WsprryControl.prefix + path,if_match:etag || null,body:body === undefined ? null : body});}
    catch (e) {e.local=true;throw e;}
    this.busy = true;
    try {
      this.sequence++;
      const result = open(this.state,sequence,await this.post('request',packet,true,timeout));
      this.seen = this.now();
      if (!Number.isInteger(result.status) || result.status < 100 || result.status > 599 ||
          (result.etag !== null && typeof result.etag !== 'string') || !result.body || typeof result.body !== 'object') throw new Error('Invalid radio API response');
      return {ok:result.status >= 200 && result.status < 300,status:result.status,headers:{get:name => name.toLowerCase() === 'etag' ? result.etag : null},json:async () => result.body};
    } catch (error) {
      this.lostSession = {selector:retirementSelector(this.identityContext,this.state.session),...this.identityContext};
      this.clear(); error.code ||= 'radio_session_unconfirmed'; error.unconfirmed = true; throw error;
    }
    finally { this.busy = false; }
  }
  async logout() {
    try {
      if (this.authenticated) {
        const result=await this.request('consumer/logout','POST',{});
        if(!result.ok) throw new Error('Remote logout was refused; this browser has cleared its authority.');
      }
    } catch(error) {
      if(this.state) this.lostSession={selector:retirementSelector(this.identityContext,this.state.session),...this.identityContext};
      throw error;
    } finally { this.clear(); }
  }
  get retirementSelector() { return this.state ? retirementSelector(this.identityContext,this.state.session) : this.lostSession?.selector; }
  async recovery() {
    const response = await this.fetcher('/api/consumer/v1/recovery',{credentials:'omit',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(5000)});
    if (response.status === 404) {const e = new Error('This firmware has no authenticated login retirement. Existing reads and saves remain supported; occupied logins require their own logout or expiry.');e.code='radio_recovery_unsupported';throw e;}
    if (!response.ok) throw new Error('Login retirement support could not be read');
    const data = await response.json();
    if (Object.keys(data).sort().join(',') !== 'authority,boot_id,device_id,generation,interface,proof_ms,schema,sessions' ||
        data.schema !== 'consumer-recovery/1' || data.proof_ms !== 5000 || !['ap','station'].includes(data.interface) ||
        typeof data.authority !== 'string' || !/^[a-z0-9.:-]{1,72}$/.test(data.authority) ||
        typeof data.generation !== 'string' || !/^[1-9][0-9]{0,19}$/.test(data.generation) || BigInt(data.generation) > 0xffffffffffffffffn ||
        !Array.isArray(data.sessions) || data.sessions.length > 3) throw new Error('Invalid retirement discovery');
    unhex(data.device_id,16);unhex(data.boot_id,16);
    const selectors = new Set();
    for (const s of data.sessions) {
      if (Object.keys(s).sort().join(',') !== 'selector,state' || !['active','pending'].includes(s.state)) throw new Error('Invalid occupied login');
      unhex(s.selector,16);
      if (selectors.has(s.selector)) throw new Error('Duplicate occupied login');
      selectors.add(s.selector);
    }
    if (this.context && (data.authority !== this.context.authority || data.interface !== this.context.interface)) throw new Error('Retirement authority does not match this page');
    return data;
  }
  async retire(password, discovery, target) {
    if (this.busy) throw new Error('A radio request is already in progress');
    unhex(target,16);
    if (typeof password !== 'string' || !/^[\x20-\x7e]{8,63}$/.test(password)) throw new Error('Use the current Pico password, 8–63 ASCII characters');
    if (this.context && (discovery.authority !== this.context.authority || discovery.interface !== this.context.interface)) throw new Error('Retirement authority does not match this client');
    this.busy = true;let pending,state,finishAttempted=false;
    try {
      pending = begin();
      const {device_id,boot_id,generation,authority,interface:surface} = discovery;
      const identity = {device_id,boot_id,generation};
      const scope = {target_selector:target,authority,interface:surface};
      const grant = await this.post('recovery/start',{version:1,...identity,public_key:pending.public_key,nonce:pending.nonce,target_selector:target},false,5000);
      state = authenticate(pending,grant,password,identity,scope);
      // Once the proof can reach the server our own traffic may be retired.
      // Keep only its nonsecret alias until an authenticated ACK confirms it.
      if (this.state && retirementSelector(this.identityContext,this.state.session) === target) {
        this.lostSession = {selector:target,...this.identityContext}; this.clear();
      }
      finishAttempted=true;
      const ack = open(state,0n,await this.post('recovery/finish',state.finish,true,5000));
      if (ack.retired !== true || typeof ack.present !== 'boolean' || ack.target_selector !== target || ack.device_id !== device_id || ack.boot_id !== boot_id) throw new Error('Retirement result is unconfirmed');
      if (this.state && retirementSelector(this.identityContext,this.state.session) === target) this.clear();
      if (this.lostSession?.selector === target) this.lostSession = null;
      return ack;
    } catch (error) {
      if (finishAttempted) {error.unconfirmed=true;error.code ||= 'radio_retirement_unconfirmed';}
      throw error;
    } finally {pending?.secret.fill(0);state?.finish.fill(0);clear(state);this.busy=false;}
  }
  prepareNetwork(identity,settings) { return prepareNetwork(this,identity,settings); }
  prepareStation(identity,settings) { return prepareStation(this,identity,settings); }
  submitSetup(attempt) { return submitSetup(this,attempt); }
  checkSetup(attempt) { return checkSetup(this,attempt); }
}
globalThis.WsprryPicoConsumerRadio = Object.freeze({createClient:(...args) => new RadioClient(...args)});

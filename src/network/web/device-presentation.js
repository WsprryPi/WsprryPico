'use strict';
// Display observations only. No URL, storage, transport or mutation authority.
(function(root) {
  function canonicalHostname(value) {
    if (typeof value !== 'string' || /[^\x00-\x7f]/.test(value)) return null;
    const name = value.toLowerCase().replace(/\.$/,'');
    return /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local$/.test(name) ? name : null;
  }
  const validId = value => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value);
  function create(document) {
    let epoch = 0, device = null, boot = null, name = null, saved = null;
    let pending = false, fresh = false, authenticated = false;
    const put = (id,text) => { const e=document.getElementById(id); if(e.textContent !== text) e.textContent=text; };
    function render() {
      put('device-name',name || 'Hostname unavailable');
      const state = !fresh ? name ? 'Last confirmed' : 'Connection unknown' :
        pending ? 'Rename pending' : '';
      put('device-name-state',state +
        (pending && saved ? '. Saved for restart: ' + saved : '') +
        (!name ? '. Use the current IP address or setup Wi-Fi.' : ''));
      document.getElementById('device-name-state').hidden = fresh && !pending;
      put('device-id',device || 'Unavailable');
      put('device-boot',boot || 'Unavailable on this connection');
      document.title = (name || 'WsprryPico') + ' - Station control' +
        (!fresh ? name ? ' (last confirmed)' : ' (connection unknown)' : '') +
        (pending ? ' (rename pending)' : '');
    }
    function bind(identity) {
      if (!validId(identity?.device_id) || identity.boot_id !== undefined && !validId(identity.boot_id))
        throw new Error('Device identity is unavailable or malformed.');
      if (device && device !== identity.device_id) throw new Error('This is a different Pico. Return to the original Pico by IP or setup Wi-Fi.');
      ++epoch;
      if (identity.boot_id && boot !== identity.boot_id) { name=null; saved=null; pending=false; authenticated=false; }
      device=identity.device_id; boot=identity.boot_id || boot; fresh=false;
      render();
    }
    function request() { return ++epoch; }
    function current(token) { return token === epoch; }
    function observe(token,target,active,options={}) {
      if (!current(token)) return false;
      if (!validId(target?.device_id) || !validId(target.boot_id) ||
          canonicalHostname(active) !== active || device && target.device_id !== device ||
          !options.authenticated && (authenticated && !options.publicRead || target.device_id !== device || target.boot_id !== boot)) return false;
      if (options.pending && canonicalHostname(options.saved) !== options.saved) return false;
      device=target.device_id; boot=target.boot_id; name=active; saved=options.saved || null;
      pending=!!options.pending; fresh=true; authenticated=!!options.authenticated; render(); return true;
    }
    function unavailable(token,target) {
      if (!current(token)) return;
      if (target) bind(target);
      fresh=false; render();
    }
    async function readPublic(identity,fetch) {
      if (authenticated) return;
      const token=request(), expected={...identity};
      try {
        const response=await fetch('/api/consumer/v1/presentation',
          {cache:'no-store',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(2000)});
        if (!response.ok) { unavailable(token); return; }
        const data=await response.json();
        if (data && Object.keys(data).sort().join(',') === 'boot_id,device_id,hostname,schema' &&
            data.schema === 'device-presentation/1' && data.device_id === expected.device_id &&
            data.boot_id === expected.boot_id && observe(token,data,data.hostname)) return;
        unavailable(token);
      } catch { unavailable(token); /* Unavailable metadata must not prevent login. */ }
    }
    function stale() { ++epoch; fresh=false; render(); }
    render();
    return {bind,request,current,observe,unavailable,stale,readPublic};
  }
  root.WsprryPicoPresentation={canonicalHostname,create};
  if (typeof module !== 'undefined') module.exports=root.WsprryPicoPresentation;
})(globalThis);

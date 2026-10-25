(function (root) {
  'use strict';
  const minutes = text => /^[1-9][0-9]{0,3}$/.test(text) && Number(text) <= 1440 ? Number(text) : null;
  const duration = seconds => seconds === 3600 ? '1 hour' : seconds === 60 ? '1 minute' : `${seconds / 60} minutes`;
  function create({input,read,save,discard,adopt,status,exchange,afterSave = ()=>{}}) {
    let readable = false, writable = false, busy = false, observed = null, revision = '', epoch = 0;
    let edited = false, draftTarget = '', review = false;
    const identity = value => JSON.stringify(value.target);
    function render() {
      read.disabled = busy || !readable;
      input.disabled = busy || !readable || !observed || !revision;
      save.disabled = input.disabled || !writable || !edited || review || minutes(input.value) === null;
      discard.disabled = busy || !observed || !revision;
      adopt.hidden = !review; adopt.disabled = busy || !observed || !revision;
      input.setAttribute('aria-invalid', String(edited && minutes(input.value) === null));
    }
    function valid(r) {
      const v = r.data;
      if (v?.schema !== 'transmitter-ntp-timeout/1' || !r.revision || !v.storage_healthy ||
          v.target?.scope !== 'member' || !/^[0-9a-f]{32}$/.test(v.target.device_id) ||
          !/^[0-9a-f]{32}$/.test(v.target.boot_id) || typeof v.pending_restart !== 'boolean' ||
          !['saved_timeout_s','active_timeout_s'].every(k => Number.isInteger(v[k]) && v[k] % 60 === 0 && minutes(String(v[k]/60)) !== null))
        throw new Error('NTP timeout readback is unavailable or unsupported by this firmware.');
      return v;
    }
    async function load() {
      if (read.disabled) return;
      busy = true; revision = ''; const ticket = ++epoch; render();
      try {
        const r = await exchange('GET'), v = valid(r);
        if (ticket !== epoch) return;
        observed = v; revision = r.revision;
        if (!edited) { input.value = String(v.saved_timeout_s/60); draftTarget = identity(v); }
        review = edited && draftTarget !== identity(v);
        status.textContent = `Saved: ${duration(v.saved_timeout_s)}. Active: ${duration(v.active_timeout_s)}.${v.pending_restart ? ' Restart the Pico to activate the saved timeout.' : ''}${edited ? ' Your entry is preserved.' : ''}${review ? ' Review the new Pico before using this entry.' : ''}`;
      } catch (e) { if (ticket === epoch) status.textContent = e.message; }
      finally { busy = false; render(); }
    }
    async function commit() {
      if (save.disabled || !observed || !revision) return;
      const target = observed.target, expected = minutes(input.value) * 60;
      const ticket = ++epoch, match = revision; busy = true; revision = ''; render();
      try {
        const r = await exchange('PUT',{schema:'transmitter-ntp-timeout/1',target,timeout_s:expected},match);
        const v = valid(r);
        if (ticket !== epoch) return;
        if (identity(v) !== JSON.stringify(target) || v.saved_timeout_s !== expected)
          throw new Error('Saved timeout differs. Read it before another save.');
        observed = v; revision = r.revision; edited = review = false; draftTarget = identity(v);
        input.value = String(v.saved_timeout_s/60);
        status.textContent = `NTP timeout saved: ${duration(expected)}.${v.pending_restart ? ' Restart the Pico to activate it.' : ' This timeout is active.'}`;
        await afterSave();
      } catch (e) { if (ticket === epoch) status.textContent = e.message + ' Read saved timeout before another save; your entry is preserved.'; }
      finally { busy = false; render(); }
    }
    input.oninput = () => { edited = true; if (observed && !review) draftTarget = identity(observed); render(); };
    discard.onclick = () => {
      if (discard.disabled) return;
      input.value = String(observed.saved_timeout_s/60); edited = review = false; draftTarget = identity(observed); render();
    };
    adopt.onclick = () => { if (!adopt.disabled) { draftTarget = identity(observed); review = false; render(); } };
    read.onclick = load; save.onclick = commit; render();
    return {setAvailability(canRead,canWrite) { readable = canRead; writable = canWrite; render(); },
      invalidate() { ++epoch; revision = ''; observed = null; render(); }};
  }
  root.WsprryNtpTimeout = {minutes,create};
  if (typeof module !== 'undefined') module.exports = root.WsprryNtpTimeout;
})(globalThis);

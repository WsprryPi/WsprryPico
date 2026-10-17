(function (root) {
  'use strict';
  function frequency(text) {
    return /^[1-9][0-9]{5,7}$/.test(text) && Number(text) >= 100000 && Number(text) <= 74999994 ? Number(text) : null;
  }
  function supported(d) {
    return d?.schema === 'transmitter-standalone-frequency/1' && d.path === '/api/v1/standalone-frequency' &&
      d.method === 'PUT' && d.units === 'Hz' && d.activation === 'next_job' && d.default === null;
  }
  function create({input,read,save,discard,adopt,status,exchange,afterSave = ()=>{}}) {
    let available = false, busy = false, observed = null, revision = '', epoch = 0, edited = false, draftTarget = '', review = false;
    const identity = value => JSON.stringify(value.target);
    function render() {
      read.disabled = busy || !available;
      input.disabled = busy || !available || !observed || !revision;
      save.disabled = input.disabled || review || !edited || frequency(input.value) === null;
      discard.disabled = busy || !observed || !revision;
      adopt.hidden = !review; adopt.disabled = busy || !observed || !revision;
      input.setAttribute('aria-invalid',String(edited && frequency(input.value) === null));
    }
    function valid(r) {
      const v = r.data;
      if (v?.schema !== 'transmitter-standalone-frequency/1' || !r.revision ||
          v.target?.scope !== 'member' || !/^[0-9a-f]{32}$/.test(v.target.device_id) ||
          !/^[0-9a-f]{32}$/.test(v.target.boot_id) || !v.storage_healthy ||
          (v.frequency_hz !== null && (!Number.isInteger(v.frequency_hz) || frequency(String(v.frequency_hz)) === null)) || typeof v.allowed !== 'boolean')
        throw new Error('Saved frequency is unavailable. Complete station setup, then read it again.');
      return v;
    }
    async function load() {
      if (!available || busy) return;
      busy = true; revision = ''; const ticket = ++epoch; render();
      try {
        const r = await exchange('GET'), v = valid(r);
        if (ticket !== epoch) return;
        observed = v; revision = r.revision;
        if (!edited) { input.value = v.frequency_hz === null ? '' : String(v.frequency_hz); draftTarget = identity(v); }
        review = edited && draftTarget !== identity(v);
        status.textContent = (v.frequency_hz === null ? 'No standalone transmit frequency is saved. Choose and save one before enabling schedules.' : `Saved ${v.frequency_hz.toLocaleString('en-US')} Hz. ${v.allowed ? 'Used by future standalone WSPR jobs.' : 'Blocked by the current frequency permissions or engine limits.'}`) + `${edited ? ' Your entry is preserved.' : ''}${review ? ' Review the new Pico identity before saving this entry.' : ''}`;
      } catch (e) { if (ticket === epoch) status.textContent = e.message; }
      finally { if (ticket === epoch) busy = false; render(); }
    }
    async function commit() {
      if (save.disabled || !observed || !revision) return;
      const target = observed.target, expected = frequency(input.value), match = revision, ticket = ++epoch;
      busy = true; revision = ''; render();
      try {
        const r = await exchange('PUT',{schema:'transmitter-standalone-frequency/1',target,frequency_hz:expected},match);
        const v = valid(r);
        if (ticket !== epoch) return;
        if (identity(v) !== JSON.stringify(target) || v.frequency_hz !== expected || !v.allowed)
          throw new Error('Saved frequency differs from the request.');
        observed = v; revision = r.revision; edited = false; review = false;
        input.value = String(v.frequency_hz); draftTarget = identity(v);
        status.textContent = `Saved ${v.frequency_hz.toLocaleString('en-US')} Hz for future standalone WSPR jobs. A first frequency selection leaves schedules disabled; enable them when ready.`;
        afterSave();
      } catch (e) { if (ticket === epoch) status.textContent = e.message + ' Read the saved frequency before another save; your entry is preserved.'; }
      finally { if (ticket === epoch) busy = false; render(); }
    }
    input.oninput = () => {
      edited = true; if (observed && !review) draftTarget = identity(observed);
      if (frequency(input.value) === null) status.textContent = 'Enter a whole frequency in Hz, without commas or decimals. The Pico checks its supported range and frequency permissions.';
      else status.textContent = review ? 'Review the current Pico identity before saving this entry.' : 'Save frequency to validate and apply this entry to future standalone WSPR jobs.';
      render();
    };
    discard.onclick = () => {
      if (discard.disabled) return;
      input.value = observed.frequency_hz === null ? '' : String(observed.frequency_hz); edited = false; review = false; draftTarget = identity(observed); render();
      status.textContent = observed.frequency_hz === null ? 'No standalone transmit frequency is saved. Choose and save one before enabling schedules.' : `Saved ${observed.frequency_hz.toLocaleString('en-US')} Hz remains selected. Your frequency draft was discarded.`;
    };
    adopt.onclick = () => { if (!adopt.disabled) { draftTarget = identity(observed); review = false; status.textContent = 'Your entry now addresses this Pico. Save frequency to validate and apply it.'; render(); } };
    read.onclick = load; save.onclick = commit; render();
    const invalidate = () => { ++epoch; revision = ''; observed = null; busy = false; render(); };
    return {setAvailability(value) { if (available && !value) invalidate(); available = value; render(); }, invalidate};
  }
  root.WsprryStandaloneFrequency = {frequency,supported,create};
  if (typeof module !== 'undefined') module.exports = root.WsprryStandaloneFrequency;
})(globalThis);

(function (root) {
  'use strict';
  function frequency(text, ranges) {
    if (!/^[1-9][0-9]{4,7}$/.test(text) || Number(text) < 98503 || Number(text) > 74998496) return null;
    // nHz never enters Number arithmetic. Check every tone against one engine
    // range; the server separately enforces its current frequency permissions.
    if (ranges) {
      const tone0 = BigInt(text)*1000000000n + 1497802734375n;
      if (![0n,1n,2n,3n].every(k => ranges.some(r => tone0+k*1464843750n >= BigInt(r.minimum_nhz) && tone0+k*1464843750n <= BigInt(r.maximum_nhz)))) return null;
    }
    return Number(text);
  }
  function supported(d) {
    return d?.schema === 'transmitter-standalone-frequency/1' && d.path === '/api/v1/standalone-frequency' &&
      d.method === 'PUT' && d.units === 'Hz' && d.activation === 'next_job' && d.default === null;
  }
  function create({input,read,save,discard,adopt,status,exchange,ranges = ()=>undefined,afterSave = ()=>{},onError = ()=>{}, context = ()=>null, stationActions = draft=>draft ? 'Choose Apply saved station settings.' : 'Complete station details, choose Save valid station fields, then Apply saved station settings.', hasProgress = ()=>true, run = fn=>fn()}) {
    let available = false, busy = false, observed = null, revision = '', epoch = 0, edited = false, draftTarget = '', review = false;
    let ready = false, draftOnly = false, knownRevision = '', hasRead = false, refreshNeeded = false;
    const identity = value => JSON.stringify(value.target);
    function render() {
      read.disabled = busy || !available;
      input.disabled = busy || !available || !observed || !revision;
      save.disabled = input.disabled || !ready || review || !edited || frequency(input.value,ranges()) === null;
      discard.disabled = busy || !observed || !revision;
      adopt.hidden = !review; adopt.disabled = busy || !observed || !revision;
      input.setAttribute('aria-invalid',String(edited && frequency(input.value,ranges()) === null));
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
    const sameTarget = (a,b) => a?.scope === 'member' && b?.scope === 'member' && a.device_id === b.device_id && a.boot_id === b.boot_id;
    const sameStation = (a,b) => a === null && b === null || a && b && ['callsign','locator','power_dbm'].every(k=>a[k] === b[k]);
    function prerequisite() {
      return (draftOnly ? 'Station details are saved as a draft and are not applied. ' : 'No applied station is available. ') + stationActions(draftOnly) + (edited ? ' Your frequency entry is preserved.' : '');
    }
    function summary() {
      if (!ready) return prerequisite();
      return observed.frequency_hz === null ? 'No WSPR dial frequency is saved. Station settings are applied; choose and save a dial before enabling schedules.' : `Saved WSPR dial ${observed.frequency_hz.toLocaleString('en-US')} Hz. ${observed.allowed ? 'Used by future standalone WSPR jobs.' : 'Blocked by the current frequency permissions or engine limits.'}`;
    }
    function stationRead(r) {
      const s = r.data;
      if (s?.schema !== 'transmitter-station/2' || !r.revision || !s.storage_healthy ||
          !sameTarget(s.target,s.target) || !/^[0-9a-f]{32}$/.test(s.target.device_id) || !/^[0-9a-f]{32}$/.test(s.target.boot_id) ||
          !(s.station === null || typeof s.station?.callsign === 'string' && s.station.callsign.length > 0 && typeof s.station.locator === 'string' && s.station.locator.length > 0 && Number.isInteger(s.station.power_dbm)))
        throw new Error('Applied station readiness is unconfirmed. Read saved frequency to check again; your entry is preserved.');
      return s;
    }
    async function load() {
      if (!available || busy) return;
      busy = true; ready = false; revision = ''; hasRead = true; refreshNeeded = false; const ticket = ++epoch; render();
      try {
        // All resources share the API revision, including profile and draft epochs.
        // Bracket the read so a station/profile transition cannot mix contexts.
        const before = await exchange('GET',undefined,undefined,'station/2');
        if (ticket !== epoch) return;
        const b = stationRead(before);
        const r = await exchange('GET'), v = valid(r);
        const progress = hasProgress() ? await exchange('GET',undefined,undefined,'progress') : null;
        const after = await exchange('GET',undefined,undefined,'station/2');
        const a = stationRead(after), current = context();
        if (ticket !== epoch) return;
        if (![before,after,...(progress ? [progress] : [])].every(x=>x.revision === r.revision && sameTarget(x.data.target,v.target)) ||
            !sameStation(b.station,a.station) || current && (current.boot_id !== v.target.boot_id || current.device_id && current.device_id !== v.target.device_id) ||
            progress && (!/^transmitter-progress\/[123]$/.test(progress.data.schema) || typeof progress.data.station_complete !== 'boolean' || !sameStation(progress.data.applied_station,a.station)))
          throw new Error('Station or saved revision changed during readback. Read saved frequency again; your entry is preserved.');
        ready = a.station !== null; draftOnly = !ready && progress?.data.station_complete === true;
        knownRevision = r.revision;
        observed = v; revision = r.revision;
        if (!edited) { input.value = v.frequency_hz === null ? '' : String(v.frequency_hz); draftTarget = identity(v); }
        review = edited && draftTarget !== identity(v);
        status.textContent = summary() + `${ready && edited ? ' Your entry is preserved.' : ''}${review ? ' Review the new Pico identity before saving this entry.' : ''}`;
      } catch (e) { if (ticket === epoch) { onError(e); status.textContent = e.message; } }
      finally { if (ticket === epoch) busy = false; render(); }
    }
    async function commit() {
      if (save.disabled || !observed || !revision) return;
      const target = observed.target, expected = frequency(input.value,ranges()), match = revision, ticket = ++epoch;
      busy = true; revision = ''; render();
      try {
        const r = await exchange('PUT',{schema:'transmitter-standalone-frequency/1',target,frequency_hz:expected},match);
        const v = valid(r);
        if (ticket !== epoch) return;
        if (identity(v) !== JSON.stringify(target) || v.frequency_hz !== expected || !v.allowed)
          throw new Error('Saved frequency differs from the request.');
        observed = v; revision = r.revision; knownRevision = r.revision; edited = false; review = false;
        input.value = String(v.frequency_hz); draftTarget = identity(v);
        status.textContent = `Saved WSPR dial ${v.frequency_hz.toLocaleString('en-US')} Hz for future standalone WSPR jobs. A first frequency selection leaves schedules disabled; enable them when ready.`;
        await afterSave(r);
      } catch (e) {
        if (ticket === epoch) {
          onError(e);
          if (e.code === 'not_configured') { ready = false; draftOnly = false; status.textContent = prerequisite(); return; }
          const reason = {revision_conflict:'Saved settings changed.',precondition_failed:'Saved revision changed.',
            frequency_not_allowed:'The four WSPR tones are blocked by the engine limits or frequency permissions.',
            invalid_frequency_resource:'The Pico identity changed or the frequency request was invalid.',
            storage_fault:'Frequency storage could not be verified.'}[e.code] || e.message.replace(/[.!?]*$/,'') + '.';
          status.textContent = reason + ' Read the saved frequency before another save; your entry is preserved.';
        }
      }
      finally { if (ticket === epoch) busy = false; render(); }
    }
    input.oninput = () => {
      edited = true; if (observed && !review) draftTarget = identity(observed);
      if (observed && !ready) status.textContent = prerequisite();
      else if (frequency(input.value,ranges()) === null) status.textContent = 'Enter a whole WSPR dial frequency in Hz, without commas or decimals, whose four RF tones fit this engine. The Pico checks frequency permissions.';
      else status.textContent = review ? 'Review the current Pico identity before saving this entry.' : 'Save frequency to validate and apply this entry to future standalone WSPR jobs.';
      render();
    };
    discard.onclick = () => {
      if (discard.disabled) return;
      input.value = observed.frequency_hz === null ? '' : String(observed.frequency_hz); edited = false; review = false; draftTarget = identity(observed); render();
      status.textContent = summary() + ' Your frequency draft was discarded.';
    };
    adopt.onclick = () => { if (!adopt.disabled) { draftTarget = identity(observed); review = false; status.textContent = ready ? 'Station settings are applied. Your entry now addresses this Pico. Save frequency to validate and apply it.' : prerequisite(); render(); } };
    read.onclick = ()=>run(load); save.onclick = ()=>run(commit); render();
    const invalidate = () => {
      if (hasRead) status.textContent = observed && !ready ? prerequisite() : 'Station readiness needs fresh readback. Read saved frequency before saving; your entry is preserved.';
      ++epoch; revision = ''; observed = null; ready = false; busy = false; refreshNeeded = true; render();
    };
    return {setAvailability(value) { if (available && !value) invalidate(); available = value; render(); }, invalidate,
      observeRevision(value) { if (knownRevision && value !== knownRevision) invalidate(); knownRevision = value; },
      async refresh() { if (hasRead && refreshNeeded && available && !busy) await load(); }
    };
  }
  root.WsprryStandaloneFrequency = {frequency,supported,create};
  if (typeof module !== 'undefined') module.exports = root.WsprryStandaloneFrequency;
})(globalThis);

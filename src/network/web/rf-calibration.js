(function (root) {
  'use strict';
  function ppm(text) {
    if (!/^[+-]?[0-9]{1,3}(\.[0-9]{1,3})?$/.test(text)) return null;
    const sign = text.startsWith('-') ? -1 : 1;
    const [whole,fraction = ''] = text.replace(/^[+-]/,'').split('.');
    const value = sign * (Number(whole)*1000 + Number(fraction.padEnd(3,'0')));
    return Math.abs(value) <= 100000 ? value : null;
  }
  function supported(d) {
    return d?.schema === 'transmitter-rf-calibration/1' && d.path === '/api/v1/rf-calibration' &&
      d.method === 'PUT' && d.precision === 3 && d.units === 'ppm' &&
      d.minimum === '-100.000' && d.maximum === '100.000' &&
      d.default_mode === 'manual' && d.activation === 'next_preparation';
  }
  function create({input,mode,read,save,discard,adopt,status,exchange,afterSave = ()=>{},onError = ()=>{},run = fn=>fn()}) {
    let available = false, busy = false, observed = null, revision = '', epoch = 0, edited = false, draftTarget = '', review = false;
    const identity = value => JSON.stringify(value.target);
    function render() {
      read.hidden = !available || Boolean(observed && revision);
      read.disabled = busy || !available;
      input.disabled = mode.disabled = busy || !available || !observed || !revision;
      save.disabled = input.disabled || review || !edited || ppm(input.value) === null || mode.value !== 'manual';
      if (discard) discard.disabled = busy || !observed || !revision;
      if (adopt) { adopt.hidden = !review; adopt.disabled = busy || !observed || !revision; }
      input.setAttribute('aria-invalid',String(ppm(input.value) === null));
    }
    function valid(r) {
      const v = r.data;
      if (!v || v.schema !== 'transmitter-rf-calibration/1' || !r.revision ||
          v.target?.scope !== 'member' || !/^[0-9a-f]{32}$/.test(v.target.device_id) ||
          !/^[0-9a-f]{32}$/.test(v.target.boot_id) || !v.storage_healthy ||
          typeof v.saved?.manual_ppm !== 'string' || ppm(v.saved.manual_ppm) === null ||
          v.saved.mode !== 'manual') throw new Error('Calibration readback is unavailable or unsupported.');
      return v;
    }
    async function load() {
      if (!available || busy) return;
      busy = true; revision = ''; const ticket = ++epoch; render();
      try {
        const r = await exchange('GET'), v = valid(r);
        if (ticket !== epoch) return;
        observed = v; revision = r.revision;
        if (!edited) {
          input.value = v.saved.manual_ppm; mode.value = v.saved.mode; draftTarget = identity(v);
        }
        review = edited && draftTarget !== identity(v);
        status.textContent = `Saved ${v.saved.manual_ppm} ppm (${v.saved.mode}). Next job: ${v.selection?.next_ppb ?? 'unavailable'} ppb. Network time disciplines UTC only.${edited ? ' Your entry is preserved.' : ''}${review ? ' Review the new Pico identity before using this entry.' : ''}`;
      } catch (e) { if (ticket === epoch) { onError(e); status.textContent = e.message; } }
      finally { busy = false; render(); }
    }
    async function commit() {
      if (save.disabled || !observed || !revision) return;
      const target = observed.target, expected = ppm(input.value), selectedMode = mode.value;
      const ticket = ++epoch, match = revision; busy = true; revision = ''; render();
      try {
        const r = await exchange('PUT',{schema:'transmitter-rf-calibration/1',target,
          calibration:{manual_ppm:input.value,mode:selectedMode}},match);
        const v = valid(r);
        if (ticket !== epoch) return;
        if (JSON.stringify(v.target) !== JSON.stringify(target) ||
            ppm(v.saved.manual_ppm) !== expected || v.saved.mode !== selectedMode)
          throw new Error('Saved calibration differs; read saved calibration before another save.');
        observed = v; revision = r.revision; edited = false; review = false;
        input.value = v.saved.manual_ppm; mode.value = v.saved.mode; draftTarget = identity(v);
        status.textContent = 'Manual calibration saved for future jobs.';
        afterSave();
      } catch (e) { if (ticket === epoch) { onError(e); status.textContent = e.message + ' Read saved calibration before another save; your entry is preserved.'; } }
      finally { busy = false; render(); }
    }
    input.oninput = mode.onchange = () => {
      edited = true;
      if (observed && !review) draftTarget = identity(observed);
      render();
    };
    if (discard) discard.onclick = () => {
      if (discard.disabled) return;
      input.value = observed.saved.manual_ppm; mode.value = observed.saved.mode;
      edited = false; review = false; draftTarget = identity(observed); render();
    };
    if (adopt) adopt.onclick = () => {
      if (adopt.disabled) return;
      draftTarget = identity(observed); review = false; render();
    };
    read.onclick = ()=>run(load); save.onclick = ()=>run(commit);
    render();
    return {load,setAvailability(value) { available = value; render(); },
      invalidate() { ++epoch; revision = ''; observed = null; render(); }};
  }
  root.WsprryRfCalibration = {ppm,supported,create};
  if (typeof module !== 'undefined') module.exports = root.WsprryRfCalibration;
})(globalThis);

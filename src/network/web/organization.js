'use strict';
// Navigation changes only presentation. Paths are reloadable aliases on each
// admitted carrier; fragments remain exclusively receipt/bookmark context.
(() => {
  const station = $('station-area'), wifi = $('wifi-host-area');
  function renderArea() {
    const deep = location.hash;
    const hostArea = location.pathname === '/wifi-host' ||
      ['#consumer-setup','#hostname-form','#wifi-host-area'].includes(deep);
    station.hidden = hostArea; wifi.hidden = !hostArea;
    $('station-link').setAttribute('aria-current',hostArea ? 'false' : 'page');
    $('wifi-host-link').setAttribute('aria-current',hostArea ? 'page' : 'false');
  }
  for (const link of document.querySelectorAll('#area-nav a,[data-area-link]')) {
    link.addEventListener('click',event => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      // Keep receipt bytes verbatim, including uncertain-save evidence.
      const receipt = /^#(?:save|hostname-return)=/.test(location.hash) ? location.hash : '';
      history.pushState(null,'',link.getAttribute('href') + receipt);
      renderArea();
      (station.hidden ? wifi : station).scrollIntoView?.({block:'start'});
    });
  }
  addEventListener('popstate',renderArea);
  addEventListener('hashchange',renderArea);
  renderArea();

  for (const kind of ['station','network']) {
    const form = $('engineering-' + kind + '-form');
    form.addEventListener('input',() => {
      if (kind === 'station') engineeringStationDirty = true;
      else engineeringNetworkDirty = true;
      dirty = true; cancelReconnect();
    });
    form.onsubmit = event => {
      event.preventDefault();
      for (const input of form.querySelectorAll('input')) if (!input.reportValidity()) return;
      if (kind === 'network') setPasswordVisible('config-password',false);
      return action(async () => {
      if (radio) throw new Error('Use the transactional consumer editor');
      if (!currentConfig) throw new Error('Complete initial configuration through the existing commissioning workflow first');
      const f = $('config').elements;
      const patch = kind === 'station' ? {station:{callsign:f.callsign.value.trim().toUpperCase(),
        locator:f.locator.value.trim().toUpperCase(),power_dbm:Number(f.power_dbm.value)}} :
        {wifi:{ssid:f.ssid.value,password:f.password.value || null,ntp_ipv4:f.ntp_ipv4.value.trim()}};
      const application = await readApplication();
      if (kind === 'station') await reviewWspr(patch.station,'draft-wspr-plan');
      const descriptor = capabilities?.configuration_updates;
      if (descriptor?.schema !== 'transmitter-config-update/1' || descriptor.path !== '/api/v1/config/update' ||
          descriptor.method !== 'POST' || !descriptor.modes?.includes('merge'))
        throw new Error('This firmware has not advertised scoped configuration saves. Your draft is preserved');
      // Do not silently rebase an edit onto another client's configuration.
      if (application.revision !== revision) { requireReadback(); throw new Error('Saved settings changed. Read and review them before saving'); }
      try {
        const result = await api(applicationVersion === 2 ? 'config/update/2' : 'config/update','POST',
          {schema:'transmitter-config-update/1',target:application.data.target,mode:'merge',config:patch},revision);
        currentConfig = checkedConfig(result,false); revision = result.revision;
        if (kind === 'station') engineeringStationDirty = false;
        else engineeringNetworkDirty = false;
        await refresh();
        notice(kind === 'station' ? 'Station identity saved. Other drafts are unchanged.' :
          'Wi-Fi settings saved. Use Restart device to apply them. Other drafts are unchanged.');
      } finally { if (kind === 'network') clearPassword('config-password'); }
    }); };
  }
  $('initial-config').onclick = () => {
    for (const id of ['engineering-station-form','engineering-network-form','config'])
      for (const input of $(id).querySelectorAll('input,textarea')) if (!input.reportValidity())
        return notice('Complete station, Wi-Fi and schedules in both areas before creating the initial configuration',true);
    setPasswordVisible('config-password',false);
    return action(async () => {
    if (radio || currentConfig !== null) throw new Error('Initial configuration is available only for an unconfigured engineering deployment');
    const f = $('config').elements;
    const schedules = f.schedules.value.trim() ? f.schedules.value.trim().split('\n').map(line => {
      if (!/^\s*\d+\s*\/\s*\d+\s*$/.test(line)) throw new Error('Use period / phase for each schedule');
      const [period_s,phase_s] = line.split('/').map(Number); return {period_s,phase_s};
    }) : [];
    await readApplication();
    const station = {callsign:f.callsign.value.trim().toUpperCase(),locator:f.locator.value.trim().toUpperCase(),power_dbm:Number(f.power_dbm.value)};
    await reviewWspr(station,'draft-wspr-plan');
    const config = {version:1,enabled:f.enabled.checked,station,
      wifi:{ssid:f.ssid.value,password:f.password.value,ntp_ipv4:f.ntp_ipv4.value.trim()},schedules,
      pins:pinChoices ? readPins() : undefined,expires_utc_s:f.expiry.value ? Date.parse(f.expiry.value + 'Z')/1000 : 0};
    try {
      const result = await api(applicationVersion === 2 ? 'config/2' : 'config','PUT',config,revision);
      const confirmed = checkedConfig(result,false); revision = result.revision;
      engineeringStationDirty = false; engineeringNetworkDirty = false; fill(confirmed);
      await refresh(); notice('Initial complete configuration saved. Restart applies network and pin settings.');
    } finally { clearPassword('config-password'); }
  }); };
  const hasDraft = () => dirty || consumerSetupDirty || hostnameDraft ||
    engineeringStationDirty || engineeringNetworkDirty || $('message-text').value || $('job-file').files?.length;
  addEventListener('beforeunload',event => {
    if (hasDraft()) { event.preventDefault(); event.returnValue = ''; }
  });
  $('consumer-resume').addEventListener('click',event => {
    if (hasDraft() && !confirm('Continue at this address? Copy unsaved drafts before leaving this tab.')) event.preventDefault();
  });
})();

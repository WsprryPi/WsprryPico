'use strict';
// Fixed section IDs are presentation only; they never select API authority.
(() => {
  const station = $('station-area'), wifi = $('wifi-host-area');
  const sections = new Map([
    ['radio-settings','station'],['time-calibration','station'],['radio-pins','station'],['message-section','station'],
    ['wifi-settings','wifi-host'],['pico-password-section','wifi-host'],['hostname-section','wifi-host'],
    ['connection-section','wifi-host'],['saved-settings','station'],['device-diagnostics','station']
  ]);
  const aliases = new Map([
    ['hostname-form','hostname-section'],['station-identity','radio-settings'],
    ['engineering-station-form','radio-settings'],['consumer-station-form','radio-settings'],
    ['radio-settings-heading','radio-settings'],['job-heading','message-section'],
    ['station-area','radio-settings'],['wifi-host-area','wifi-settings']
  ]);
  const setupSection = () => (consumerAttempt?.kind || setupResultKind) === 'network' ? 'wifi-settings' : 'radio-settings';
  const pendingSection = () => consumerAttempt ? setupSection() : returnReceipt ? 'hostname-section' : 'saved-settings';
  const receipt = () => /^#(?:save|hostname-return)=/.test(location.hash);
  const stateKey = 'wsprrypicoPresentation';
  function fragment() {
    if (receipt() || location.hash.length > 100) return null;
    try { const id=decodeURIComponent(location.hash.slice(1)); return sections.has(id) || id==='top' ? id : id==='consumer-setup' ? setupSection() : aliases.get(id) || null; }
    catch { return null; }
  }
  function setArea(area) {
    const hostArea = area === 'wifi-host';
    station.hidden = hostArea; wifi.hidden = !hostArea;
    $('station-link').setAttribute('aria-current',hostArea ? 'false' : 'page');
    $('wifi-host-link').setAttribute('aria-current',hostArea ? 'page' : 'false');
  }
  function closePopovers() { utcEditors.forEach(editor=>editor.close()); }
  function reveal(node, focus = false) {
    if (!node) return;
    if (node === $('saved-settings')) showSettingsRecovery();
    const area=node.closest?.('[data-task-area]')?.getAttribute('data-task-area');
    if (area) setArea(area);
    for (let parent=node; parent; parent=parent.parentElement) if (parent.tagName === 'DETAILS') parent.open=true;
    if (focus) {
      const target=node.tagName==='DETAILS' ? node.querySelector('summary') : node;
      target?.focus({preventScroll:true}); node.scrollIntoView?.({block:'start'});
    }
  }
  function top() {
    settingsReviewRequested = false; renderSettingsRecovery();
    closePopovers();
    $('device-name').focus({preventScroll:true});
    for (const id of sections.keys()) {
      const section=$(id);
      for (const child of section.querySelectorAll('details')) child.open=false;
      section.open=false;
    }
    globalThis.scrollTo?.({top:0,left:0,behavior:'auto'});
  }
  function restore(focus=false) {
    const saved=history.state?.[stateKey];
    const id=fragment() || (receipt() && (sections.has(saved?.section) || saved?.section==='top') ? saved.section : null);
    const savedArea=['station','wifi-host'].includes(saved?.area)?saved.area:null;
    const area=sections.get(id) || (receipt() && !savedArea ? sections.get(pendingSection()) : savedArea) || (location.pathname==='/wifi-host' ? 'wifi-host' : 'station');
    setArea(area);
    if (id==='top') { if(focus) top(); else if(receipt()) reveal($(pendingSection())); }
    else if (id) reveal($(id),focus);
    else if (receipt() && !savedArea) reveal($(pendingSection()));
  }
  function navigate(id,area,path) {
    closePopovers();
    const prior=history.state;
    const existing=prior && typeof prior==='object' && !Array.isArray(prior) ? prior : prior===null || prior===undefined ? {} : {wsprrypicoPreviousState:prior};
    const next={...existing,[stateKey]:{section:id,area}};
    // There is exactly one fragment. Receipt bytes remain verbatim; only a
    // bounded section choice is stored in namespaced History presentation data.
    const hash=receipt() ? location.hash : id ? '#'+id : '';
    history.pushState(next,'',path+location.search+hash);
    setArea(area);
    if(id==='top') top();
    else if(id) reveal($(id),true);
    else {
      $(area==='wifi-host'?'wifi-host-link':'station-link').focus({preventScroll:true});
      globalThis.scrollTo?.({top:0,left:0,behavior:'auto'});
    }
  }
  for (const link of document.querySelectorAll('a[href]')) {
    if (!/^(?:\/station|\/wifi-host|#)/.test(link.getAttribute('href') || '')) continue;
    link.addEventListener('click',event=>{
      if(event.button!==0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      // Pending result links can move between station and Wi-Fi after load.
      const [path,hash]=(link.getAttribute('href') || '').split('#');
      const id=sections.has(hash) || hash==='top' ? hash : hash==='consumer-setup' ? setupSection() : aliases.get(hash);
      if (hash && !id || path && !['/station','/wifi-host'].includes(path)) return;
      event.preventDefault();
      const area=sections.get(id) || (path ? path==='/wifi-host' ? 'wifi-host' : 'station' : station.hidden ? 'wifi-host' : 'station');
      navigate(id || null,area,path || (area==='wifi-host' ? '/wifi-host' : '/station'));
    });
  }
  document.addEventListener('invalid',event=>reveal(event.target),true);
  for(const id of sections.keys()) {
    const section=$(id);
    section.addEventListener('toggle',()=>{
      if (!section.open) {
        closePopovers();
        if (section.contains(document.activeElement) && document.activeElement!==section.querySelector('summary')) section.querySelector('summary').focus({preventScroll:true});
      }
    });
  }
  globalThis.WsprryPicoSections={reveal,top,recovery:()=>reveal($('saved-settings')),setup:()=>reveal($(pendingSection()))};
  addEventListener('popstate',()=>restore(true));
  addEventListener('hashchange',()=>restore(true));
  restore(Boolean(fragment()));
  if(consumerAttempt || returnReceipt) reveal($(pendingSection()));

  for (const kind of ['station','network']) {
    const form = $('engineering-' + kind + '-form');
    form.addEventListener('input',event => {
      editedProgress(event);
      if (kind === 'station') engineeringStationDirty = true;
      else engineeringNetworkDirty = true;
      dirty = true; cancelReconnect();
      showDraftComparison();
    });
    form.onsubmit = event => {
      event.preventDefault();
      if (supportsProgress()) return action(() => saveConfigProgress(kind));
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
      if (kind === 'station') await reviewWspr(patch.station);
      const descriptor = capabilities?.configuration_updates;
      if (!WsprryControl.supported('configuration_updates',descriptor))
        throw new Error('This firmware has not advertised scoped configuration saves. Your draft is preserved');
      // Do not silently rebase an edit onto another client's configuration.
      if (application.revision !== revision) { requireReadback(); throw new Error('Saved settings changed. Read and review them before saving'); }
      try {
        const result = await api('config/update','POST',
          {schema:'config-update',target:application.data.target,mode:'merge',config:patch},revision);
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
    if (supportsProgress()) return action(() => applyProgressDomain('all'));
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
    await reviewWspr(station);
    const config = {version:1,enabled:f.enabled.checked,station,
      wifi:{ssid:f.ssid.value,password:f.password.value,ntp_ipv4:f.ntp_ipv4.value.trim()},schedules,
      pins:pinChoices ? readPins() : undefined,expires_utc_s:f.expiry.value ? Date.parse(f.expiry.value + 'Z')/1000 : 0};
    try {
      const {version:_storageVersion,...patch} = config;
      const application = await readApplication();
      const result = await api('config/update','POST',{schema:'config-update',target:application.data.target,mode:'merge',config:patch},revision);
      const confirmed = checkedConfig(result,false); revision = result.revision;
      engineeringStationDirty = false; engineeringNetworkDirty = false; fill(confirmed);
      await refresh(); notice('Initial complete configuration saved. Restart applies network and pin settings.');
    } finally { clearPassword('config-password'); }
  }); };
  addEventListener('beforeunload',event => {
    if (hasUnsavedDraft()) { event.preventDefault(); event.returnValue = ''; }
  });
  $('consumer-resume').addEventListener('click',event => {
    if (hasUnsavedDraft() && !confirm('Continue at this address? Copy unsaved drafts before leaving this tab.')) event.preventDefault();
  });
})();

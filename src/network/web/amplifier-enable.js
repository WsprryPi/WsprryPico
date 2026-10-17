// MIT. Explicit negotiation for amplifier-aware, closed management resources.
(function(root) {
  'use strict';
  const descriptor = {schema:'transmitter-amplifier-enable/1',pins:'/api/v1/pins/2',validate:'/api/v1/pins/validate/2',config:'/api/v1/config/4',update:'/api/v1/config/update/4',update_schema:'transmitter-config-update/3',hardware:'/api/v1/hardware/3',application:'/api/v1/application/4',progress:'/api/v1/progress/3',progress_schema:'transmitter-progress/3',default_pin:null,default_active_high:true,activation:'restart'};
  function supported(v) {
    return v && Object.keys(v).sort().join(',') === [...Object.keys(descriptor),'execution'].sort().join(',') &&
      Object.entries(descriptor).every(([key,value])=>v[key] === value) &&
      ['local_job','inhibited_inactive_only'].includes(v.execution);
  }
  function select(path,body) {
    const routes = {config:'config/4','config/2':'config/4','config/3':'config/4',
      'config/update':'config/update/4','config/update/2':'config/update/4','config/update/3':'config/update/4',
      'application/2':'application/4',pins:'pins/2','pins/validate':'pins/validate/2',
      progress:'progress/3','progress/2':'progress/3','progress/update':'progress/update/3',
      'progress/update/2':'progress/update/3','progress/apply':'progress/apply/3','progress/apply/2':'progress/apply/3'};
    const selected = routes[path] || path;
    if (body?.schema?.startsWith('transmitter-progress/') && selected.startsWith('progress/'))
      body = {...body,schema:'transmitter-progress/3'};
    if (body?.schema?.startsWith('transmitter-config-update/') && selected === 'config/update/4')
      body = {...body,schema:'transmitter-config-update/3'};
    return {path:selected,body};
  }
  root.WsprryAmplifier = {supported,select};
  if (typeof module !== 'undefined') module.exports = {supported,select};
})(typeof window === 'undefined' ? globalThis : window);

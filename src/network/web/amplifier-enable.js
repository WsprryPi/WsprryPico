// MIT. Explicit negotiation for amplifier-aware, closed management resources.
(function(root) {
  'use strict';
  const control = root.WsprryControl || (typeof module !== 'undefined' && module.exports ? require('./control-contract.js') : null);
  if (!control) throw new Error('The control definitions could not be loaded. Reload the Pico page.');
  const descriptor = control.descriptors.amplifier_enable;
  function supported(value) { return control.supported('amplifier_enable',value); }
  root.WsprryAmplifier = {supported};
  if (typeof module !== 'undefined') module.exports = {supported};
})(typeof window === 'undefined' ? globalThis : window);

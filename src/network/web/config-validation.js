'use strict';
function validSavedConfig(c) {
  if (c === null) return true;
  const object = v => v && typeof v === 'object' && !Array.isArray(v);
  const ascii = (v,min,max) => typeof v === 'string' && v.length >= min && v.length <= max && /^[\x20-\x7e]*$/.test(v);
  const gp = v => v === null || Number.isInteger(v) && (v >= 0 && v <= 22 || v >= 26 && v <= 28);
  if (!object(c) || c.version !== 1 || typeof c.enabled !== 'boolean' ||
      !object(c.station) || !ascii(c.station.callsign,3,12) || !/^(?:[A-Z0-9]+(?:\/[A-Z0-9]+)*|<[A-Z0-9]+(?:\/[A-Z0-9]+)*>)$/.test(c.station.callsign) || !/^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$/.test(c.station.locator) ||
      ![0,3,7,10,13,17,20,23,27,30,33,37,40,43,47,50,53,57,60].includes(c.station.power_dbm) ||
      !object(c.wifi) || !ascii(c.wifi.ssid,0,32) || c.wifi.password !== null || !ascii(c.wifi.ntp_ipv4,1,253) ||
      !Array.isArray(c.schedules) || c.schedules.length > 8 || !c.schedules.every(s=>object(s) &&
        Number.isInteger(s.period_s) && s.period_s >= 120 && s.period_s <= 86400 && s.period_s % 120 === 0 && 86400 % s.period_s === 0 &&
        Number.isInteger(s.phase_s) && s.phase_s >= 0 && s.phase_s < s.period_s && s.phase_s % 120 === 0) ||
      c.expires_utc_s !== undefined && (!Number.isSafeInteger(c.expires_utc_s) || c.expires_utc_s !== 0 && (c.expires_utc_s < 1735689600 || c.expires_utc_s >= 4102444800))) return false;
  for (const name of ['allow_unqualified_frequency','allow_non_amateur_frequency']) if (c[name] !== undefined && typeof c[name] !== 'boolean') return false;
  if (c.pins !== undefined) {
    const p=c.pins;
    if (!object(p) || !['direct','i2c'].includes(p.engine) || !gp(p.rf_gp) || !gp(p.button_gp) || !gp(p.amplifier_gp) || !gp(p.indicator_gp) ||
        !(p.i2c_pair === null || Number.isInteger(p.i2c_pair) && p.i2c_pair >= 0 && p.i2c_pair < 12) ||
        !Array.isArray(p.lpf_gps) || p.lpf_gps.length > 26 || !p.lpf_gps.every(n=>n !== null && gp(n)) ||
        !['onboard_led','external','disabled'].includes(p.indicator) || typeof p.indicator_active_high !== 'boolean') return false;
  }
  return true;
}

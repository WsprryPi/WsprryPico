'use strict';
function validSavedConfig(c) {
  if (c === null) return true;
  const object = v => v && typeof v === 'object' && !Array.isArray(v);
  const ascii = (v,min,max) => typeof v === 'string' && v.length >= min && v.length <= max && /^[\x20-\x7e]*$/.test(v);
  const gp = v => v === null || Number.isInteger(v) && (v >= 0 && v <= 22 || v >= 26 && v <= 28);
  const known=['enabled','station','wifi','schedules','pins','expires_utc_s','allow_unqualified_frequency','allow_non_amateur_frequency','gpio_drive_ma'];
  if (!object(c) || Object.keys(c).some(k=>!known.includes(k)) || typeof c.enabled !== 'boolean' ||
      !object(c.station) || Object.keys(c.station).sort().join(',') !== 'callsign,locator,power_dbm' || !ascii(c.station.callsign,3,12) || !/^(?:[A-Z0-9]+(?:\/[A-Z0-9]+)*|<[A-Z0-9]+(?:\/[A-Z0-9]+)*>)$/.test(c.station.callsign) || !/^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$/.test(c.station.locator) ||
      ![0,3,7,10,13,17,20,23,27,30,33,37,40,43,47,50,53,57,60].includes(c.station.power_dbm) ||
      !object(c.wifi) || Object.keys(c.wifi).sort().join(',') !== 'ntp_ipv4,password,ssid' || !ascii(c.wifi.ssid,0,32) || c.wifi.password !== null || !ascii(c.wifi.ntp_ipv4,1,253) ||
      !Array.isArray(c.schedules) || c.schedules.length > 8 || !c.schedules.every(s=>object(s) &&
        Object.keys(s).sort().join(',') === 'period_s,phase_s' && Number.isInteger(s.period_s) && s.period_s >= 120 && s.period_s <= 86400 && s.period_s % 120 === 0 && 86400 % s.period_s === 0 &&
        Number.isInteger(s.phase_s) && s.phase_s >= 0 && s.phase_s < s.period_s && s.phase_s % 120 === 0) ||
      c.expires_utc_s !== undefined && (!Number.isSafeInteger(c.expires_utc_s) || c.expires_utc_s !== 0 && (c.expires_utc_s < 1735689600 || c.expires_utc_s >= 4102444800))) return false;
  for (const name of ['allow_unqualified_frequency','allow_non_amateur_frequency']) if (c[name] !== undefined && typeof c[name] !== 'boolean') return false;
  if (![2,4,8,12].includes(c.gpio_drive_ma)) return false;
  if (c.pins !== undefined) {
    const p=c.pins;
    if (!object(p) || Object.keys(p).sort().join(',') !== 'amplifier_active_high,amplifier_gp,button_gp,engine,i2c_pair,indicator,indicator_active_high,indicator_gp,lpf_gps,rf_gp' || !['direct','i2c'].includes(p.engine) || !gp(p.rf_gp) || !gp(p.button_gp) || !gp(p.amplifier_gp) || !gp(p.indicator_gp) ||
        !(p.i2c_pair === null || Number.isInteger(p.i2c_pair) && p.i2c_pair >= 0 && p.i2c_pair < 12) ||
        !Array.isArray(p.lpf_gps) || p.lpf_gps.length > 26 || !p.lpf_gps.every(n=>n !== null && gp(n)) ||
        !['onboard_led','external','disabled'].includes(p.indicator) || typeof p.indicator_active_high !== 'boolean' ||
        typeof p.amplifier_active_high !== 'boolean') return false;
  }
  return true;
}

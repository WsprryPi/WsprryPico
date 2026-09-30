import assert from 'node:assert/strict';
import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {hkdf} from '@noble/hashes/hkdf.js';
import {chacha20poly1305} from '@noble/ciphers/chacha.js';
import {claimTranscript, claimPlaintext, sealOwnerClaim} from './owner-claim.js';

const hex = (value) => Buffer.from(value, 'hex');
const owner = hex('046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c2964fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5');
const sequence = (start, size) => Uint8Array.from({length: size}, (_, i) => i + start);
const fields = {origin: 'http://192.168.4.1',
  deviceId: Buffer.from(sequence(1, 16)).toString('hex'),
  bootId: Buffer.from(sequence(17, 16)).toString('hex'),
  slotId: Buffer.from(sequence(33, 16)).toString('hex'),
  ownerPublicKey: owner, browserPublicKey: sequence(49, 32),
  picoPublicKey: sequence(81, 32),
  browserNonce: Buffer.from(sequence(113, 16)).toString('hex'),
  requestId: Buffer.from(sequence(129, 16)).toString('hex'),
  source: 4, generation: '1'};
const settings = {ssid: 'LabNet', password: 'test-only-password',
  callsign: 'K1ABC', locator: 'FN20', powerDbm: 30};
const aad = claimTranscript(fields);
assert.equal(aad.length, 261);
// Calculated independently with Python hashlib and struct.
assert.equal(Buffer.from(sha256(aad)).toString('hex'),
  'b13fd05696af4d82e4684aacdde110cefbfe3918a65b3da56dc4451f020d988f');
assert.equal(Buffer.from(claimPlaintext(settings)).toString('hex'),
  '064c61624e657412746573742d6f6e6c792d70617373776f7264054b31414243464e32301e');
assert.equal(Buffer.from(claimPlaintext({...settings, ssid: '', password: ''})).toString('hex'),
  '0000054b31414243464e32301e');
assert.throws(() => claimPlaintext({...settings, ssid: '', password: 'test-only-password'}));
for (const patch of [{deviceId: 'ff' + fields.deviceId.slice(2)},
  {bootId: 'ff' + fields.bootId.slice(2)}, {slotId: 'ff' + fields.slotId.slice(2)},
  {ownerPublicKey: Uint8Array.from(owner, (b, i) => i === 1 ? b ^ 1 : b)},
  {browserPublicKey: sequence(50, 32)}, {picoPublicKey: sequence(82, 32)},
  {browserNonce: 'ff' + fields.browserNonce.slice(2)},
  {requestId: 'ff' + fields.requestId.slice(2)},
  {source: 2}, {generation: '2'}])
  assert.notEqual(Buffer.from(sha256(claimTranscript({...fields, ...patch}))).toString('hex'),
    Buffer.from(sha256(aad)).toString('hex'));
assert.throws(() => claimTranscript({...fields, origin: 'http://192.168.4.2'}));
assert.notEqual(Buffer.from(sha256(claimTranscript({...fields, source: 5}))).toString('hex'),
  Buffer.from(sha256(aad)).toString('hex'));
assert.throws(() => claimTranscript({...fields, generation: '01'}));
assert.throws(() => claimTranscript({...fields, generation: '1\n'}));
assert.throws(() => claimTranscript({...fields, deviceId: fields.deviceId + '\n'}));
assert.throws(() => claimPlaintext({...settings, password: 'short'}));
assert.throws(() => claimPlaintext({...settings, password: settings.password + '\n'}));
assert.throws(() => claimPlaintext({...settings, callsign: 'bad'}));
assert.throws(() => claimPlaintext({...settings, locator: settings.locator + '\n'}));
assert.equal(Buffer.from(claimPlaintext({...settings, ssid: '', password: '', locator: 'FN20XX'}))
  .toString('hex'), '0000054b31414243464e323058581e');
assert.equal(claimPlaintext({ssid: 'A'.repeat(32), password: 'p'.repeat(63),
  callsign: 'KA1BCD', locator: 'FN20AA', powerDbm: 60}).length, 111);
for (const locator of ['FN20A', 'FN20AAA', 'FN20AY', 'FN20ZA', 'SN20AA', 'FN20aa'])
  assert.throws(() => claimPlaintext({...settings, locator}));
for (const callsign of ['AA0NT/P', 'PJ4/AA0NT', 'PJ4/AA0NT/P', 'AA0NT/ABCDEF', '3DA0ABC'])
  assert.ok(claimPlaintext({...settings, callsign, locator: 'EM18AA'}));
for (const callsign of ['AA0NT/ABCDEFG', '/AA0NT', 'AA0NT/', 'AA0NT//P', 'AA0NT-P', 'aa0nt/P',
  'AAAAAA', '123456', 'AA0NT\n']) assert.throws(() => claimPlaintext({...settings, callsign}));

const browserSecret = hex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a');
const picoSecret = hex('5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb');
const exchange = {...fields, browserPublicKey: x25519.getPublicKey(browserSecret),
  picoPublicKey: x25519.getPublicKey(picoSecret)};
const nonce = sequence(0, 12);
const result = sealOwnerClaim(exchange, browserSecret, nonce, settings);
assert.equal(Buffer.from(browserSecret).toString('hex'), '00'.repeat(32));
const mismatchSecret = hex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a');
assert.throws(() => sealOwnerClaim({...exchange, browserPublicKey: sequence(49, 32)},
  mismatchSecret, nonce, settings));
assert.equal(Buffer.from(mismatchSecret).toString('hex'), '00'.repeat(32));
const peerShared = x25519.getSharedSecret(picoSecret, exchange.browserPublicKey);
const exchangeAad = claimTranscript(exchange);
const key = hkdf(sha256, peerShared, sha256(exchangeAad),
  new TextEncoder().encode('WsprryPico owner claim AEAD v1'), 32);
const sealed = Buffer.concat([Buffer.from(result.ciphertext, 'base64url'),
  Buffer.from(result.tag, 'base64url')]);
assert.deepEqual(chacha20poly1305(key, nonce, exchangeAad).decrypt(sealed),
  claimPlaintext(settings));
const alteredAad = claimTranscript({...exchange, generation: '2'});
assert.throws(() => chacha20poly1305(key, nonce, alteredAad).decrypt(sealed));
// This exact source-5 station-only envelope is opened by the real Pico crypto
// host test, rather than a mock HTTP handler that never decrypts the request.
const updateFields = {...exchange, source: 5, generation: '3'};
assert.equal(Buffer.from(sha256(claimTranscript(updateFields))).toString('hex'),
  '8d9b7141924fe6a5b3ff430ccb75a9f004989587e20e533a80f515c1398efdb9');
const update = sealOwnerClaim(updateFields,
  hex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a'),
  nonce, {ssid: '', password: '', callsign: 'AA0NT', locator: 'EM18', powerDbm: 20});
assert.equal(update.ciphertext, 'U4dqWEtiMhoFzBnB4A');
assert.equal(update.tag, 'FBv45vIeTQCvbHa4kRE6NA');
const six = sealOwnerClaim(updateFields,
  hex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a'),
  nonce, {ssid: '', password: '', callsign: 'AA0NT', locator: 'EM18AA', powerDbm: 20});
assert.equal(six.ciphertext, 'U4dqWEtiMhoFzBnBtfg6');
assert.equal(six.tag, 'XQVKa1R4zGBUIvIM6TAjEA');
const maximum = sealOwnerClaim(updateFields,
  hex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a'),
  nonce, {ssid: 'A'.repeat(32), password: 'p'.repeat(63), callsign: 'KA1BCD',
    locator: 'FN20XX', powerDbm: 60});
assert.equal(maximum.ciphertext,
  'c8YuWEsTPQ8BwGm4tfhv1wJ0opkd68Mv3bPB6mOzKWDl_Ew3pGkcC_0Xn3eC7gywq0N_JsqSraAK-gs6HLC5' +
  'EEGK82O9dhD3n2by2ZeeJsMoekf5PnY1ABUmIsbJPsthb_dkXNPK_HxD4mnn3NGR');
assert.equal(maximum.tag, 'DBWKeXp9RLkWZZTqUsyAGw');
const extended = sealOwnerClaim(updateFields,
  hex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a'),
  nonce, {ssid: 'A'.repeat(32), password: 'p'.repeat(63), callsign: 'AA0NT/ABCDEF',
    locator: 'EM18XX', powerDbm: 60});
assert.equal(extended.ciphertext,
  'c8YuWEsTPQ8BwGm4tfhv1wJ0opkd68Mv3bPB6mOzKWDl_Ew3pGkcC_0Xn3eC7gywq0N_JsqSraAK-gs6HLC5' +
  'EEGK82O9dhD3n2by2ZeeJsMoekf5PnY1ABUmIsbJPsthb_1uXNLG6xdE7hiTwc_ow2Dg_nER');
assert.equal(extended.tag, 'vY0RtxhmK1balnTmctLM7Q');
peerShared.fill(0); key.fill(0); picoSecret.fill(0);
console.log('owner claim browser transcript and envelope passed');

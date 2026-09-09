# TLS 1.3 certificate rejection alerts

The Phase 11.4 F3 investigation reproduced certificate rejections reported by
OpenSSL as bad-record-MAC errors. Mbed TLS 3.6.6 keeps the server outbound
handshake transform until handshake wrap-up; its certificate rejection can occur
after Server Finished, when the client already expects application traffic keys.
The actual-TLS regression originally accepted any TLS failure and missed this.

The build generates three narrowly modified upstream translation units under
`mbedtls-alert-overlay/`. The external SDK remains unmodified and revision-pinned.
`scripts/prepare_mbedtls_alert_overlay.py` checks exact SHA-256 input hashes and
unique patch anchors before generating the copies. Both host tests and firmware
replace exactly one copy of each affected source; configuration fails otherwise.
Original upstream licensing headers are retained; generated copies identify the
modifications. Apache-2.0 is selected for these derived Mbed TLS files.

The changes are limited to:

- Encrypt a fatal server alert with the available TLS 1.3 application transform
  after Server Finished. Preserve an already selected transform and pending
  ciphertext, including WANT_WRITE retries. Successful handshakes are unchanged.
- Emit TLS 1.3 `certificate_required` for an empty required client certificate,
  replacing the obsolete `no_certificate` code in the TLS 1.3 parser.
- Retain certificate-verification alerts in the TLS 1.3 pending-alert state
  across WANT_WRITE. The original common verifier discarded the send result;
  seven-byte writes with alternating backpressure reproduced the lost alert.
- Keep a rejected Pico connection inert for at most one second while queued TLS
  bytes are acknowledged. Never resume its handshake or dispatch application
  data. Immediate network loss and existing connection deadlines still close it.

Certificate validation, required mutual authentication, hostname/IP SAN checking,
ALPN, UTC validation and principal derivation remain enforced. Issuing replacement
credentials does not revoke old valid identities. The local patches must be
reassessed when changing the SDK/Mbed TLS pin; never carry them forward blindly.

The protocol basis is [RFC 8446 appendix A.2](https://www.rfc-editor.org/rfc/rfc8446#appendix-A.2)
and [section 4.4.2.4](https://www.rfc-editor.org/rfc/rfc8446#section-4.4.2.4).
The missing-certificate alert mapping is also described in
[upstream issue 10720](https://github.com/Mbed-TLS/mbedtls/issues/10720).
Physical and regression results belong to the F2/F3/F6 execution record.

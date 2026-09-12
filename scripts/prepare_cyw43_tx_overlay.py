#!/usr/bin/env python3
"""Preserve CYW43 transmit bytes across credit-wait RX; never edit the pinned SDK."""
import argparse
import hashlib
from pathlib import Path

REVISION = '055d64274b014dd7b1c2fc94d26e8a18face7124'
SHA256 = '7f4c93755b2ab911d18606652497b2f3cd08085ce63b3b1836171d375f806b10'


def transform(raw):
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError('Expected unmodified pinned CYW43 cyw43_ll.c at ' + REVISION)
    text = raw.decode()
    anchor = 'static int cyw43_sdpcm_send_common(cyw43_int_t *self, uint32_t kind, size_t len, uint8_t *buf) {'
    diagnostics = '''/* WsprryPico modification: NO_SYS/core-0 diagnostics; no payload logging. */
static uint32_t wsprry_tx_credit_waits, wsprry_tx_credit_preserved, wsprry_tx_credit_timeouts;
void wsprry_cyw43_tx_diagnostics(uint32_t *waits, uint32_t *preserved, uint32_t *timeouts) {
    *waits = wsprry_tx_credit_waits;
    *preserved = wsprry_tx_credit_preserved;
    *timeouts = wsprry_tx_credit_timeouts;
}
static void wsprry_tx_count(uint32_t *value) {
    if (*value != UINT32_MAX) {
        ++*value;
    }
}

'''
    if text.count(anchor) != 1:
        raise ValueError('CYW43 send anchor changed')
    text = text.replace(anchor, diagnostics + anchor)
    old = '''    cyw43_ll_bus_sleep((void *)self, false);

    // Wait until we are allowed to send'''
    new = '''    /* WsprryPico: RX credit polling and async callbacks reuse spid_buf.
     * Snapshot the already-built TX frame before either can overwrite it.
     * Per-call aligned storage also preserves an outer frame across a nested
     * send from an async callback. No heap allocation or shared TX scratch.
     * Includes bounded bus padding; never read outside the original buffer.
     */
    if (buf != self->spid_buf || len > sizeof(self->spid_buf) - SDPCM_HEADER_LEN) {
        return CYW43_FAIL_FAST_CHECK(-CYW43_EINVAL);
    }
    _Alignas(4) uint8_t wsprry_tx_bytes[sizeof(self->spid_buf)];
    _Static_assert(CYW43_WRITE_BYTES_PAD(sizeof(self->spid_buf)) <= sizeof(self->spid_buf),
        "CYW43 padding exceeds TX snapshot");
    memcpy(wsprry_tx_bytes, buf, CYW43_WRITE_BYTES_PAD(SDPCM_HEADER_LEN + len));
    buf = wsprry_tx_bytes;
    bool wsprry_waited = false;

    cyw43_ll_bus_sleep((void *)self, false);

    // Wait until we are allowed to send'''
    if text.count(old) != 1:
        raise ValueError('CYW43 credit-wait anchor changed')
    text = text.replace(old, new)
    old = '        uint32_t start_us = cyw43_hal_ticks_us();\n        uint32_t last_poke = start_us - 100000;'
    new = '''        wsprry_waited = true;
        wsprry_tx_count(&wsprry_tx_credit_waits);
''' + old
    if text.count(old) != 1:
        raise ValueError('CYW43 wait entry changed')
    text = text.replace(old, new)
    old = '                return CYW43_FAIL_FAST_CHECK(-CYW43_ETIMEDOUT);\n            }\n            CYW43_SDPCM_SEND_COMMON_WAIT;'
    new = '                wsprry_tx_count(&wsprry_tx_credit_timeouts);\n' + old
    if text.count(old) != 1:
        raise ValueError('CYW43 timeout changed')
    text = text.replace(old, new)
    old = '    size_t size = SDPCM_HEADER_LEN + len;\n\n    // create header'
    new = '''    if (wsprry_waited && memcmp(self->spid_buf + SDPCM_HEADER_LEN,
            buf + SDPCM_HEADER_LEN, len) != 0) {
        wsprry_tx_count(&wsprry_tx_credit_preserved);
    }

''' + old
    if text.count(old) != 1:
        raise ValueError('CYW43 post-wait anchor changed')
    text = text.replace(old, new)
    return ('/* Modified by WsprryPico: preserve TX across shared-buffer RX credit polling.\n'
            ' * Original licensing and attribution follow unchanged. */\n' + text)


def prepare(source, output):
    source = source.resolve(strict=True)
    output = output.resolve()
    if output.is_relative_to(source):
        raise ValueError('Overlay output must be outside the SDK checkout')
    rendered = transform((source / 'src/cyw43_ll.c').read_bytes())
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'cyw43_ll.c'
    if target.is_symlink():
        raise ValueError('Refusing a symlinked generated source')
    target.write_text(rendered)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    prepare(a.source, a.output)


if __name__ == '__main__':
    main()

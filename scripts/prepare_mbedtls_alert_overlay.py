#!/usr/bin/env python3
"""Generate narrow Apache-2.0 Mbed TLS 3.6.6 fixes; never modify the SDK."""
import argparse
import hashlib
from pathlib import Path

PINNED = {
    'ssl_tls.c': '842e5b2faa6155b8eacd7461276e34c4297fbe2b56325d8a96b9a87ba59cf636',
    'ssl_msg.c': '7365ec47a2e1e133693bad61ca6caa27c73d953279716f0a6bfb073e3a32f9fa',
    'ssl_tls13_generic.c': '26901c2aaf7b584c991836ed36448f88f616028ad2086de5b880d53f73cb648d',
}


def prepare(source, output):
    if output.resolve().is_relative_to(source.resolve()):
        raise ValueError("Overlay output must be outside the SDK checkout")
    originals = {}
    for name, digest in PINNED.items():
        raw = (source / 'library' / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f'{name}: expected unmodified pinned Mbed TLS 3.6.6')
        originals[name] = raw.decode()
    old = '    MBEDTLS_SSL_DEBUG_MSG(2, ("=> send alert message"));\n'
    new = """    /* WsprryPico modification: RFC 8446 A.2 switches server writes to
     * application keys after Server Finished, before client authentication.
     * 3.6.6 otherwise uses handshake keys for a certificate failure alert.
     * Do not reset an existing application sequence or a WANT_WRITE retry.
     */
#if defined(MBEDTLS_SSL_PROTO_TLS1_3) && defined(MBEDTLS_SSL_SRV_C)
    if (level == MBEDTLS_SSL_ALERT_LEVEL_FATAL &&
        ssl->conf->endpoint == MBEDTLS_SSL_IS_SERVER &&
        ssl->tls_version == MBEDTLS_SSL_VERSION_TLS1_3 &&
        ssl->transform_application != NULL &&
        ssl->transform_out != ssl->transform_application) {
        mbedtls_ssl_set_outbound_transform(ssl, ssl->transform_application);
    }
#endif

""" + old
    if originals['ssl_msg.c'].count(old) != 1:
        raise ValueError('pending alert anchor changed')
    originals['ssl_msg.c'] = originals['ssl_msg.c'].replace(old, new)
    old = '                    MBEDTLS_SSL_ALERT_MSG_NO_CERT,'
    if originals['ssl_tls13_generic.c'].count(old) != 1:
        raise ValueError('TLS 1.3 missing certificate anchor changed')
    originals['ssl_tls13_generic.c'] = originals['ssl_tls13_generic.c'].replace(
        old, '                    MBEDTLS_SSL_ALERT_MSG_CERT_REQUIRED, /* RFC 8446 4.4.2.4 */')
    # The common verifier ignored WANT_WRITE from an immediate alert. TLS 1.3
    # handshake_step already owns a pending-alert retry state; use that path.
    old = ("        mbedtls_ssl_send_alert_message(ssl, MBEDTLS_SSL_ALERT_LEVEL_FATAL,\n"
           "                                       alert);")
    if originals['ssl_tls.c'].count(old) != 1:
        raise ValueError('certificate verification alert anchor changed')
    new = """#if defined(MBEDTLS_SSL_PROTO_TLS1_3)
        if (ssl->tls_version == MBEDTLS_SSL_VERSION_TLS1_3) {
            /* WsprryPico: retain fatal certificate alerts across WANT_WRITE. */
            mbedtls_ssl_pend_fatal_alert(ssl, alert, ret);
        } else
#endif
        {
""" + old + "\n        }"
    originals['ssl_tls.c'] = originals['ssl_tls.c'].replace(old, new)
    output.mkdir(parents=True, exist_ok=True)
    for name, text in originals.items():
        banner = ('/* Modified by WsprryPico: TLS 1.3 certificate rejection alerts.\n'
                  ' * Derived from pinned Mbed TLS 3.6.6; Apache-2.0 selected.\n'
                  ' * See docs/development/tls-certificate-alerts.md. */\n')
        target = output / name
        content = banner + text
        if not target.exists() or target.read_text() != content:
            target.write_text(content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)

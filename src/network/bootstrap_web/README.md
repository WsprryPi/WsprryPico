# Wi-Fi bootstrap browser crypto candidate

This directory holds a browser-side candidate for the approved
[WiFi-Bootstrap/1](../../../docs/protocol/WiFi-Bootstrap-v1-proposal.md)
transcript. It is **not served by firmware yet**. The current blank AP remains
read-only until the runtime BOOTSEL safety gate and mutating protocol tests
pass. The selected iPhone captive sheet and Safari remain untested for this
crypto code.

The exact locked dependencies are `@noble/curves`, `@noble/hashes` and
`@noble/ciphers` 2.3.0. Their source repositories are
[curves](https://github.com/paulmillr/noble-curves),
[hashes](https://github.com/paulmillr/noble-hashes) and
[ciphers](https://github.com/paulmillr/noble-ciphers); all are MIT licensed.
The local `node_modules/@noble/*/LICENSE` files carry the full licenses. The
build uses pinned `esbuild` 0.28.2, with its own
[MIT license](https://github.com/evanw/esbuild/blob/master/LICENSE.md).
The generated bundle retains esbuild's bundled license notice. The package
lock fixes the fetched versions and integrity hashes. No remote import is
used by the resulting browser code.

From this directory, `npm ci`, `npm test`, and `npm run build` reproduce the
candidate. The build emits the ignored
`build/bootstrap-crypto.js` at the repository root; firmware does not consume
it. The known-answer test matches the synthetic vector and changes bound
transcript fields to check that the tag changes. A future enabled page must
feature-detect `crypto.getRandomValues`, execute `available()` before showing
the password field, and handle a failing captive sheet with Safari directions.

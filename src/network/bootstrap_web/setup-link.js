// Local presentation only: copying never enters the setup transaction.
export function createSetupLink(doc, {allowed = () => true} = {}) {
    const panel = doc.getElementById('setup-link-panel');
    if (!panel) return {update() {}, suspend() {}, resume() {}};
    const url = doc.getElementById('setup-url');
    const anchor = doc.getElementById('setup-hostname');
    const button = doc.getElementById('copy-setup-link');
    const status = doc.getElementById('setup-copy-status');
    const explanation = doc.getElementById('setup-link-state');
    let key, revision = 0, pending = false, suspended = false;

    function enable() { button.disabled = pending || suspended || !url.value || panel.hidden; }
    function select() { url.focus({preventScroll:true}); url.select(); }
    function feedback(text) { status.textContent = text; }
    button.addEventListener('click', async () => {
        if (button.disabled || suspended || panel.hidden || !allowed()) return;
        const value = url.value, captured = revision, focused = doc.activeElement;
        const selection = {start:url.selectionStart, end:url.selectionEnd, direction:url.selectionDirection};
        const current = () => captured === revision && !suspended && !panel.hidden && allowed();
        pending = true;
        enable();
        feedback('');
        try {
            if (globalThis.isSecureContext && globalThis.navigator?.clipboard?.writeText) {
                await globalThis.navigator.clipboard.writeText(value);
            } else {
                select();
                if (!doc.execCommand?.('copy')) throw new Error('copy unavailable');
                if (current()) {
                    url.setSelectionRange(selection.start, selection.end, selection.direction);
                    focused?.focus({preventScroll:true});
                }
            }
            if (current()) feedback('Link copied');
        } catch {
            if (current()) {
                // A delayed refusal must not pull focus away from another control.
                if (doc.activeElement === focused || doc.activeElement === url) select();
                feedback('Could not copy automatically. Select and copy this link.');
            }
        } finally { pending = false; enable(); }
    });
    return {
        update({hostname, phase, screen}) {
            const visible = ['credentials','checking','accepted','unconfirmed','connected','saved','unknown'].includes(screen);
            const next = JSON.stringify([hostname || '', phase, screen]);
            if (next !== key) { key = next; ++revision; feedback(''); }
            const destination = doc.getElementById(screen === 'credentials' ? 'setup-link-edit' : 'setup-link-result');
            // Do not repeatedly move a focused/selected control during status polling.
            if (panel.parentElement !== destination) destination.append(panel);
            panel.hidden = !visible;
            const value = hostname ? 'http://' + hostname + '/' : '';
            if (url.value !== value) url.value = value;
            anchor.hidden = !hostname;
            if (hostname) { anchor.textContent = hostname; anchor.href = value; }
            else { anchor.textContent = ''; anchor.removeAttribute('href'); }
            explanation.textContent = !hostname ? 'Link unavailable. Enter a valid hostname or wait for the current name to load.' :
                phase === 'saved' ? 'Saved Pico address. Name discovery and reachability are not confirmed.' :
                    'Intended Pico address. This link does not confirm that settings have been saved.';
            doc.getElementById('setup-link-help').textContent = screen === 'credentials' ?
                'Copy this link before saving. After the Pico restarts, reconnect to your normal Wi-Fi and paste it into your browser.' :
                'After the Pico restarts, reconnect to your normal Wi-Fi and paste this link into your browser.';
            enable();
        },
        suspend() { suspended = true; ++revision; feedback(''); enable(); },
        resume() { suspended = false; enable(); }
    };
}

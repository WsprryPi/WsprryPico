(function (root) {
  'use strict';
  // One intent owns the page until all of its bounded adapter work settles.
  // This is deliberately not a request queue, retry loop or transport lock.
  function create(doc, {refuse = () => {}, controls = () => []} = {}) {
    let active = null, serial = 0, panel = null, message, buttons, focus, suspended = false;
    function present(token) {
      if (!doc.body?.append || !doc.createElement) return;
      if (!panel) {
        panel = doc.createElement('dialog'); panel.id = 'submission-busy';
        panel.className = 'submission-busy';
        panel.setAttribute('aria-label', 'Pico request in progress');
        message = doc.createElement('p'); message.id = 'submission-message';
        message.setAttribute('role', 'status'); message.setAttribute('aria-live', 'polite');
        message.setAttribute('aria-atomic', 'true'); message.tabIndex = -1;
        panel.setAttribute('aria-describedby', message.id);
        buttons = doc.createElement('div'); buttons.className = 'submission-actions';
        panel.append(message, buttons); doc.body.append(panel);
        panel.addEventListener('cancel', event => { event.preventDefault(); active?.cancel?.(); });
      }
      focus = token.origin;
      message.textContent = token.message + ' Please wait; another action cannot start yet.';
      buttons.replaceChildren();
      for (const item of controls()) {
        const button = doc.createElement('button'); button.type = 'button';
        button.textContent = item.label; button.id = 'submission-' + item.id;
        button.onclick = () => { if (active === token) item.run(); };
        buttons.append(button);
      }
      doc.querySelector?.('main')?.setAttribute('aria-busy', 'true');
      if (!panel.open) panel.showModal();
      message.focus({preventScroll: true});
    }
    function hide(token) {
      if (active !== token) return;
      active = null;
      doc.querySelector?.('main')?.removeAttribute('aria-busy');
      const restore = panel?.contains(doc.activeElement);
      if (panel?.open) panel.close();
      if (restore) {
        const intended = token.focus || focus;
        const target = intended?.isConnected && !intended.matches(':disabled') && !intended.closest('[hidden]') && intended.getClientRects().length ? intended : doc.getElementById('access-toggle');
        target?.focus({preventScroll: true});
      }
    }
    // Native modal inertness handles real input; capture also rejects synthetic
    // events. The token below remains authoritative for direct handler calls.
    for (const type of ['click', 'submit']) doc.addEventListener?.(type, event => {
      if (!active || !panel?.open || panel.contains(event.target)) return;
      event.preventDefault(); event.stopImmediatePropagation();
      refuse('Wait for the current Pico request to finish. No additional action was sent.');
    }, true);
    return {
      get pending() { return active !== null; },
      get suspended() { return suspended; },
      get origin() { return active?.origin; },
      get token() { return active; },
      async run(fn, options = {}) {
        const preceding = !options.background && active?.background ? active.done : null;
        if (suspended || active && !preceding) { if (!options.background) refuse('Wait for the current Pico request to finish. No additional action was sent.'); return false; }
        let settled;
        const token = {id: ++serial, message: options.message || 'Contacting the Pico.', cancel: options.cancel,
          origin: doc.activeElement, background: Boolean(options.background), done: new Promise(resolve => { settled = resolve; })};
        active = token;
        try {
          if (!options.background) present(token);
          if (preceding) { options.drain?.(); await preceding; }
          await fn(token);
          return true;
        } finally { try { hide(token); } finally { settled(); } }
      },
      // Page lifecycle invalidates presentation only. It does not claim that a
      // dispatched write was cancelled or admit a second operation on restore.
      describe(text) { if (active && message) message.textContent = text; },
      focus(node) { if (active) active.focus = node; else node?.focus({preventScroll:true}); },
      suspend() { suspended = true; if (panel?.open) panel.close(); },
      resume() { suspended = false; if (active && !active.background) present(active); }
    };
  }
  root.WsprrySubmission = Object.freeze({create});
})(globalThis);

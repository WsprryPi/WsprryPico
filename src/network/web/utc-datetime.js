'use strict';
// The native datetime-local popup supplies OS-local defaults. These controls
// keep calendar arithmetic, defaults and the submitted wall-clock value in UTC.
(function(root) {
  const pad = value => String(value).padStart(2,'0');
  function parse(value) {
    if (!/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?$/.test(value)) return null;
    const canonical = value.replace(' ','T') + (value.length === 16 ? ':00' : '');
    const ms = Date.parse(canonical + 'Z');
    if (!Number.isFinite(ms) || new Date(ms).toISOString().slice(0,19) !== canonical) return null;
    return {ms,date:canonical.slice(0,10),time:canonical.slice(11),value:canonical};
  }
  const format = ms => new Date(ms).toISOString().slice(0,19);
  function select(value, part, selected, now) {
    const prior = parse(value) || parse(format(now));
    if (!['date','time'].includes(part)) return null;
    const pieces = value.split(/[T ]/), complete = pieces.length === 2 && pieces.every(Boolean);
    // Preserve a complete draft's other component, including an invalid draft
    // that the operator is correcting one component at a time.
    if (part === 'date') {
      if (!parse(selected + 'T00:00:00')) return null;
      return selected + 'T' + (complete ? pieces[1] : prior.time);
    }
    if (!parse('2000-01-01T' + selected)) return null;
    return (complete ? pieces[0] : prior.date) + 'T' + selected;
  }
  let dismissOpen = null;
  function create(input, now = Date.now) {
    const container = input.closest('[data-utc-picker]'), doc = input.ownerDocument;
    const dateButton = container.querySelector('[data-utc-date]');
    const timeButton = container.querySelector('[data-utc-time]');
    const panel = doc.createElement('div');
    panel.className = 'utc-panel'; panel.hidden = true;
    panel.id = (input.id || input.name) + '-picker';
    panel.setAttribute('role','group');
    container.append(panel);
    for (const button of [dateButton,timeButton]) {
      button.setAttribute('aria-controls',panel.id);
      button.setAttribute('aria-expanded','false');
    }
    let active = null, month = '', focusedDay = '';
    const disabled = () => input.disabled || input.readOnly || input.matches(':disabled');
    const node = (tag,text,className) => {
      const element = doc.createElement(tag);
      if (text !== undefined) element.textContent = text;
      if (className) element.className = className;
      return element;
    };
    const button = (text, action, label) => {
      const element = node('button',text);
      element.type = 'button'; element.onclick = action;
      if (label) element.setAttribute('aria-label',label);
      return element;
    };
    function validate() {
      input.setCustomValidity(input.value && !parse(input.value) ? 'Enter a UTC date and time as YYYY-MM-DD HH:MM:SS.' : '');
    }
    function write(value) {
      input.value = value; validate();
      input.dispatchEvent(new Event('input',{bubbles:true}));
      input.dispatchEvent(new Event('change',{bubbles:true}));
    }
    function complete() {
      const pieces = input.value.split(/[T ]/);
      if (pieces.length !== 2 || pieces.some(value=>!value)) write(format(now()));
      return parse(input.value) || parse(format(now()));
    }
    function close(focus = false) {
      panel.hidden = true;
      dateButton.setAttribute('aria-expanded','false'); timeButton.setAttribute('aria-expanded','false');
      if (dismissOpen === close) dismissOpen = null;
      if (focus && active && !disabled()) (active === 'date' ? dateButton : timeButton).focus();
    }
    function choose(part, value) {
      if (disabled()) { close(); return; }
      const selected = select(input.value,part,value,now());
      if (selected) { write(selected); close(true); }
    }
    function moveMonth(delta) {
      const value = new Date(month + '-01T00:00:00Z');
      value.setUTCMonth(value.getUTCMonth() + delta);
      const next = format(value.getTime()).slice(0,7);
      if (/^\d{4}-\d{2}$/.test(next)) {
        const focus = doc.activeElement?.getAttribute('aria-label');
        month = next; calendar();
        if (focus) panel.querySelector('button[aria-label="' + focus + '"]')?.focus();
      }
    }
    function calendar() {
      panel.replaceChildren(); panel.setAttribute('aria-label','Choose UTC date');
      const heading = node('div',undefined,'utc-month');
      const date = new Date(month + '-01T00:00:00Z');
      const title = node('strong',date.toLocaleDateString('en',{month:'long',year:'numeric',timeZone:'UTC'}));
      heading.append(button('Prev',()=>moveMonth(-1),'Previous month'),title,button('Next',()=>moveMonth(1),'Next month'));
      const table = node('table'); table.setAttribute('aria-label',title.textContent + ' UTC');
      const head = node('thead'), weekdays = node('tr');
      for (const day of ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']) { const cell = node('th',day); cell.scope = 'col'; weekdays.append(cell); }
      head.append(weekdays); table.append(head);
      const body = node('tbody'), selected = parse(input.value)?.date, today = format(now()).slice(0,10);
      const start = date.getUTCDay(), end = new Date(date.getTime());
      end.setUTCMonth(end.getUTCMonth() + 1); end.setUTCDate(0);
      let row;
      for (let slot = 0; slot < Math.ceil((start + end.getUTCDate()) / 7) * 7; ++slot) {
        if (slot % 7 === 0) { row = node('tr'); body.append(row); }
        const cell = node('td'), day = slot - start + 1;
        if (day > 0 && day <= end.getUTCDate()) {
          const value = month + '-' + pad(day), pick = button(String(day),()=>choose('date',value),value + ' UTC');
          pick.dataset.utcDay = value; pick.setAttribute('aria-pressed',String(value === selected));
          if (value === today) pick.setAttribute('aria-current','date');
          pick.onkeydown = event => {
            const offsets = {ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7};
            if (!(event.key in offsets)) return;
            event.preventDefault();
            focusedDay = format(Date.parse(value + 'T00:00:00Z') + offsets[event.key] * 86400000).slice(0,10);
            month = focusedDay.slice(0,7); calendar();
            panel.querySelector('[data-utc-day="' + focusedDay + '"]')?.focus();
          };
          cell.append(pick);
        }
        row.append(cell);
      }
      table.append(body);
      const actions = node('div',undefined,'utc-actions');
      actions.append(button('Today (UTC)',()=>choose('date',format(now()).slice(0,10))),button('Close',()=>close(true)));
      panel.append(heading,table,actions);
    }
    function clock() {
      panel.replaceChildren(); panel.setAttribute('aria-label','Choose UTC time');
      panel.append(node('strong','Time (UTC, 24-hour)'));
      const fields = node('div',undefined,'utc-clock'), values = complete().time.split(':');
      const selects = ['Hour','Minute','Second'].map((name,index) => {
        const label = node('label',name), select = node('select');
        select.setAttribute('aria-label',name + ' (UTC)');
        for (let i = 0; i < (index ? 60 : 24); ++i) { const option = node('option',pad(i)); option.value = pad(i); select.append(option); }
        select.value = values[index]; label.append(select); fields.append(label); return select;
      });
      const actions = node('div',undefined,'utc-actions');
      actions.append(button('Use time',()=>choose('time',selects.map(select=>select.value).join(':'))),
                     button('Now (UTC)',()=>choose('time',format(now()).slice(11))),button('Close',()=>close(true)));
      panel.append(fields,actions);
    }
    function open(part) {
      if (disabled()) return;
      if (!panel.hidden && active === part) { close(true); return; }
      dismissOpen?.();
      const value = complete(); active = part; month = value.date.slice(0,7); focusedDay = value.date;
      if (part === 'date') calendar(); else clock();
      panel.hidden = false; dismissOpen = close;
      if (container.getBoundingClientRect && doc.defaultView) {
        const bounds = container.getBoundingClientRect(), height = panel.getBoundingClientRect().height;
        panel.classList.toggle('utc-above',bounds.bottom + height > doc.defaultView.innerHeight && bounds.top >= height);
        panel.scrollIntoView({block:'nearest'});
      }
      (part === 'date' ? dateButton : timeButton).setAttribute('aria-expanded','true');
      (part === 'date' ? panel.querySelector('[data-utc-day="' + focusedDay + '"]') : panel.querySelector('select'))?.focus();
    }
    dateButton.onclick = () => open('date'); timeButton.onclick = () => open('time');
    input.addEventListener('input',validate);
    container.addEventListener('keydown',event=>{if (event.key === 'Escape' && !panel.hidden) { event.preventDefault(); close(true); }});
    doc.addEventListener('pointerdown',event=>{if (!container.contains(event.target)) close();});
    doc.defaultView?.addEventListener('resize',()=>close());
    validate();
    return {sync:validate,close};
  }
  const api = {parse,format,select,create};
  root.WsprryUtcDateTime = api;
  if (typeof module !== 'undefined') module.exports = api;
})(globalThis);

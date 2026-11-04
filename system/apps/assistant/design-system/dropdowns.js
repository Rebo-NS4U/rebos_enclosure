// Enhance native selects while keeping their values, forms, and change events.
(() => {
  let sequence = 0;
  document.querySelectorAll('.dweebo select:not([multiple]):not([size])').forEach(select => {
    if (select.dataset.enhanced) return;
    select.dataset.enhanced = 'true';
    const wrapper = document.createElement('div');
    wrapper.className = 'dw-select';
    select.before(wrapper);
    wrapper.append(select);
    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'dw-select-trigger';
    trigger.id = `dw-select-${++sequence}`;
    trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    const menu = document.createElement('div');
    menu.id = `${trigger.id}-list`;
    menu.className = 'dw-select-menu';
    menu.setAttribute('role', 'listbox');
    menu.hidden = true;
    trigger.setAttribute('aria-controls', menu.id);
    const labels = Array.from(select.labels || []);
    if (labels.length) {
      labels.forEach((label, i) => { label.id ||= `${trigger.id}-label-${i}`; label.htmlFor = trigger.id; });
      trigger.setAttribute('aria-labelledby', labels.map(l => l.id).join(' '));
      menu.setAttribute('aria-labelledby', labels.map(l => l.id).join(' '));
    } else trigger.setAttribute('aria-label', select.getAttribute('aria-label') || 'Choose an option');
    for (const attr of ['aria-describedby', 'aria-invalid', 'aria-required']) {
      if (select.hasAttribute(attr)) trigger.setAttribute(attr, select.getAttribute(attr));
    }
    wrapper.append(trigger, menu);
    select.hidden = true;
    let active = select.selectedIndex;
    let search = '', lastSearch = 0;
    const enabled = () => Array.from(select.options).map((o, i) => !o.disabled && !o.parentElement.disabled ? i : -1).filter(i => i >= 0);
    function highlight(index) {
      active = index;
      Array.from(menu.children).forEach((row, i) => row.classList.toggle('dw-active', i === active));
      const row = menu.children[active];
      if (row) {
        trigger.setAttribute('aria-activedescendant', row.id);
        row.scrollIntoView({block: 'nearest'});
      }
    }
    function close() {
      menu.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      trigger.removeAttribute('aria-activedescendant');
    }
    function sync() {
      trigger.textContent = select.selectedOptions[0]?.textContent || 'Choose an option';
      trigger.disabled = select.disabled;
      Array.from(menu.children).forEach((row, i) => row.setAttribute('aria-selected', String(i === select.selectedIndex)));
    }
    function choose(index) {
      const changed = select.selectedIndex !== index;
      select.selectedIndex = index;
      sync(); close(); trigger.focus();
      if (changed) {
        select.dispatchEvent(new Event('input', {bubbles: true}));
        select.dispatchEvent(new Event('change', {bubbles: true}));
      }
    }
    function open() {
      document.dispatchEvent(new CustomEvent('dw-select-open', {detail: trigger}));
      menu.hidden = false;
      trigger.setAttribute('aria-expanded', 'true');
      highlight(enabled().includes(select.selectedIndex) ? select.selectedIndex : enabled()[0]);
    }
    Array.from(select.options).forEach((option, i) => {
      const row = document.createElement('div');
      row.id = `${menu.id}-${i}`;
      row.setAttribute('role', 'option');
      row.textContent = option.textContent;
      row.setAttribute('aria-disabled', String(!enabled().includes(i)));
      row.addEventListener('pointerdown', e => e.preventDefault());
      row.addEventListener('click', () => { if (enabled().includes(i)) choose(i); });
      menu.append(row);
    });
    trigger.addEventListener('click', () => menu.hidden ? open() : close());
    trigger.addEventListener('keydown', event => {
      const keys = ['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' ', 'Escape'];
      if (event.key === 'Tab') { close(); return; }
      if (!keys.includes(event.key) && (event.key.length !== 1 || event.ctrlKey || event.metaKey || event.altKey)) return;
      event.preventDefault();
      if (event.key === 'Escape') { close(); return; }
      if (event.key === 'Enter' || event.key === ' ') {
        if (menu.hidden) open(); else if (enabled().includes(active)) choose(active);
        return;
      }
      const wasClosed = menu.hidden;
      if (wasClosed) open();
      const choices = enabled();
      if (event.key === 'Home') highlight(choices[0]);
      else if (event.key === 'End') highlight(choices.at(-1));
      else if (event.key.startsWith('Arrow')) {
        if (!wasClosed) highlight(choices[Math.max(0, Math.min(choices.length - 1, choices.indexOf(active) + (event.key === 'ArrowDown' ? 1 : -1)))]);
      } else {
        const now = Date.now();
        search = (now - lastSearch > 700 ? '' : search) + event.key.toLowerCase();
        lastSearch = now;
        const match = choices.find(i => select.options[i].text.toLowerCase().startsWith(search));
        if (match !== undefined) highlight(match);
      }
    });
    document.addEventListener('pointerdown', event => { if (!wrapper.contains(event.target)) close(); });
    document.addEventListener('dw-select-open', event => { if (event.detail !== trigger) close(); });
    wrapper.addEventListener('focusout', event => { if (!wrapper.contains(event.relatedTarget)) close(); });
    select.addEventListener('change', sync);
    select.form?.addEventListener('reset', () => setTimeout(sync, 0));
    select.addEventListener('invalid', event => { event.preventDefault(); trigger.setAttribute('aria-invalid', 'true'); trigger.focus(); });
    sync();
  });
})();

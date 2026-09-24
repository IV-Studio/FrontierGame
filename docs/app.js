(() => {
  const catalog = window.FRONTIER_CATALOG;
  if (!catalog) return;
  const local = location.protocol === 'file:';
  if (local) document.getElementById('local-notice').hidden = false;
  const urlFor = asset => new URL(asset.path, document.baseURI).href;
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  let toastTimer;
  const toast = message => {
    const node = document.getElementById('toast');
    node.textContent = message;
    node.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.remove('show'), 2200);
  };
  async function copy(input) {
    input.focus();
    input.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch {}
    if (!copied) {
      try { await navigator.clipboard.writeText(input.value); copied = true; } catch {}
    }
    toast(copied ? 'URL selected. If paste is empty, press Ctrl+C.' : 'URL selected. Press Ctrl+C to copy.');
  }
  function urlRow(label, asset) {
    const row = el('div', 'url-row');
    const id = `url-${Math.random().toString(36).slice(2)}`;
    const labelNode = el('label', '', label);
    labelNode.htmlFor = id;
    const controls = el('div', 'url-controls');
    const input = el('input');
    input.id = id;
    input.type = 'text';
    input.readOnly = true;
    input.value = local ? 'Available after publishing' : urlFor(asset);
    input.addEventListener('focus', () => input.select());
    const button = el('button', 'copy-btn', 'Copy');
    button.type = 'button';
    button.disabled = local;
    button.setAttribute('aria-label', `Copy ${label.toLowerCase()} URL`);
    button.addEventListener('click', () => copy(input));
    controls.append(input, button);
    row.append(labelNode, controls);
    return row;
  }
  function image(asset, title) {
    const img = el('img');
    img.src = asset.path;
    img.alt = title;
    img.loading = 'lazy';
    img.decoding = 'async';
    return img;
  }
  function renderDeck(deck) {
    const article = el('article', 'deck-card');
    const art = el('div', 'deck-art');
    art.append(image(deck.face, `${deck.title} card sheet`));
    const info = el('div', 'deck-info');
    const titleRow = el('div', 'deck-title-row');
    titleRow.append(el('h3', '', deck.title), el('span', 'pill', `${deck.count} cards`));
    const meta = el('div', 'deck-meta');
    for (const [label, value] of [['Width', deck.columns], ['Height', deck.rows], ['Number', deck.count]]) {
      const chip = el('span', 'meta-chip', label);
      chip.append(el('strong', '', String(value)));
      meta.append(chip);
    }
    info.append(titleRow, meta, urlRow('Face sheet URL', deck.face), urlRow('Shared back URL', deck.back),
      el('p', 'meta-note', `Sheet: ${deck.face.width} × ${deck.face.height} px · Cards touch edge to edge · Back is Hidden: On`));
    article.append(art, info);
    return article;
  }
  function renderSingle(asset) {
    const article = el('article', 'asset-card');
    const art = el('div', 'asset-art');
    art.append(image(asset, asset.title));
    const info = el('div', 'asset-info');
    info.append(el('h3', '', asset.title), el('p', 'dimensions', `${asset.width} × ${asset.height} px`), urlRow('Image URL', asset));
    article.append(art, info);
    return article;
  }
  for (const deck of catalog.decks) document.getElementById('deck-list').append(renderDeck(deck));
  for (const [key, target] of [['boards', 'board-list'], ['cards', 'card-list'], ['tokens', 'token-list']]) {
    for (const asset of catalog[key]) document.getElementById(target).append(renderSingle(asset));
  }
  const summary = document.getElementById('summary');
  for (const [value, label] of [[catalog.decks.length, 'Decks'], [catalog.boards.length, 'Boards'],
                                 [catalog.cards.length, 'Single cards'], [catalog.tokens.length, 'Tokens']]) {
    const item = el('div', 'summary-item');
    item.append(el('strong', '', String(value)), el('span', '', label));
    summary.append(item);
  }
})();

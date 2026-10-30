/* Client-side archive. Design: ../.mkdocs/REFACTOR.md */
(() => {
  const script = document.currentScript;
  const siteRoot = new URL('../', script.src);
  let indexPromise;
  let dispose = () => {};
  const loadIndex = () => indexPromise ||= fetch(new URL('assets/notes-index.json', siteRoot))
    .then(response => { if (!response.ok) throw new Error('index unavailable'); return response.json(); })
    .catch(error => { indexPromise = null; throw error; });

  function init() {
    dispose();
    const container = document.getElementById('notes-catalog');
    if (!container) return;
    const controller = new AbortController();
    let active = true;
    dispose = () => { active = false; controller.abort(); };
    const options = { signal: controller.signal };
    const query = container.querySelector('#notes-query');
    const filters = container.querySelector('#notes-filters');
    const sort = container.querySelector('#notes-sort');
    const status = container.querySelector('#notes-status');
    const results = container.querySelector('#notes-results');
    const pagination = container.querySelector('#notes-pagination');
    let rows = [], category = '', page = 1;
    const pageSize = 10;

    function readLocation() {
      const params = new URL(location.href).searchParams;
      query.value = params.get('query') || '';
      category = params.get('category') || '';
      const requestedSort = params.get('sort');
      sort.value = requestedSort === 'relevance' ? 'relevance' : 'title';
      page = Math.max(1, Number.parseInt(params.get('page'), 10) || 1);
    }
    function writeLocation() {
      const url = new URL(location.href);
      for (const key of ['query', 'category', 'sort', 'page']) url.searchParams.delete(key);
      if (query.value.trim()) url.searchParams.set('query', query.value.trim());
      if (category) url.searchParams.set('category', category);
      if (sort.value !== 'title') url.searchParams.set('sort', sort.value);
      if (page > 1) url.searchParams.set('page', page);
      if (url.href !== location.href) history.pushState({}, '', url);
    }
    function highlight(element, text, tokens) {
      if (!tokens.length) { element.textContent = text; return; }
      const pattern = tokens.map(token => token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
      const expression = new RegExp(pattern, 'giu');
      let cursor = 0;
      for (const match of text.matchAll(expression)) {
        element.append(document.createTextNode(text.slice(cursor, match.index)));
        const mark = document.createElement('mark');
        mark.textContent = match[0];
        element.append(mark);
        cursor = match.index + match[0].length;
      }
      element.append(document.createTextNode(text.slice(cursor)));
    }
    function render(updateUrl = false) {
      const tokens = [...new Set(query.value.trim().toLowerCase().split(/\s+/u).filter(Boolean))];
      const matches = rows.filter(row => (!category || row.category === category) &&
        tokens.every(token => (row.title + ' ' + row.text).toLowerCase().includes(token)));
      const score = row => tokens.reduce((total, token) => total + (row.title.toLowerCase().includes(token) ? 10 : 1), 0);
      matches.sort((a, b) => (sort.value === 'relevance' ? score(b) - score(a) : 0) || a.title.localeCompare(b.title, 'zh-CN'));
      const totalPages = Math.max(1, Math.ceil(matches.length / pageSize));
      page = Math.min(page, totalPages);
      if (updateUrl) writeLocation();
      for (const button of filters.children) button.setAttribute('aria-pressed', String(button.dataset.category === category));
      status.textContent = `找到 ${matches.length} 篇笔记 · 搜索标题与正文`;
      results.replaceChildren();
      for (const row of matches.slice((page - 1) * pageSize, page * pageSize)) {
        const card = document.createElement('article'); card.className = 'note-card';
        const label = document.createElement('span'); label.className = 'eyebrow'; label.textContent = row.category;
        const heading = document.createElement('h2');
        const link = document.createElement('a'); link.href = new URL(row.url, siteRoot).href;
        highlight(link, row.title, tokens); heading.append(link);
        const summary = document.createElement('p');
        let excerpt = row.summary;
        const firstMatch = tokens.length ? row.text.toLowerCase().indexOf(tokens[0]) : -1;
        if (firstMatch >= 0) {
          const start = Math.max(0, firstMatch - 45);
          excerpt = (start ? '…' : '') + row.text.slice(start, start + 200) + (start + 200 < row.text.length ? '…' : '');
        }
        highlight(summary, excerpt, tokens); card.append(label, heading, summary); results.append(card);
      }
      if (!matches.length) {
        const empty = document.createElement('p'); empty.textContent = '没有找到匹配的笔记。试试更短的关键词，或清除筛选。';
        const reset = document.createElement('button'); reset.type = 'button'; reset.className = 'md-button'; reset.textContent = '清除筛选';
        reset.addEventListener('click', () => { query.value = ''; category = ''; page = 1; render(true); query.focus(); }, options);
        results.append(empty, reset);
      }
      pagination.replaceChildren();
      if (matches.length > pageSize) {
        const previous = document.createElement('button'); previous.type = 'button'; previous.textContent = '上一页'; previous.disabled = page === 1;
        const next = document.createElement('button'); next.type = 'button'; next.textContent = '下一页'; next.disabled = page === totalPages;
        const counter = document.createElement('span'); counter.textContent = `${page} / ${totalPages}`;
        for (const [button, delta] of [[previous, -1], [next, 1]]) button.addEventListener('click', () => {
          page += delta; render(true); container.scrollIntoView({ block: 'start' });
          container.querySelector('#notes-status').focus({ preventScroll: true });
        }, options);
        pagination.append(previous, counter, next);
      }
    }
    readLocation();
    loadIndex().then(data => {
      if (!active) return;
      rows = data;
      const names = [...new Set(rows.map(row => row.category))];
      const order = ['Java', 'LLM', '中间件', '数据库', '408', '软考', 'Ideas'];
      const categories = ['', ...order.filter(name => names.includes(name)), ...names.filter(name => !order.includes(name))];
      if (!categories.includes(category)) category = '';
      for (const name of categories) {
        const button = document.createElement('button'); button.type = 'button'; button.dataset.category = name;
        button.textContent = name || '全部';
        button.addEventListener('click', () => { category = name; page = 1; render(true); }, options);
        filters.append(button);
      }
      render();
    }).catch(() => { if (active) status.textContent = '索引暂时无法加载，请刷新页面重试，或使用下方目录阅读。'; });
    container.querySelector('form').addEventListener('submit', event => {
      event.preventDefault(); page = 1; sort.value = query.value.trim() ? 'relevance' : 'title'; render(true);
    }, options);
    sort.addEventListener('change', () => { page = 1; render(true); }, options);
    window.addEventListener('popstate', () => { readLocation(); render(); }, options);
  }
  if (typeof document$ !== 'undefined') document$.subscribe(init);
  else if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

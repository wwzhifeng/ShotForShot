/* 王知风 H3 导演台 · 爆款复刻版 —— 前端（原生 JS，无构建，无外网）
   字段以《接口约定 v1》为准。界面只显示接口给的 title + action，不显示英文原文。 */
(() => {
'use strict';

/* ============ 小工具 ============ */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const yuan = v => '¥' + Number(v || 0).toFixed(2);
const price = v => Number(v || 0).toFixed(2);
const tc = t => { t = Math.max(0, +t || 0); const m = Math.floor(t / 60), s = t - m * 60; return String(m).padStart(2, '0') + ':' + s.toFixed(1).padStart(4, '0'); };
const clock = t => { t = Math.max(0, Math.round(+t || 0)); return String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0'); };
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const bg = url => url ? `background-image:url('${String(url).replace(/'/g, '%27')}')` : '';
const uid = () => (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2));
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch { /* 存不了就算了 */ } } };

/* 图标：线性，1.75 描边，按 Lucide（ISC）的画法自绘路径 */
const ICO = {
  upload: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12',
  check: 'M20 6 9 17l-5-5', chev: 'm6 9 6 6 6-6', x: 'M18 6 6 18M6 6l12 12',
  copy: 'M9 9h11v11H9zM5 15H4V4h11v1',
  sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6',
  play: 'M7 4l13 8-13 8V4z', pause: 'M6 4h4v16H6zM14 4h4v16h-4z',
  alert: 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01',
  shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
  image: 'M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM21 15l-5-5L5 21',
  download: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  folder: 'M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z',
  info: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 16v-4M12 8h.01',
  arrow: 'M5 12h14M12 5l7 7-7 7', type: 'M4 7V4h16v3M9 20h6M12 4v16',
  zap: 'M13 2 3 14h9l-1 8 10-12h-9l1-8z', pencil: 'M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2', plus: 'M12 5v14M5 12h14',
  film: 'M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4M3 12h18',
  refresh: 'M23 4v6h-6M1 20v-6h6M3.5 9a9 9 0 0 1 14.9-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15',
  vol: 'M11 5 6 9H2v6h4l5 4V5zM15.5 8.5a5 5 0 0 1 0 7M18.8 5.2a9.5 9.5 0 0 1 0 13.6',
  mute: 'M11 5 6 9H2v6h4l5 4V5zM22 9l-6 6M16 9l6 6',
  undo: 'M3 7v6h6M3.5 13a9 9 0 1 0 2.6-6.4L3 9.5'
};
const ico = (n, c = '') => `<svg class="ico ${c}" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICO[n]}"/></svg>`;
const hydrateIcons = (root = document) => $$('i[data-ico]', root).forEach(i => { const t = document.createElement('template'); t.innerHTML = ico(i.dataset.ico, i.className); i.replaceWith(t.content.firstChild); });

/* 示例卡上的画面：自己画的《雨夜摊牌》第一镜，不引用任何图片文件 */
const SAMPLE_ART = "url('data:image/svg+xml," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="360" height="640" viewBox="0 0 180 320"><defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a1422"/><stop offset=".62" stop-color="#18293b"/><stop offset="1" stop-color="#06090e"/></linearGradient><radialGradient id="gW"><stop offset="0" stop-color="#ffe6ba" stop-opacity=".95"/><stop offset=".35" stop-color="#ffbd6b" stop-opacity=".45"/><stop offset="1" stop-color="#ffb45a" stop-opacity="0"/></radialGradient><radialGradient id="gM"><stop offset="0" stop-color="#ff86a6" stop-opacity=".8"/><stop offset="1" stop-color="#ff3d6e" stop-opacity="0"/></radialGradient><radialGradient id="vig" cx=".5" cy=".45" r=".78"><stop offset=".5" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".72"/></radialGradient><filter id="b1"><feGaussianBlur stdDeviation="1.2"/></filter><filter id="b3"><feGaussianBlur stdDeviation="3"/></filter><pattern id="rain" width="16" height="44" patternUnits="userSpaceOnUse" patternTransform="rotate(11)"><line x1="3" y1="0" x2="3" y2="14" stroke="#d6e8f8" stroke-width=".55" opacity=".34"/><line x1="11" y1="22" x2="11" y2="33" stroke="#d6e8f8" stroke-width=".4" opacity=".24"/></pattern></defs><rect width="180" height="320" fill="url(#sky)"/><rect x="0" y="34" width="50" height="206" fill="#080d15"/><rect x="130" y="8" width="50" height="232" fill="#070b12"/><rect x="50" y="96" width="38" height="144" fill="#0a111b"/><g fill="#ffcf87" opacity=".55"><rect x="8" y="60" width="6" height="9"/><rect x="26" y="96" width="6" height="9"/><rect x="140" y="40" width="6" height="9"/><rect x="158" y="84" width="6" height="9"/><rect x="140" y="128" width="6" height="9"/><rect x="60" y="120" width="5" height="8"/></g><rect x="2" y="150" width="34" height="9" fill="#ff5f8a" opacity=".8" filter="url(#b1)"/><circle cx="19" cy="154" r="26" fill="url(#gM)" opacity=".55"/><rect x="117" y="72" width="2.4" height="166" fill="#05080c"/><circle cx="118" cy="72" r="44" fill="url(#gW)"/><rect x="0" y="236" width="180" height="84" fill="#060a10"/><g filter="url(#b3)" opacity=".55"><rect x="110" y="238" width="16" height="78" fill="#ffc777" opacity=".35"/><rect x="6" y="238" width="26" height="60" fill="#ff5f8a" opacity=".28"/><rect x="128" y="246" width="40" height="40" fill="#fff0cf" opacity=".22"/></g><rect x="132" y="196" width="60" height="24" rx="9" fill="#0b1017"/><rect x="118" y="212" width="80" height="30" rx="10" fill="#0a0e14"/><circle cx="124" cy="226" r="20" fill="url(#gW)" opacity=".9"/><ellipse cx="124" cy="226" rx="4" ry="3" fill="#fff6dc"/><g transform="translate(74 172)"><path d="M-24 2Q0 -24 24 2Q0 -6 -24 2Z" fill="#0b0f15"/><rect x="-.6" y="0" width="1.2" height="26" fill="#0b0f15"/><circle cx="0" cy="12" r="5" fill="#b89482"/><path d="M-5.5 12Q-6 5 0 5Q6 5 5.5 12L6.5 30L3.5 30L4 13Q0 8 -4 13L-3.5 30L-6.5 30Z" fill="#0a0708"/><rect x="-7.5" y="18" width="15" height="34" rx="5" fill="#1d3350"/><rect x="2" y="19" width="5" height="32" rx="2.5" fill="#38557a" opacity=".7"/><rect x="-4" y="50" width="8" height="16" fill="#080b10"/></g><rect width="180" height="320" fill="url(#rain)"/><rect width="180" height="320" fill="url(#vig)"/></svg>`).replace(/'/g, '%27') + "')";

/* ============ 状态 ============ */
const S = {
  st: null,            // GET /api/state
  list: [],            // 作品列表
  p: null,             // 当前作品
  q: { full: null, trial: null, sig: '', loading: false, err: null },
  ui: fresh(),
  memo: {},
  phase: null
};
function fresh() {
  return { tier: null, takes: null, trial: false, adv: false, peek: new Set(), reshoot: false, lines: {}, dirtyLines: new Set(), busy: {}, sel: null, ear: null, trim: null, promptDirty: false, keyEdit: false, keyTest: null, nonce: null, nonceFor: '' };
}

/* ============ 接口 ============ */
const OFFLINE = { title: '连不上本机程序', action: '看一下那个黑色的启动窗口是不是关了。重新双击「启动」，再刷新这个网页。', retryable: true };
async function api(method, path, body) {
  const opt = { method, credentials: 'same-origin', headers: {} };
  if (body instanceof FormData) opt.body = body;
  else if (body !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
  let res;
  try { res = await fetch(path, opt); } catch { throw { ...OFFLINE }; }
  let data = null;
  try { data = await res.json(); } catch { /* 不是 JSON */ }
  if (!res.ok) {
    const e = data && data.error;
    throw { title: (e && e.title) || '这一步没做成', action: (e && e.action) || '再试一次。还不行的话，把「日志」文件夹发给作者。', retryable: !!(e && e.retryable), code: e && e.code };
  }
  return data;
}
const isProject = d => d && typeof d === 'object' && d.id && d.stage;
/* 改动类接口：返回了作品结构就直接用，没返回就重新取一次 */
async function mutate(method, path, body) {
  const id = S.p && S.p.id;
  const d = await api(method, path, body);
  if (isProject(d)) setProject(d);
  else if (id && S.p && S.p.id === id) setProject(await api('GET', `/api/projects/${id}`));
  return d;
}

/* ============ 提示、报错、确认 ============ */
let toastT;
function toast(m) { const t = $('#toast'); t.textContent = m; t.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('on'), 2600); }
function showError(e) {
  const box = $('#errs');
  const title = (e && e.title) || '这一步没做成', action = (e && e.action) || '再试一次。';
  if ($$('.alert', box).some(a => a.dataset.t === title)) return;
  while (box.children.length >= 2) box.firstChild.remove();
  const d = document.createElement('div');
  d.className = 'alert'; d.setAttribute('role', 'alert'); d.dataset.t = title;
  d.innerHTML = `${ico('alert')}<div><h3>${esc(title)}</h3><p>${esc(action)}</p></div><button aria-label="关掉这条提示">${ico('x')}</button>`;
  d.querySelector('button').onclick = () => d.remove();
  box.appendChild(d);
}
function ask({ title, text, rows, yes, no = '再想想' }) {
  const d = $('#ask');
  d.innerHTML = `<form method="dialog" class="ask-in"><h2>${esc(title)}</h2>${text ? `<p>${esc(text)}</p>` : ''}${rows ? `<dl>${rows.map(r => `<dt>${esc(r[0])}</dt><dd class="${r[2] || ''}">${esc(r[1])}</dd>`).join('')}</dl>` : ''}<div class="ask-act"><button class="btn ghost" value="no">${esc(no)}</button><button class="btn primary" value="yes">${esc(yes)}</button></div></form>`;
  return new Promise(res => { d.onclose = () => res(d.returnValue === 'yes'); d.returnValue = 'no'; d.showModal(); d.querySelector('[value=no]').focus(); });
}

/* ============ 阶段 ============ */
const ACTIVE_ST = ['queued', 'running', 'downloading'];
const TAKE_CN = { queued: '排队中', running: '拍摄中', downloading: '下载中', succeeded: '拍好了', failed: '没拍成', cancelled: '已取消' };
const STAGE_CN = { upload: '处理中', select: '等你选一段', analyzing: 'AI 拉片中', cast: '等人物照片', ready: '可以开拍', shooting: '拍摄中', pick: '等你挑片', exported: '已导出' };
const okTakes = p => ((p && p.takes) || []).filter(t => t.status === 'succeeded' && t.file);
/* 主角：A 放了照片就是 A；只给别人放了照片就是他（和后端 service.main_of 一致）；都没放时提示放 A（拉片把站最前、脸最大的人编成 A） */
const mainPerson = p => { const pp = (p.analysis && p.analysis.people) || [], c = p.cast || {}; const has = x => c[x.id] && c[x.id].photo; return (pp.find(x => x.id === 'A' && has(x)) || pp.find(has) || pp.find(x => x.id === 'A') || pp[0] || { id: 'A' }).id; };
const hasCast = (p, id) => !!(p.cast && p.cast[id] && p.cast[id].photo);
function phase() {
  const p = S.p; if (!p) return 'empty';
  if (p.stage === 'select') return 'select';
  if (!p.analysis) {
    const j = p.jobs && p.jobs.analyze;
    if (j && j.status === 'error') return 'anaerr';
    if ((j && j.status === 'running') || p.stage === 'analyzing') return 'analyzing';
    if (p.stage === 'upload' || !p.window) return 'proc';
    return 'anaidle';
  }
  const takes = p.takes || [];
  if (takes.some(t => ACTIVE_ST.includes(t.status))) return 'shooting';
  if (S.ui.reshoot || !takes.length) return hasCast(p, mainPerson(p)) ? 'ready' : 'cast';
  if (!okTakes(p).length) return 'failed';
  return 'pick';
}
const ACTIVE_STEP = { empty: 1, select: 1, proc: 1, analyzing: 2, anaerr: 2, anaidle: 2, cast: 3, ready: 4, shooting: 5, failed: 5, pick: 6 };
const NAMES = ['传原片', 'AI 拉片表', '换成你的', '看价钱，开拍', '拍摄中', '对着原片挑'];
const LOCK = ['', 'AI 看片，列出每个镜头怎么拍的', '换上你的人，台词想改就改', '先看价钱，点了确认才提交', '默认拍 1 条，不满意再拍一条', '和原片对着看，挑一条导出'];
function stepStates(ph) {
  const p = S.p, takes = (p && p.takes) || [], t5 = takes.length ? 'd' : 'l', t6 = okTakes(p).length ? 'd' : 'l';
  switch (ph) {
    case 'empty': case 'select': case 'proc': return 'olllll';
    case 'analyzing': case 'anaerr': case 'anaidle': return 'dollll';
    case 'cast': return 'dool' + t5 + t6;
    case 'ready': return 'ddoo' + t5 + t6;
    case 'shooting': case 'failed': return 'ddddo' + t6;
    default: return 'dddddo';
  }
}
const memo = (k, key) => { if (S.memo[k] === key) return false; S.memo[k] = key; return true; };
const focusIn = sel => { const a = document.activeElement; return !!(a && a.closest && a.closest(sel) && /INPUT|TEXTAREA|SELECT/.test(a.tagName)); };

/* ============ 载入、轮询 ============ */
let pollT = 0, pollFail = 0;
function setProject(p) {
  const prev = S.p;
  if (!prev || !p || prev.id !== p.id) {
    player.stop();
    S.ui = Object.assign(fresh(), { tier: S.st && S.st.settings.tier, takes: S.st && S.st.settings.takes });
    S.memo = {}; S.q = { full: null, trial: null, sig: '', loading: false, err: null };
    if (p) store.set('h3dt.last', p.id);
  }
  const wasShooting = prev && p && prev.id === p.id && (prev.takes || []).some(t => ACTIVE_ST.includes(t.status));
  S.p = p;
  if (wasShooting && p && !(p.takes || []).some(t => ACTIVE_ST.includes(t.status))) {
    loadState();
    const n = okTakes(p).length;
    if (n) toast(n > 1 ? `拍好了，${n} 条都在下面，挑一条吧` : '拍好了，和原片对着看看');
  }
  render();
  schedulePoll();
}
function schedulePoll() {
  clearTimeout(pollT);
  if (!S.p || !['proc', 'analyzing', 'shooting'].includes(phase())) return;
  pollT = setTimeout(async () => {
    const id = S.p && S.p.id; if (!id) return;
    try {
      const p = await api('GET', `/api/projects/${id}`);
      pollFail = 0;
      if (S.p && S.p.id === id) return setProject(p);
    } catch (e) { if (++pollFail === 3) showError(e); }
    schedulePoll();
  }, pollFail >= 3 ? 5000 : 1500);
}
async function loadState() { try { S.st = await api('GET', '/api/state'); renderBar(); renderDrawer(); if (S.p) render(); } catch (e) { showError(e); } }
async function loadList() { try { S.list = (await api('GET', '/api/projects')) || []; } catch { /* 列表拿不到不挡事 */ } }
async function openProject(id) { try { setProject(await api('GET', `/api/projects/${id}`)); } catch (e) { showError(e); } }
function newProject() { clearTimeout(pollT); setProject(null); window.scrollTo({ top: 0, behavior: 'smooth' }); }

/* ============ 渲染：总入口 ============ */
function render() {
  const ph = phase();
  const changed = ph !== S.phase;
  if (changed) { S.ui.peek.clear(); if (ph !== 'pick') player.pause(); }
  renderBar();
  renderSteps(ph);
  s1(ph); s2(ph); s3(ph); s4(ph); s5(ph); s6(ph);
  renderDock(ph, changed);
  if (ph === 'cast' || ph === 'ready') ensureQuote();
  if (changed) {
    const first = S.phase === null; S.phase = ph;
    if (!first) {
      const n = ph === 'cast' ? 2 : ph === 'ready' ? (S.ui.reshoot ? 3 : 4) : ACTIVE_STEP[ph];
      if (n === 1) window.scrollTo({ top: 0, behavior: 'smooth' });
      else setTimeout(() => { if (S.phase === ph) $('#s' + n).scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 420);
    }
  }
}

// 示例作品永远走模拟（后端 is_mock 同理），填了密钥也不能显示成「真拍」
const isMock = () => !!(S.st && S.st.mock) || !!(S.p && S.p.sample);

function renderBar() {
  const p = S.p, st = S.st;
  $('#projName').textContent = p ? (p.name || '新作品') : '还没有作品';
  const pill = $('#simPill');
  if (st) { const m = isMock(); pill.hidden = false; pill.classList.toggle('real', !m); pill.textContent = m ? '模拟，不扣费' : '真拍，按量扣费'; }
  const sp = $('#spend');
  const key = JSON.stringify([p && p.spent, p && p.budget, st && st.spent_total, st && st.settings.budget, !!p]);
  if (memo('spend', key)) sp.innerHTML = p ? `<span>这个作品已花 </span><b>${yuan(p.spent)}</b><span> / 预算 ¥${+(p.budget ?? (st ? st.settings.budget : 0))}</span>` : st ? `<span>累计已花 </span><b>${yuan(st.spent_total)}</b>` : '';
}

function renderSteps(ph) {
  const m = stepStates(ph), p = S.p;
  $$('.step').forEach((s, i) => {
    const state = { o: 'open', d: 'done', l: 'locked' }[m[i]];
    s.dataset.s = state;
    s.classList.toggle('peek', state === 'done' && S.ui.peek.has(i + 1));
    const h = s.querySelector('.step-head');
    h.tabIndex = state === 'done' ? 0 : -1;
    h.setAttribute('aria-expanded', state === 'open' || s.classList.contains('peek'));
    s.querySelector('.step-edit').firstChild.textContent = s.classList.contains('peek') ? '收起' : '展开';
    const sum = s.querySelector('.step-sum');
    const html = state === 'locked' ? LOCK[i] : state === 'done' ? stepSum(i + 1, p) : '';
    if (memo('sum' + i, html)) sum.innerHTML = html;
  });
  $('#s5 .step-title').textContent = ph === 'shooting' ? '拍摄中' : '拍摄';
}
function stepSum(n, p) {
  if (!p) return '';
  const a = p.analysis, src = p.source || {};
  if (n === 1) return `<span class="grow">${esc(p.name)}</span><span class="hint num">${(p.window ? p.window.dur : src.duration || 0).toFixed(1)} 秒 · ${src.width || '?'}×${src.height || '?'}</span>`;
  if (n === 2 && a) {
    const hard = a.shots.filter(s => s.hard && s.hard.length).length;
    return `<span class="ministrip">${a.shots.map(s => `<i style="flex:${Math.max(.2, s.end - s.start)};${bg(s.thumb)}"></i>`).join('')}</span><span>${a.shots.length} 个镜头，${a.lines.length} 句台词</span>${hard ? `<span class="hint">${hard} 个高难镜头</span>` : ''}`;
  }
  if (n === 3 && a) {
    const changed = a.lines.filter(l => l.new != null && l.new !== l.text).length, id = mainPerson(p);
    return `<span>${hasCast(p, id) ? `人物 ${esc(id)} 已换成你的照片` : `人物 ${esc(id)} 还没选照片`}</span><span class="hint">${changed ? `改了 ${changed} 句台词` : '台词照搬原片'}</span>`;
  }
  if (n === 4) {
    const t = (p.takes || []).slice(-1)[0], tier = t && S.st && S.st.tiers.find(x => x.id === t.tier);
    return t ? `<span>${modeName(curMode(p))}${tier ? '，' + esc(tier.name) + '档' : ''}，一共拍过 ${p.takes.length} 条</span><span class="hint">这个作品已花 <span class="num">${yuan(p.spent)}</span></span>` : '';
  }
  if (n === 5) {
    const ok = okTakes(p).length, bad = (p.takes || []).filter(t => t.status === 'failed').length;
    return `<span>${ok ? `拍好 ${ok} 条` : '还没有拍好的'}${bad ? `，${bad} 条没拍成` : ''}</span>`;
  }
  if (n === 6) return `<span>${okTakes(p).length} 条可以挑</span>${p.exports && p.exports.length ? '<span class="hint">已导出过</span>' : ''}`;
  return '';
}

/* ============ 1 传原片 ============ */
function arStyle(p) { const s = (p && p.source) || {}; const w = s.width || 9, h = s.height || 16; return `--ar:${w}/${h};--arn:${(w / h).toFixed(4)}`; }
const isWide = p => { const s = (p && p.source) || {}; return (s.width || 9) > (s.height || 16); };
function s1(ph) {
  const box = $('#s1in'), p = S.p, st = S.st;
  if (ph === 'empty') {
    if (!memo('s1', 'empty|' + !!S.ui.busy.upload + '|' + !!S.ui.busy.sample + '|' + (st && st.settings.auto_analyze) + '|' + (st && st.mock))) return;
    const up = S.ui.busy.upload;
    box.innerHTML = `<div class="up">
      <div class="drop" id="drop" role="button" tabindex="0" data-act="pickVideo" aria-label="选择原片">
        ${up ? '<span class="spin"></span><strong>正在把片子交给本机程序</strong><span class="hint">片子只存在你电脑上，不会传到别处。</span>'
        : `${ico('upload')}<strong>把原片拖到这里，或者点一下选文件</strong><span class="hint">MP4 或 MOV，15 秒以内最好。更长的也能传，传完选其中一段。</span>`}
      </div>
      <div class="demo">
        <div class="frame"><div class="pic" style="background-image:${SAMPLE_ART}"></div><span class="tag cool">示例</span></div>
        <div>
          <h3>第一次用，先拿示例走一遍</h3>
          <p>一条 15 秒的示例片，从拉片到挑片全程模拟，不花一分钱。</p>
          <button class="btn${S.ui.busy.sample ? ' busy' : ''}" data-act="sample">${S.ui.busy.sample ? '<span class="spin"></span>' : ''}用示例走一遍</button>
        </div>
      </div>
      <div class="up-foot">
        <label class="check"><input type="checkbox" data-in="autoAnalyze"${!st || st.settings.auto_analyze ? ' checked' : ''}>传完自动让 AI 看片写拉片表（最多 ¥0.05${st && st.mock ? '，模拟模式不扣' : ''}）</label>
        <span class="hint">${ico('shield')} 只传你有权使用的视频。这里学的是结构和运镜，不是搬运。</span>
      </div></div>`;
    return;
  }
  if (!p) return;
  const src = p.source || {};
  if (ph === 'select') {
    if (!memo('s1', 'select|' + p.id + '|' + !!S.ui.busy.window)) return;
    const D = src.duration || 0, W = Math.min(15, Math.floor(D));
    if (!S.ui.trim) S.ui.trim = { start: clamp((p.window && p.window.start) || 0, 0, Math.max(0, D - W)), dur: W };
    box.innerHTML = `<div class="trim${isWide(p) ? ' wide' : ''}" style="${arStyle(p)}">
      <div class="frame"><video id="trimV" playsinline preload="auto" src="${esc(src.file)}"></video><span class="tag cool">原片</span></div>
      <div class="trim-r">
        <p>这条片子有 <b class="num">${D.toFixed(1)}</b> 秒，一次最多复刻 ${W} 秒。拖动下面的框，选你要的那一段。左边会跟着放你选中的部分。</p>
        <div class="trim-track" id="trimTrack"><canvas id="trimC"></canvas><div class="trim-win" id="trimWin"><canvas id="trimC2"></canvas></div></div>
        <div class="trim-scale"><span>00:00.0</span><span>${tc(D)}</span></div>
        <input type="range" id="trimRange" min="0" max="${Math.max(0, D - W).toFixed(1)}" step="0.1" value="${S.ui.trim.start}" aria-label="选段起点（秒）">
        <p class="trim-read">已选 <b class="num" id="trimRead"></b> <button class="btn sm" data-act="trimPlay" id="trimPlay" style="margin-left:.75rem">${ico('play', 'fill')}放这一段听听</button></p>
        <p class="hint" style="margin-top:.5rem">尽量从一个镜头的开头选起，别把一句台词切成两半。选好后在你电脑上裁剪，不花钱。</p>
      </div></div>`;
    trimInit(D, W);
    return;
  }
  const win = p.window;
  if (!memo('s1', 'info|' + p.id + '|' + ph + '|' + JSON.stringify(win))) return;
  const file = (win && win.file) || src.file;
  box.innerHTML = `<div class="proc${isWide(p) ? ' wide' : ''}" style="${arStyle(p)}">
    <div class="frame"><video muted playsinline preload="metadata" ${ph === 'proc' ? '' : 'controls'} src="${esc(file)}#t=0.1"></video><span class="tag cool">原片</span></div>
    <div>
      <h3>${esc(p.name)} <span class="hint num">${(src.duration || 0).toFixed(1)} 秒 · ${src.width || '?'}×${src.height || '?'}${src.fps ? ' · ' + Math.round(src.fps) + ' 帧' : ''}</span></h3>
      ${ph === 'proc' ? `<div class="now"><span class="spin"></span>正在本机读片、裁剪</div><div class="bar-track run"><i></i></div><p class="hint" style="margin-top:.6rem">这一步在你电脑上做，不联网，不花钱。</p>`
      : `<p class="hint" style="margin-top:.4rem">${win && src.duration > win.dur + .3 ? `用的是其中 <span class="num">${tc(win.start)} – ${tc(win.start + win.dur)}</span> 这一段，共 ${win.dur} 秒。` : '整条都用上了。'}${src.has_audio === false ? '这条片子没有声音。' : ''}</p>
         <p class="hint">想换一条原片，点左上角作品名，选「复刻新的一条」。</p>`}
    </div></div>`;
}

/* 选段条 */
function trimInit(D, W) {
  const v = $('#trimV'), track = $('#trimTrack'), win = $('#trimWin'), range = $('#trimRange'), c1 = $('#trimC'), c2 = $('#trimC2');
  const T = S.ui.trim;
  const paint = seek => {
    const tw = track.clientWidth, left = D ? T.start / D * tw : 0;
    win.style.left = left + 'px'; win.style.width = (D ? W / D * tw : tw) + 'px';
    c2.style.left = (-left - 2) + 'px'; c2.style.width = tw + 'px';
    $('#trimRead').textContent = tc(T.start) + ' – ' + tc(T.start + W);
    range.value = T.start;
    if (seek && v.readyState) { try { v.currentTime = T.start; } catch { /* 还没准备好 */ } }
  };
  const set = (s, seek = true) => { T.start = Math.round(clamp(s, 0, Math.max(0, D - W)) * 10) / 10; paint(seek); };
  range.oninput = () => set(+range.value);
  let drag = null;
  track.onpointerdown = e => {
    const r = track.getBoundingClientRect(), x = e.clientX - r.left, wl = T.start / D * r.width, ww = W / D * r.width;
    drag = { off: (x >= wl && x <= wl + ww) ? x - wl : ww / 2, w: r.width, l: r.left };
    track.setPointerCapture(e.pointerId); set((x - drag.off) / drag.w * D);
  };
  track.onpointermove = e => { if (drag) set((e.clientX - drag.l - drag.off) / drag.w * D); };
  track.onpointerup = track.onpointercancel = () => { drag = null; };
  v.addEventListener('loadedmetadata', () => paint(true), { once: true });
  v.ontimeupdate = () => { if (v.currentTime >= T.start + W - .05 || v.currentTime < T.start - .3) v.currentTime = T.start; };
  v.onplay = v.onpause = () => { const b = $('#trimPlay'); if (b) b.innerHTML = v.paused ? ico('play', 'fill') + '放这一段听听' : ico('pause', 'fill') + '暂停'; };
  paint(false);
  filmstrip(v.currentSrc || v.src, D, c1, c2);
}
/* 用隐藏的 <video> 抽帧画一条胶片；画不出来就保持空白底，不影响选段 */
async function filmstrip(url, D, c1, c2) {
  try {
    const v = document.createElement('video'); v.muted = true; v.preload = 'auto'; v.src = url;
    await new Promise((ok, no) => { v.onloadeddata = ok; v.onerror = no; setTimeout(no, 8000); });
    const dpr = Math.min(2, window.devicePixelRatio || 1), cw = Math.round(c1.clientWidth * dpr), ch = Math.round(c1.clientHeight * dpr);
    if (!cw || !ch) return;
    c1.width = c2.width = cw; c1.height = c2.height = ch;
    const fw = ch * v.videoWidth / v.videoHeight, n = Math.ceil(cw / fw), g = c1.getContext('2d'), g2 = c2.getContext('2d');
    for (let k = 0; k < n; k++) {
      if (!c1.isConnected) return;
      v.currentTime = Math.min(D - .05, (k + .5) / n * D);
      await new Promise(ok => { v.onseeked = ok; setTimeout(ok, 1500); });
      g.drawImage(v, k * fw, 0, fw, ch); g2.drawImage(c1, 0, 0);
    }
  } catch { /* 留空白底 */ }
}

/* ============ 2 拉片表 ============ */
const SIZES = ['远景', '全景', '中景', '近景', '特写'];
const SIZE_P = { 远景: '人很小，主要拍环境', 全景: '人和环境都拍全', 中景: '拍到腰以上', 近景: '拍到胸口以上', 特写: '只拍脸或一个细节' };
const CAMS = ['固定', '推', '拉', '摇', '移', '跟', '升', '降', '手持', '环绕'];
const CAM_V = { 推: '往前靠', 拉: '往后退', 摇: '原地转着拍', 移: '横着走', 跟: '跟着人走', 升: '往上升', 降: '往下降', 环绕: '绕着人转' };
const AMPS = ['轻微', '小幅', '中幅', '大幅'], SPEEDS = ['慢', '中', '快'];
function camPlain(c) {
  if (!c || !c.type || c.type === '固定') return '镜头不动';
  if (c.type === '手持') return '有一点晃，像人拿着拍';
  const v = CAM_V[c.type]; if (!v) return '';
  return '镜头' + (c.speed === '慢' ? '慢慢' : c.speed === '快' ? '很快地' : '') + v;
}
const camName = c => !c || !c.type ? '固定' : c.type + (c.type !== '固定' && (c.amp || c.speed) ? '，' + [c.amp, c.speed].filter(Boolean).join('，') : '');
const shotOfLine = (a, l) => { const i = a.shots.findIndex(s => l.start >= s.start - .01 && l.start < s.end); return i < 0 ? a.shots.length - 1 : i; };
const lineText = l => (S.ui.lines[l.i] !== undefined ? S.ui.lines[l.i] : (l.new != null ? l.new : l.text));
const whoName = (p, id) => id ? '人物 ' + id : '旁白';

function s2(ph) {
  const box = $('#s2in'), p = S.p;
  if (!p || ACTIVE_STEP[ph] < 2) { if (memo('s2', 'none')) box.innerHTML = ''; return; }
  const j = (p.jobs && p.jobs.analyze) || {};
  if (ph === 'analyzing') {
    if (memo('s2', 'ing|' + p.id)) {
      box.innerHTML = `<div class="analyzing${isWide(p) ? ' wide' : ''}" style="${arStyle(p)}">
        <div class="frame"><video muted playsinline preload="metadata" src="${esc((p.window && p.window.file) || (p.source && p.source.file))}#t=0.1"></video><span class="tag cool">原片</span></div>
        <div class="ana-r">
          <p>AI 正在一个镜头一个镜头地看这条片子，把每个镜头怎么拍的、说了什么都记下来。<span class="hint">一般不到一分钟${S.st && S.st.mock ? '，模拟模式不扣费' : '，最多 ¥0.05'}。</span></p>
          <div class="now"><span class="spin"></span><span id="anaStep"></span><b id="anaPct"></b></div>
          <div class="bar-track"><i id="anaBar"></i></div>
          <div class="skel"></div><div class="skel rowsk"></div><div class="skel rowsk" style="width:82%"></div><div class="skel rowsk" style="width:64%"></div>
        </div></div>`;
    }
    $('#anaStep').textContent = j.step || '准备中';
    const pr = clamp(+j.progress || 0, 0, 1);
    $('#anaPct').textContent = Math.round(pr * 100) + '%'; $('#anaBar').style.width = (pr * 100) + '%';
    return;
  }
  if (ph === 'anaerr') {
    const e = j.error || {};
    if (memo('s2', 'err|' + JSON.stringify(e))) box.innerHTML = `<div class="alert" role="alert">${ico('alert')}<div><h3>${esc(e.title || (typeof e === 'string' ? e : '拉片没做成'))}</h3><p>${esc(e.action || '右下角点「再拉一次」。')}</p></div></div>`;
    return;
  }
  if (ph === 'anaidle') {
    if (memo('s2', 'idle|' + p.id)) box.innerHTML = `<div class="empty">${ico('film')}<h3>还没拉片</h3><p>让 AI 把这条片子看一遍，列出每个镜头的景别、运镜、动作和台词。后面就照这张表来拍。${S.st && S.st.mock ? '模拟模式不扣费。' : '这一步最多花 ¥0.05。'}</p></div>`;
    return;
  }
  const a = p.analysis; if (!a) return;
  if (focusIn('#shots') && S.memo.s2 && S.memo.s2 !== 'none') return;   // 正在改表，别打断
  const key = 'tbl|' + p.id + '|' + S.ui.adv + '|' + JSON.stringify([a.shots, a.lines.map(l => [l.i, l.start, l.end, l.who, lineText(l)]), a.subtitle, a.watermark, a.vision_by, a.vision_note, p.mode, p.warnings, Object.keys(p.cast || {}), p.window && p.window.dur]);
  if (!memo('s2', key)) return;
  const D = Math.max((p.window && p.window.dur) || 0, a.shots.length ? a.shots[a.shots.length - 1].end : 0) || 15;
  const pct = t => (t / D * 100) + '%';
  let ruler = '';
  const stepLab = D > 20 ? 10 : 5;
  for (let s = 0; s <= Math.floor(D); s++) { ruler += `<i class="${s % stepLab === 0 ? 'maj' : ''}" style="left:${pct(s)}"></i>`; if (s % stepLab === 0 && D - s > stepLab * .45) ruler += `<b style="left:${pct(s)}">${s} 秒</b>`; }
  ruler += `<b class="end" style="left:100%">${+D.toFixed(1)} 秒</b>`;
  const clips = a.shots.map(sh => `<button class="clip${(sh.end - sh.start) / D < .06 ? ' tiny' : ''}" data-shot="${sh.i}" data-n="镜 ${sh.i}" aria-label="镜 ${sh.i}，${tc(sh.start)} 到 ${tc(sh.end)}" style="left:calc(${pct(sh.start)} + 1.5px);width:calc(${pct(sh.end - sh.start)} - 3px);${bg(sh.thumb)}">${sh.hard && sh.hard.length && (sh.end - sh.start) / D >= .14 ? `<span class="tag warm flag">${ico('zap')}高难</span>` : ''}</button>`).join('');
  const cuts = a.shots.slice(1).map(sh => `<span class="cutmark" style="left:${pct(sh.start)}">${sh.start.toFixed(1)}</span>`).join('');
  const lines = a.lines.map(l => `<div class="lineblk${hasCast(p, l.who) ? ' you' : ''}" style="left:${pct(l.start)};width:${pct(l.end - l.start)}" title="${esc(lineText(l))}"><b>${esc(l.who || '旁白')}</b><span>${esc(lineText(l))}</span></div>`).join('');
  const notes = [];
  (p.warnings || []).forEach(w => notes.push(`<div><span class="tag warm">${ico(w.kind === 'hard_shot' ? 'zap' : 'info')}${w.kind === 'hard_shot' ? '高难镜头' : '留意'}</span><span class="hint">${esc(w.text)}</span></div>`));
  if (a.subtitle && a.subtitle.has) notes.push(`<div><span class="tag mute">${ico('type')}原片有字幕</span><span class="hint">${curMode(p) === 'video' ? '「动作照抄」时新片偶尔会把字幕学去，介意就换「照着拍」。' : '「照着拍」不传原片，字幕不会带进新片。'}</span></div>`);
  if (a.vision_note) notes.push(`<div><span class="tag warm">${ico('info')}看片</span><span class="hint">${esc(a.vision_note)}。</span></div>`);
  else if (/^gpt/i.test(a.vision_by || '')) notes.push(`<div><span class="tag mute">${ico('check')}GPT 看片</span><span class="hint">这份拉片表是 ${esc(a.vision_by)} 写的，用的是你的 OpenAI 额度。</span></div>`);
  if (a.watermark) notes.push(`<div><span class="tag mute">${ico('info')}原片有水印</span><span class="hint">水印可能被学进画面，介意就换一条干净的原片。</span></div>`);
  const sel = (list, cur, f, dis) => { const opts = list.includes(cur) || !cur ? list : [cur, ...list]; return `<select class="fld" data-f="${f}"${dis ? ' disabled' : ''} aria-label="${f === 'size' ? '景别' : f === 'type' ? '运镜方式' : f === 'amp' ? '幅度' : '速度'}">${!cur ? '<option value="">—</option>' : ''}${opts.map(x => `<option${x === cur ? ' selected' : ''}>${esc(x)}</option>`).join('')}</select>`; };
  const rows = a.shots.map(sh => {
    const ls = a.lines.filter(l => a.shots[shotOfLine(a, l)].i === sh.i), c = sh.camera || {}, fixed = !c.type || c.type === '固定';
    return `<tr data-shot="${sh.i}">
      <td><div class="th" style="${bg(sh.thumb)}"></div></td>
      <td class="tc"><strong>镜 ${sh.i}</strong><small>${tc(sh.start)} – ${tc(sh.end)}</small><small>${(sh.end - sh.start).toFixed(1)} 秒</small></td>
      <td>${S.ui.adv ? `<div class="edit">${sel(SIZES, sh.size, 'size')}</div>` : `<strong>${esc(sh.size || '—')}</strong><small>${esc(SIZE_P[sh.size] || '')}</small>`}</td>
      <td>${S.ui.adv ? `<div class="edit">${sel(CAMS, c.type || '固定', 'type')}${sel(AMPS, fixed ? '' : c.amp, 'amp', fixed)}${sel(SPEEDS, fixed ? '' : c.speed, 'speed', fixed)}</div>` : `<strong>${esc(camName(c))}</strong>${sh.hard && sh.hard.length ? ` <span class="tag warm">${ico('zap')}${esc(sh.hard.join('、'))}</span>` : ''}<small>${esc(camPlain(c))}</small>`}</td>
      <td class="act">${S.ui.adv ? `<input class="fld w" data-f="action" value="${esc(sh.action)}" aria-label="镜 ${sh.i} 画面里发生什么" maxlength="120">` : esc(sh.action)}</td>
      <td class="say">${ls.length ? ls.map(l => { const t = lineText(l), ch = t !== l.text; return `<p><em>${esc(l.who || '旁白')}</em>${esc(t)}${ch ? ` <span class="tag warm">已改</span>` : ''}<small>${tc(l.start)} – ${tc(l.end)}</small></p>`; }).join('') : '<span class="hint">没有台词</span>'}</td></tr>`;
  }).join('');
  box.innerHTML = `<div style="${arStyle(p)}">
    <div class="tl" id="tl">
      <div class="tl-row"><span></span><div class="ruler">${ruler}</div></div>
      <div class="tl-row" style="margin-top:1.1rem"><span>画面</span><div class="clips">${cuts}${clips}</div></div>
      <div class="tl-row"><span>台词</span><div class="lines">${lines || '<span class="hint" style="font-size:.82rem">这条片子没有台词</span>'}</div></div>
    </div>
    <div class="tl-notes">${notes.join('')}<button class="btn sm ghost sp" data-act="adv">${ico(S.ui.adv ? 'check' : 'pencil')}<span>${S.ui.adv ? '改好了，收起' : '高级：改拉片表'}</span></button></div>
    <table class="shots" id="shots"><thead><tr><th></th><th>时间</th><th>景别<small>拍多大</small></th><th>运镜<small>镜头怎么动</small></th><th>画面里发生什么</th><th>台词${S.ui.adv ? '<small>在第 3 步改</small>' : ''}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
let shotSaveT = 0; const shotDirty = new Set();
function onShotEdit(el) {
  const tr = el.closest('tr'), a = S.p.analysis, sh = a.shots.find(s => String(s.i) === tr.dataset.shot); if (!sh) return;
  const f = el.dataset.f, v = el.value;
  if (f === 'size') sh.size = v; else if (f === 'action') sh.action = v;
  else {
    sh.camera = Object.assign({ type: '固定', amp: '', speed: '' }, sh.camera); sh.camera[f] = v;
    if (f === 'type') { const fixed = v === '固定'; if (fixed) { sh.camera.amp = ''; sh.camera.speed = ''; } else { sh.camera.amp = sh.camera.amp || '小幅'; sh.camera.speed = sh.camera.speed || '中'; } $$('[data-f=amp],[data-f=speed]', tr).forEach(s => { s.disabled = fixed; if (!fixed) { if (![...s.options].some(o => o.value === sh.camera[s.dataset.f])) s.add(new Option(sh.camera[s.dataset.f])); s.value = sh.camera[s.dataset.f]; } else s.value = ''; }); }
  }
  shotDirty.add(sh.i); clearTimeout(shotSaveT); shotSaveT = setTimeout(saveShots, 600);
}
async function saveShots() {
  const p = S.p; if (!p || !shotDirty.size) return;
  const shots = [...shotDirty].map(i => { const s = p.analysis.shots.find(x => x.i === i); return { i, size: s.size, camera: s.camera, action: s.action }; });
  shotDirty.clear();
  try { await mutate('PATCH', `/api/projects/${p.id}/analysis`, { shots }); } catch (e) { showError(e); }
}

/* ============ 3 换成你的 ============ */
const countChars = s => (String(s).match(/[㐀-鿿A-Za-z0-9]/g) || []).length;
const lineOver = l => l.limit_chars ? countChars(lineText(l)) - l.limit_chars : 0;
const anyOver = p => p.analysis ? p.analysis.lines.find(l => lineOver(l) > 0) : null;
function s3(ph) {
  const box = $('#s3in'), p = S.p;
  if (!p || !p.analysis || ACTIVE_STEP[ph] < 3) { if (memo('s3', 'none')) box.innerHTML = ''; return; }
  const a = p.analysis, main = mainPerson(p);
  const key = p.id + '|' + JSON.stringify([a.people, p.cast, p.scene, a.env, a.lines.map(l => [l.i, l.text, l.limit_chars, l.who, l.start, l.end]), a.rate, S.ui.busy.cast, p.swap, p.swap_suggest, S.ui.busy.swap, p.audio, p.audio_suggest, p.has_orig_audio, S.ui.busy.audio, p.mode]);
  if (focusIn('#s3in') && S.memo.s3 && S.memo.s3 !== 'none') return;
  if (!memo('s3', key)) return;
  const faceOf = id => { const s = a.shots.find(s => (s.who || []).includes(id)) || a.shots[0]; return s ? s.thumb : ''; };
  const inShots = id => a.shots.filter(s => (s.who || []).includes(id)).map(s => s.i);
  /* 角度照（11-24）：动作照抄时 AI 会让人转回来看镜头，多给几张侧脸/转头照，头才会跟着原片转 */
  const angleRow = id => {
    const ags = (p.cast[id] && p.cast[id].angles) || [], busy = S.ui.busy.cast === 'angle:' + id, off = curMode(p) !== 'video';
    return `<div class="angles${off ? ' off' : ''}">
      <div class="label">角度照<span class="hint">可选 · 动作照抄时才用</span></div>
      <div class="angrow">${ags.map((g, i) => `<div class="slotw angw"><div class="ang" style="${bg(g.photo)}" title="${g.mirror_of ? '自动镜像出来的另一边' : '你放的角度照'}"></div>${g.mirror_of ? '<span class="ang-tag">镜像</span>' : ''}<button class="slot-x" data-act="dropAngle" data-person="${esc(id)}" data-i="${i}" aria-label="拿掉这张角度照">${ico('x')}</button></div>`).join('')}${ags.length < 3 ? `<button class="ang add${busy ? ' busy' : ''}" data-act="pickAngle" data-person="${esc(id)}" aria-label="加一张人物 ${esc(id)} 的角度照">${busy ? '<span class="spin"></span>' : ico('plus')}</button>` : ''}</div>
      ${ags.flatMap(g => g.warn || []).map(w => `<p class="warnline">${ico('alert')}${esc(w)}</p>`).join('')}
      <p>${off ? '现在是「照着拍」，角度照用不上；换成「动作照抄」才会用。' : '原片里回头、侧脸多（比如跳舞时看向举起的手），再放 1～2 张侧脸或转头的照片，头会跟着原片转。侧脸照会自动镜像出另一边。'}</p>
      ${ags.length < 3 ? `<p class="angcopy">没有侧脸照？复制提示词，连同主照片一起发给 GPT 或豆包生成，再传回来：<button class="btn ghost sm" data-act="copyAnglePrompt" data-k="side">${ico('copy')}纯侧脸</button><button class="btn ghost sm" data-act="copyAnglePrompt" data-k="turn">${ico('copy')}四分之三侧</button></p>` : ''}
    </div>`;
  };
  const whoRow = pp => {
    const filled = hasCast(p, pp.id), isMain = pp.id === main, shots = inShots(pp.id), busy = S.ui.busy.cast === pp.id;
    return `<div class="who${isMain ? '' : ' small'}">
      <div class="face" style="${bg(faceOf(pp.id))}" title="原片里的人物 ${esc(pp.id)}"></div>${ico('arrow', 'arr')}
      <div class="slotw"><button class="slot${filled ? ' filled' : isMain ? ' need' : ''}${busy ? ' busy' : ''}" data-act="pickCast" data-person="${esc(pp.id)}" style="${filled ? bg(p.cast[pp.id].photo) : ''}" aria-label="${filled ? '换一张' : '选'}人物 ${esc(pp.id)} 的照片">${busy ? '<span class="spin"></span>' : ico(isMain ? 'user' : 'plus')}</button>${filled ? `<button class="slot-x" data-act="dropCast" data-person="${esc(pp.id)}" aria-label="拿掉人物 ${esc(pp.id)} 的照片">${ico('x')}</button>` : ''}</div>
      <div><h4>人物 ${esc(pp.id)} ${filled ? '<span class="tag warm">已换成你的</span>' : isMain ? '<span class="tag warm">要选一张</span>' : '<span class="hint">可以不换</span>'}</h4>
        ${filled || isMain ? `<p>原片里：${esc((pp.desc || '—').replace(/[。.\s]+$/, ''))}${shots.length ? `。出现在镜 ${shots.join('、')}` : ''}。</p>` : ''}
        ${filled ? `${((p.cast[pp.id] && p.cast[pp.id].warn) || []).map(w => `<p class="warnline">${ico('alert')}${esc(w)}</p>`).join('')}<p>点照片可以换一张。</p>${angleRow(pp.id)}` : isMain ? '<p>放一张你的照片。拍到全身的话，衣服也一起换；大头照只换脸和发型。也可以把照片直接拖到框里。</p>' : `<p>${shots.length ? `出现在镜 ${shots.join('、')}。` : ''}不传照片，就按下面这句外貌来拍，可以改。</p><input class="fld w" data-in="desc" data-person="${esc(pp.id)}" value="${esc(pp.desc)}" maxlength="80" aria-label="人物 ${esc(pp.id)} 的外貌描述">`}
      </div></div>`;
  };
  const sceneOn = !!(p.scene && p.scene.photo);
  const sg = p.swap_suggest || {}, sw = curSwap(p);
  const swapSel = `<div class="swapsel"><div class="label">换人方式<span class="hint">只影响怎么换，不影响价钱</span></div>
    <div class="modes${S.ui.busy.swap ? ' busy' : ''}" role="radiogroup" aria-label="换人方式">${SWAPS.map(m => `<button class="mode" role="radio" aria-checked="${m.id === sw}" data-act="swap" data-id="${m.id}"><span class="dot"></span><strong>${m.name}${sg.swap === m.id ? '<span class="tag warm">推荐</span>' : ''}</strong><small>${m.desc}</small>${sg.swap === m.id && sg.why ? `<small class="why">${ico('zap')}<span>为什么推荐：${esc(sg.why)}</span></small>` : ''}</button>`).join('')}</div></div>`;
  const ag = p.audio_suggest || {}, au = curAudio(p);
  const audioSel = `<div class="swapsel"><div class="label">声音<span class="hint">不影响价钱</span></div>
    <div class="modes${S.ui.busy.audio ? ' busy' : ''}" role="radiogroup" aria-label="声音">${AUDIOS.map(m => { const off = m.id === 'orig' && !p.has_orig_audio; return `<button class="mode" role="radio" aria-checked="${m.id === au}" data-act="audio" data-id="${m.id}"${off ? ' disabled' : ''}><span class="dot"></span><strong>${m.name}${ag.audio === m.id ? '<span class="tag warm">推荐</span>' : ''}</strong><small>${off ? '原片没有声音，用不了。' : m.desc}</small>${ag.audio === m.id && ag.why ? `<small class="why">${ico('zap')}<span>为什么推荐：${esc(ag.why)}</span></small>` : ''}</button>`; }).join('')}</div></div>`;
  const scene = `<div class="who small">
      <div class="face" style="${bg(a.shots[0] && a.shots[0].thumb)}"></div>${ico('arrow', 'arr')}
      <div class="slotw"><button class="slot${sceneOn ? ' filled' : ''}${S.ui.busy.cast === '#scene' ? ' busy' : ''}" data-act="pickScene" style="${sceneOn ? bg(p.scene.photo) : ''}" aria-label="选场景图">${ico('image')}</button>${sceneOn ? `<button class="slot-x" data-act="dropScene" aria-label="拿掉场景图">${ico('x')}</button>` : ''}</div>
      <div><h4>场景 ${sceneOn ? '<span class="tag warm">已换</span>' : '<span class="hint">可以不换</span>'}</h4><p>${sceneOn ? '会在你给的这个场景里拍。' : `不传就沿用原片的${a.env ? '「' + esc(a.env) + '」' : '场景'}。`}</p></div></div>`;
  const dl = a.lines.length ? a.lines.map(l => {
    const v = lineText(l), si = shotOfLine(a, l);
    return `<div class="dlg" data-line="${l.i}">
      <div class="dlg-top"><span class="tag ${hasCast(p, l.who) ? 'warm' : 'mute'}">${esc(whoName(p, l.who))}${hasCast(p, l.who) ? ' · 你' : ''}</span><span class="num">${tc(l.start)} – ${tc(l.end)}</span><span>镜 ${a.shots[si] ? a.shots[si].i : '?'}</span><button data-act="lineReset" hidden>${ico('undo')}用回原台词</button></div>
      <input value="${esc(v)}" data-in="line" aria-label="第 ${l.i} 句台词" maxlength="80" autocomplete="off" spellcheck="false">
      <div class="meter"><div class="meter-t"><i></i><u title="原片这句话的长度"></u></div><div class="meter-m" aria-live="polite"></div></div></div>`;
  }).join('') : '<p class="nolines">这条片子没有台词，直接看价钱开拍就行。</p>';
  const mainP = a.people.filter(pp => pp.id === main), restP = a.people.filter(pp => pp.id !== main);
  box.innerHTML = `<div class="swap"><div><div class="label">换人</div>${mainP.map(whoRow).join('')}${swapSel}${restP.map(whoRow).join('')}${scene}</div>
    <div>${audioSel}<div class="label">台词<span class="hint">${au === 'orig' ? '现在用原片原声，台词就是原片的。想改就直接改，声音会自动换成「H3 重新配」；' : '默认照搬原片，H3 会自己开口说。想改就直接改，'}蓝线是原片这句话的长度，别超过它。</span></div><div id="dlgs">${dl}</div></div></div>`;
  $$('#dlgs .dlg').forEach(paintMeter);
}
function paintMeter(d) {
  const l = S.p.analysis.lines.find(x => String(x.i) === d.dataset.line); if (!l) return;
  const v = lineText(l), n = countChars(v), lim = l.limit_chars || 0, over = lim ? n - lim : 0;
  d.classList.toggle('over', over > 0);
  d.querySelector('.meter-t i').style.width = (lim ? Math.min(n / lim * 78, 100) : 0) + '%';
  d.querySelector('.meter-m').innerHTML = !lim ? `<span class="num">${n}</span> 个字` : over > 0 ? `<b class="num">${n}</b> 个字，这句最多 <b class="num">${lim}</b> 个。超了 ${over} 个字，删掉 ${over} 个就行` : `<span class="num">${n} / ${lim}</span> 个字${n === 0 ? '，留空就是这句不说' : ''}`;
  d.querySelector('[data-act=lineReset]').hidden = v === l.text;
}
let lineSaveT = 0;
function onLineInput(inp) {
  const d = inp.closest('.dlg'), i = +d.dataset.line;
  S.ui.lines[i] = inp.value; S.ui.dirtyLines.add(i);
  paintMeter(d); renderDock(phase());
  clearTimeout(lineSaveT); lineSaveT = setTimeout(saveLines, 600);
}
async function saveLines() {
  const p = S.p; if (!p || !S.ui.dirtyLines.size) return;
  const lines = [...S.ui.dirtyLines].map(i => { const l = p.analysis.lines.find(x => x.i === i), v = S.ui.lines[i]; return { i, new: v === l.text ? null : v }; });
  S.ui.dirtyLines.clear();
  try { await mutate('PATCH', `/api/projects/${p.id}/analysis`, { lines }); } catch (e) { showError(e); }
}
let descT = 0;
function onDescInput(inp) {
  const p = S.p, pp = p.analysis.people.find(x => x.id === inp.dataset.person); if (!pp) return;
  pp.desc = inp.value; clearTimeout(descT);
  descT = setTimeout(async () => { try { await mutate('PATCH', `/api/projects/${p.id}/analysis`, { people: [{ id: pp.id, desc: pp.desc }] }); } catch (e) { showError(e); } }, 700);
}
/* 角度照提示词（11-24：用户用这段让 GPT 从主照片生成的侧脸照，头能跟着原片转；MiniMax 生图的显老、不像本人，所以不做一键生成） */
const ANGLE_KEEP = '五官、脸型、肤色、妆容、发型发色、饰品和衣服都和原照片完全一样，不要美化，不要改脸。胸部以上的半身照，浅灰色纯色背景，柔和的棚拍光，真实摄影质感，竖版 3:4。';
const ANGLE_PROMPTS = {
  side: '以我上传的照片为准，生成同一个人的真实照片：完全侧脸，头转 90 度朝向这个人自己的左边，只看得到一只眼睛，鼻子和下巴的侧面轮廓清楚。' + ANGLE_KEEP,
  turn: '以我上传的照片为准，生成同一个人的真实照片：头和脸向这个人自己的左边转约 45 度，眼睛看向画面外的左上方。' + ANGLE_KEEP,
};
async function copyText(text, okMsg) {
  try { await navigator.clipboard.writeText(text); toast(okMsg); return; } catch { /* 浏览器不让写剪贴板时退回老办法 */ }
  const t = document.createElement('textarea'); t.value = text; t.style.cssText = 'position:fixed;opacity:0'; document.body.appendChild(t); t.select();
  try { document.execCommand('copy'); toast(okMsg); } catch { showError({ title: '复制没成功', action: '手动选中下面这段复制：' + text }); }
  t.remove();
}
async function uploadImage(file, target) {   // target: 人物 id、'angle:人物 id'（角度照），或 '#scene'
  const p = S.p; if (!p || !file) return;
  if (!/^image\//.test(file.type) && !/\.(png|jpe?g|webp)$/i.test(file.name)) return showError({ title: '这不是一张图片', action: '选 JPG、PNG 或 WebP 格式的照片。' });
  const fd = new FormData();
  if (target.startsWith('angle:')) { fd.append('person', target.slice(6)); fd.append('angle', '1'); }
  else if (target !== '#scene') fd.append('person', target);
  fd.append('file', file);
  S.ui.busy.cast = target; render();
  try { await mutate('POST', `/api/projects/${p.id}/${target === '#scene' ? 'scene' : 'cast'}`, fd); }
  catch (e) { showError(e); }
  finally { S.ui.busy.cast = null; render(); }
}

/* ============ 4 看价钱，开拍 ============ */
const MODES = [
  { id: 'text', name: '照着拍', desc: '换人最稳，价钱减半。构图和运镜会重新拍，不是逐帧一样。适合有对白、有近景的短剧。' },
  { id: 'video', name: '动作照抄', desc: '动作、构图和原片一模一样，价钱翻倍。原演员的脸会自动涂掉。适合跳舞、动作类的全身镜头。' }
];
const curMode = p => (p && p.mode === 'video') ? 'video' : 'text';
const modeName = id => (MODES.find(m => m.id === id) || MODES[0]).name;
async function setMode(id) {
  const p = S.p; if (!p || S.ui.busy.mode || curMode(p) === id) return;
  if (id === 'video' && p.analysis) {
    // 实测说话片用动作照抄嘴型对不上、脸变形，价钱还贵一倍
    const talk = (p.analysis.lines || []).some(l => l.new !== ''), close = (p.analysis.shots || []).some(s => s.size === '近景' || s.size === '特写');
    if ((talk || close) && !(await ask({ title: `这条片子${talk ? '有人说话' : '有近景'}，确定用动作照抄？`,
      text: '实测这类片子用动作照抄，嘴型多半对不上原声，人脸也容易变形，价钱还贵一倍。有人说话、有近景的片子用「照着拍」更好。',
      yes: '还是用动作照抄', no: '用照着拍' }))) return;
  }
  S.ui.busy.mode = true; render();
  try { await mutate('POST', `/api/projects/${p.id}/mode`, { mode: id }); }
  catch (e) { showError(e); }
  finally { S.ui.busy.mode = false; render(); }
}
const SWAPS = [
  { id: 'full', name: '换整个人', desc: '脸、发型、身材、衣服鞋包都跟你的照片。照片要拍到全身，衣服也会换成照片里的。' },
  { id: 'head', name: '只换脸和发型', desc: '衣服沿用原片的。适合大头照，衣服保持原片的样子。' }
];
const curSwap = p => (p && p.swap === 'full') ? 'full' : 'head';
async function setSwap(id) {
  const p = S.p; if (!p || S.ui.busy.swap || curSwap(p) === id) return;
  S.ui.busy.swap = true; render();
  try { await mutate('POST', `/api/projects/${p.id}/swap`, { swap: id }); }
  catch (e) { showError(e); }
  finally { S.ui.busy.swap = false; render(); }
}
const AUDIOS = [
  { id: 'orig', name: '用原片原声', desc: '人声、背景音乐、节奏和原片一模一样，人物照着原声对口型。台词照原片，不能改。' },
  { id: 'new', name: 'H3 重新配', desc: '新的人用新的声音说，台词可以逐句改。' }
];
const curAudio = p => (p && p.audio === 'orig') ? 'orig' : 'new';
async function setAudio(id) {
  const p = S.p; if (!p || S.ui.busy.audio || curAudio(p) === id) return;
  S.ui.busy.audio = true; render();
  try { await mutate('POST', `/api/projects/${p.id}/audio`, { audio: id }); }
  catch (e) { showError(e); }
  finally { S.ui.busy.audio = false; render(); }
}
const tierOf = id => (S.st ? S.st.tiers : []).find(t => t.id === id);
const curTier = () => (tierOf(S.ui.tier) || tierOf(S.st && S.st.settings.tier) || (S.st && S.st.tiers[0]) || { id: '' }).id;
const curTakes = () => clamp(+S.ui.takes || 1, 1, 4);
const activeQuote = () => S.ui.trial ? S.q.trial : S.q.full;
function quoteSig() {
  const p = S.p, a = p.analysis;
  return [p.id, curTier(), curTakes(), JSON.stringify([a.lines.map(l => l.new), a.shots.map(s => [s.size, s.camera, s.action]), p.mode, p.swap, p.audio, p.cast, p.scene, p.prompt && [p.prompt.custom, p.prompt.text], p.window, p.budget, p.spent, S.st && S.st.mock, S.st && S.st.settings.budget])].join('|');
}
let quoteT = 0, quoteSeq = 0;
function ensureQuote(force) {
  const p = S.p; if (!p || !p.analysis) return;
  const sig = quoteSig();
  if (!force && sig === S.q.sig) return;
  S.q.sig = sig; S.q.loading = true; S.q.err = null;
  clearTimeout(quoteT);
  const seq = ++quoteSeq;
  quoteT = setTimeout(async () => {
    const base = `/api/projects/${p.id}/quote?tier=${encodeURIComponent(curTier())}&takes=${curTakes()}`;
    try {
      const [full, trial] = await Promise.all([api('GET', base + '&trial=0'), api('GET', base + '&trial=1')]);
      if (seq !== quoteSeq) return;
      S.q.full = full; S.q.trial = trial; S.q.err = null;
    } catch (e) { if (seq !== quoteSeq) return; S.q.err = e; }
    S.q.loading = false;
    const ph = phase(); s4(ph); renderDock(ph);
  }, 180);
  const ph = phase(); s4(ph); renderDock(ph);
}
function s4(ph) {
  const box = $('#s4in'), p = S.p, st = S.st;
  if (!p || !p.analysis || !st || ACTIVE_STEP[ph] < 4) { if (memo('s4', 'none')) box.innerHTML = ''; return; }
  const q = activeQuote(), tr = S.q.trial, tier = curTier(), n = curTakes(), firstTime = !okTakes(p).length;
  const trs = (tr && tr.out_sec) || 5;
  const custom = !!(p.prompt && p.prompt.custom);
  const promptText = custom ? (p.prompt.text || '') : ((q && q.prompt) || (p.prompt && p.prompt.text) || '');
  const key = JSON.stringify([p.id, tier, n, S.ui.trial, q, tr && tr.sum, S.q.loading, S.q.err, st.tiers, st.mock, firstTime, custom, p.mode, p.mode_suggest, S.ui.busy.mode, S.ui.promptDirty, p.warnings, S.ui.busy.prompt]) + (focusIn('#promptFold') ? '' : promptText);
  if (!memo('s4', key)) return;
  const keepOpen = $('#promptFold') ? $('#promptFold').open : false;
  const draft = S.ui.promptDirty && $('#prompt') ? $('#prompt').value : null;
  const mock = q ? q.mock : isMock();
  const tiers = st.tiers.map(t => `<button class="tier" role="radio" aria-checked="${t.id === tier}" data-act="tier" data-id="${esc(t.id)}"><span class="dot"></span><strong>${esc(t.name)}<span>${esc(t.model.replace(/^MiniMax-/, ''))} · ${esc(t.resolution)}</span></strong><span class="p">¥${price(t.per_sec)}/秒</span><small>${esc(t.hint)}</small></button>`).join('');
  let receipt;
  if (S.q.err && !q) receipt = `<h4><span>报价小票</span></h4><p style="color:var(--bad);font-weight:500">${esc(S.q.err.title)}</p><p class="hint" style="margin:.3rem 0 .8rem">${esc(S.q.err.action)}</p><button class="btn sm" data-act="requote">${ico('refresh')}再算一次</button>`;
  else if (!q) receipt = `<h4><span>报价小票</span></h4><div class="skel" style="height:1.2rem;margin-bottom:.6rem"></div><div class="skel" style="height:1.2rem;width:80%;margin-bottom:.6rem"></div><div class="skel" style="height:2.4rem;width:55%;margin-left:auto"></div>`;
  else {
    const left = +q.budget_left, over = q.over_budget;
    receipt = `<h4><span>报价小票${q.out_sec < ((p.window && p.window.dur) || 15) ? ' · 试拍' : ''}</span>${mock ? '<span class="tag cool">模拟，不扣费</span>' : ''}</h4><dl>
      <dt>拍出来的片子<small>${+q.out_sec} 秒 × ¥${price(q.per_sec)}</small></dt><dd>${price(q.out)}</dd>
      ${+q.ref_sec ? `<dt>参考原片<small>${+q.ref_sec} 秒 × ¥${price(q.per_sec)}</small></dt><dd>${price(q.ref)}</dd>` : `<dt>参考原片<small style="font-family:var(--sans)">照着拍，不传原片</small></dt><dd>0.00</dd>`}
      <dt>参考照片<small>${+q.images} 张</small></dt><dd>${+q.img ? price(q.img) : '免费'}</dd>
      ${q.takes > 1 ? `<div class="rule"></div><dt>每条</dt><dd>${price(q.total)}</dd><dt>拍 ${q.takes} 条<small>× ${q.takes}</small></dt><dd>${price(q.sum)}</dd>` : ''}
      <div class="rule"></div>
      <div class="total"><dt>${mock ? '真拍的话约' : '这次约'}</dt><dd>${yuan(q.sum)}</dd></div></dl>
      <div class="after${over ? ' bad' : ''}">${over ? `${ico('alert')} 超预算了：这次要 ${yuan(q.sum)}，这个作品的预算只剩 ${yuan(left)}。少拍一条、换便宜的档位，或者去「设置」把预算上限调高。`
        : mock ? '现在是模拟模式，这次不会扣费，拍出来的是样片。价钱按官方单价算给你看。'
        : `预算还剩 ${yuan(left)}，拍完大约剩 ${yuan(left - q.sum)}。实际扣费以 MiniMax 账单为准。`}</div>`;
  }
  const know = [];
  if (q) {
    (q.blockers || []).forEach(b => know.push(`<li class="is-bad">${ico('alert')}<div>${esc(b.text)}<small>改好这一条才能开拍。</small></div></li>`));
    (q.notices || []).forEach(t => know.push(`<li class="${/已/.test(t) ? 'is-ok' : 'is-warn'}">${ico(/已/.test(t) ? 'check' : 'info')}<div>${esc(t)}</div></li>`));
  }
  if (curMode(p) === 'video') know.push(`<li class="is-warn">${ico('info')}<div>你的人和原片的人体型差太多会走样<small>这个要你自己看一眼。差得多，就换一张全身比例接近的照片。</small></div></li>`);
  else know.push(`<li class="is-warn">${ico('info')}<div>构图和运镜是照拉片表重新拍的<small>节奏、台词、切点跟原片走，画面不会逐帧一样。要动作一模一样，上面换成「动作照抄」。</small></div></li>`);
  const sug = p.mode_suggest || {}, mode = curMode(p);
  const modes = MODES.map(m => `<button class="mode" role="radio" aria-checked="${m.id === mode}" data-act="mode" data-id="${m.id}"><span class="dot"></span><strong>${m.name}${sug.mode === m.id ? '<span class="tag warm">推荐</span>' : ''}</strong><small>${m.desc}</small>${sug.mode === m.id && sug.why ? `<small class="why">${ico('zap')}<span>为什么推荐：${esc(sug.why)}</span></small>` : ''}</button>`).join('');
  box.innerHTML = `<div class="label">怎么拍<span class="hint">两种拍法，价钱不一样，开拍前随时可以换</span></div>
  <div class="modes${S.ui.busy.mode ? ' busy' : ''}" role="radiogroup" aria-label="拍法">${modes}</div>
  <div class="quote">
    <div>
      <div class="label">画质档位</div>
      <div role="radiogroup" aria-label="画质档位">${tiers}</div>
      <div class="label" style="margin-top:1.1rem">一次拍几条</div>
      <div class="nrow"><div class="stepper"><button data-act="nMinus" aria-label="少拍一条"${n <= 1 ? ' disabled' : ''}>−</button><b aria-live="polite">${n}</b><button data-act="nPlus" aria-label="多拍一条"${n >= 4 ? ' disabled' : ''}>+</button></div><span class="hint">先拍 1 条看看，不满意再拍一条。</span></div>
      <label class="trial${S.ui.trial ? ' on' : ''}"><span class="check"><input type="checkbox" data-in="trial"${S.ui.trial ? ' checked' : ''} aria-label="先试前 ${trs} 秒"></span><strong>先试前 ${trs} 秒${firstTime && !mock ? '<span class="tag warm">第一次建议</span>' : ''}</strong><span class="p">${tr ? yuan(tr.sum) : '…'}</span><small>花小钱先看人像不像、画面对不对，满意了再拍整条。</small></label>
    </div>
    <div class="receipt${mock ? ' mock' : ''}${S.q.loading && q ? ' stale' : ''}" aria-busy="${S.q.loading}">${receipt}</div>
    <div><div class="label">拍之前知道这几件事</div><ul class="know">${know.join('')}</ul></div>
  </div>
  <details class="fold" id="promptFold"${keepOpen ? ' open' : ''}>
    <summary>${ico('chev')}看看发给 AI 的提示词${custom ? ' <span class="tag warm">你改过</span>' : '（已按官方写法拼好，一般不用动）'}</summary>
    <textarea spellcheck="false" id="prompt" data-in="prompt" aria-label="发给 AI 的提示词">${esc(draft != null ? draft : promptText)}</textarea>
    <div class="fold-act"><button class="btn sm${S.ui.busy.prompt ? ' busy' : ''}" data-act="promptSave"${S.ui.promptDirty ? '' : ' disabled'}>${S.ui.busy.prompt ? '<span class="spin"></span>' : ''}保存我改的</button>${custom ? `<button class="btn sm ghost" data-act="promptReset">${ico('undo')}恢复自动拼的</button>` : ''}<span class="hint">${custom ? '现在用的是你改过的版本。之后再改拉片表和台词，不会自动同步到这里。' : '改拉片表和台词时，这里会自动跟着变。'}</span></div>
  </details>`;
}
function shootKey(q) { return [S.p.id, q.tier, q.takes, S.ui.trial, q.sum].join('|'); }
async function shoot() {
  const p = S.p, q = activeQuote();
  if (!p || !q || S.ui.busy.shoot || S.q.loading) return;
  const tier = tierOf(q.tier) || {};
  if (!q.mock) {
    const ok = await ask({
      title: S.ui.trial ? `确认试拍前 ${q.out_sec || 5} 秒？` : `确认开拍 ${q.takes} 条？`,
      text: '点了确认就提交给 MiniMax，开始扣费。拍摄中不能取消。',
      rows: [['拍法', modeName(q.mode || curMode(p))], ['档位', `${tier.name || ''} · ${tier.resolution || ''}`], ['拍几条', `${q.takes} 条 × ${+q.out_sec} 秒`], ['这次约', yuan(q.sum), 'tot']],
      yes: '确认，开拍'
    });
    if (!ok) return;
  }
  const k = shootKey(q);
  if (S.ui.nonceFor !== k) { S.ui.nonce = uid(); S.ui.nonceFor = k; }
  S.ui.busy.shoot = true; renderDock(phase());
  try {
    const d = await api('POST', `/api/projects/${p.id}/shoot`, { tier: q.tier, takes: q.takes, trial: !!S.ui.trial, confirm_total: q.sum, nonce: S.ui.nonce, mock: !!q.mock });
    S.ui.nonce = null; S.ui.nonceFor = ''; S.ui.reshoot = false; S.ui.trial = false;
    S.ui.busy.shoot = false;
    if (isProject(d)) setProject(d); else setProject(await api('GET', `/api/projects/${p.id}`));
    loadState();
  } catch (e) {
    S.ui.busy.shoot = false; showError(e); ensureQuote(true); renderDock(phase());
  }
}

/* ============ 5 拍摄 ============ */
function s5(ph) {
  const box = $('#s5in'), p = S.p;
  const takes = (p && p.takes) || [];
  if (!p || !takes.length) { if (memo('s5', 'none')) box.innerHTML = ''; return; }
  const key = p.id + '|' + JSON.stringify(takes.map(t => [t.id, t.status, t.step, t.error, t.file, t.trial, t.quote, t.actual, t.tier])) + '|' + ph + '|' + JSON.stringify(S.ui.busy.take || '') + isMock();
  if (memo('s5', key)) {
    const act = takes.filter(t => ACTIVE_ST.includes(t.status)).length, ok = okTakes(p).length, bad = takes.filter(t => t.status === 'failed').length;
    const blur = (p.cast && p.cast[mainPerson(p)] && p.cast[mainPerson(p)].photo) || (p.analysis && p.analysis.shots[0] && p.analysis.shots[0].thumb);
    const cards = takes.map(t => {
      const cls = t.status === 'succeeded' ? 'ok' : t.status === 'failed' ? 'fail' : t.status === 'cancelled' ? 'off' : 'run';
      const e = t.error || {}, busy = S.ui.busy.take === t.id;
      const money = t.actual != null ? yuan(t.actual) : t.quote != null ? '约 ' + yuan(t.quote) : '';
      return `<div class="take ${cls}" data-take="${esc(t.id)}">
        <div class="frame">${cls === 'ok' ? `<video muted playsinline preload="metadata" src="${esc(t.file)}#t=0.5"></video>` : `<div class="pic" style="${bg(blur)}"></div><div class="ov">${cls === 'run' ? `${esc(t.step === 'facelock' ? '换脸中' : TAKE_CN[t.status])}${t.status === 'queued' ? '' : `<b class="t-el">${clock(t.elapsed)}</b>`}` : cls === 'fail' ? ico('alert') + '没拍成' : '已取消'}</div>`}<span class="tag warm">第 ${t.n} 条${t.trial ? ' · 试拍' : ''}</span></div>
        <div class="bar-track${cls === 'run' && t.status !== 'queued' ? ' run' : ''}"><i></i></div>
        <div class="t-st"><span>${esc(t.step === 'facelock' ? '换脸中' : (TAKE_CN[t.status] || t.status))}</span><span>${isMock() && t.actual == null ? '模拟' : money}</span></div>
        ${cls === 'fail' ? `<p class="t-why"><b>${esc(e.title || '这一条没拍成')}</b>${esc(e.action || '可以点下面重拍。')}</p>${e.detail ? `<small class="t-raw">${e.refinish ? '原因' : 'MiniMax 原话'}：${esc(e.detail)}</small>` : ''}<button class="btn sm${busy ? ' busy' : ''}" data-act="${e.refinish ? 'refinish' : 'retry'}">${busy ? '<span class="spin"></span>' : ico('refresh')}${e.refinish ? '再试一次（不扣费）' : '重拍这一条'}</button>`
        : t.status === 'queued' ? `<p class="t-why">还没开拍，现在取消不扣费。</p><button class="btn sm ghost${busy ? ' busy' : ''}" data-act="cancel">${busy ? '<span class="spin"></span>' : ''}取消这一条</button>`
        : t.status === 'running' ? '<p class="t-why">画面、台词、口型一起出。</p>'
        : t.status === 'downloading' ? (t.step === 'facelock' ? `<p class="t-why">拍好了，正在本机把脸再换一遍，更像你的照片（${S.st && S.st.face_lock && S.st.face_lock.gpu ? '用 N 卡，约 1 分钟' : '没有 N 卡，用 CPU，要多等几分钟'}）。</p>` : '<p class="t-why">拍好了，正在存到你电脑上。</p>')
        : t.status === 'succeeded' ? `<p class="t-why">已存到本机${t.created ? '，' + esc(t.created) + ' 提交' : ''}。</p>` : '<p class="t-why">没有扣费。</p>'}
      </div>`;
    }).join('');
    const h = act ? `${act} 条正在拍${ok ? `，已拍好 ${ok} 条` : ''}` : ph === 'failed' ? (takes.length > 1 ? '这几条都没拍成' : '这一条没拍成') : `拍好 ${ok} 条${bad ? `，${bad} 条没拍成` : ''}`;
    const para = act ? '每条都是整段一次拍完，画面、台词、口型一起出。一般几分钟一条。' : ph === 'failed' ? '每张卡片下面写了原因和该怎么办。改好了可以单独重拍那一条，重拍前还会先报价。' : '拍好的片子都在第 6 步里，和原片对着挑。';
    box.innerHTML = `<div class="shoot" style="${arStyle(p)}"><div class="takes" style="--n:${Math.min(4, takes.length)}">${cards}</div>
      <div class="shoot-info"><h3>${h}</h3><p>${para}</p>${act ? `<div class="away">${ico('clock')}<span>可以关掉这个网页去忙别的。任务号已经存在你电脑上，回来打开自动接着看，拍好的片子会自己下载。</span></div>` : ''}</div></div>`;
  }
  takes.forEach(t => { const el = $(`#s5in .take[data-take="${CSS.escape(t.id)}"] .t-el`); if (el) el.textContent = clock(t.elapsed); });
}
async function retryTake(tid) {
  const p = S.p, t = (p.takes || []).find(x => x.id === tid); if (!t || S.ui.busy.take) return;
  S.ui.busy.take = tid; render();
  try {
    const q = await api('GET', `/api/projects/${p.id}/quote?tier=${encodeURIComponent(t.tier)}&takes=1&trial=${t.trial ? 1 : 0}`);
    if (q.blockers && q.blockers.length) throw { title: '现在还不能重拍', action: q.blockers[0].text };
    if (q.over_budget) throw { title: '重拍会超预算', action: `重拍这一条要 ${yuan(q.sum)}，预算只剩 ${yuan(q.budget_left)}。去「设置」把预算上限调高，或者换便宜的档位重新开拍。` };
    const tier = tierOf(t.tier) || {};
    const ok = q.mock || await ask({ title: `重拍第 ${t.n} 条？`, text: '点了确认就重新提交，开始扣费。', rows: [['档位', `${tier.name || ''} · ${tier.resolution || ''}`], ['这次约', yuan(q.sum), 'tot']], yes: '确认，重拍' });
    if (ok) { await mutate('POST', `/api/projects/${p.id}/takes/${tid}/retry`, { confirm_total: q.sum, nonce: uid(), mock: !!q.mock }); loadState(); }
  } catch (e) { showError(e); }
  finally { S.ui.busy.take = null; render(); schedulePoll(); }
}
async function takeAction(tid, act, msg) {
  const p = S.p; if (!p || !tid || S.ui.busy.take) return;
  S.ui.busy.take = tid; render();
  try { await mutate('POST', `/api/projects/${p.id}/takes/${tid}/${act}`, {}); toast(msg); }
  catch (e) { showError(e); }
  finally { S.ui.busy.take = null; render(); schedulePoll(); }
}
async function cancelTake(tid) {
  const p = S.p; if (S.ui.busy.take) return;
  S.ui.busy.take = tid; render();
  try { await mutate('POST', `/api/projects/${p.id}/takes/${tid}/cancel`); toast('已取消，没有扣费'); }
  catch (e) { showError(e); }
  finally { S.ui.busy.take = null; render(); }
}

/* ============ 6 挑片：真 <video> 同步对照 ============ */
const player = {
  master: null, cands: [], dur: 15, playing: false, raf: 0,
  build(dur) {
    this.stop(); this.dur = dur;
    this.master = $('#s6in video[data-k=src]');
    this.cands = $$('#s6in video[data-k]:not([data-k=src])').map(v => ({ v, id: v.dataset.k, dur: +v.dataset.dur || dur, col: v.closest('.vcol') }));
    if (!this.master) return;
    this.master.addEventListener('ended', () => { this.seek(0); if (this.playing) this.play(); });
    this.master.addEventListener('loadedmetadata', () => this.paint());
    this.applyEar(); this.paint();
  },
  stop() { cancelAnimationFrame(this.raf); if (this.master) { try { this.master.pause(); } catch { /* 无妨 */ } } this.cands.forEach(c => { try { c.v.pause(); } catch { /* 无妨 */ } }); this.master = null; this.cands = []; this.playing = false; },
  alive() { return this.master && this.master.isConnected; },
  play() {
    if (!this.alive()) return;
    this.playing = true;
    const t = this.master.currentTime;
    this.cands.forEach(c => { if (t < c.dur - .05) { if (Math.abs(c.v.currentTime - t) > .08) c.v.currentTime = t; c.v.play().catch(() => { }); } });
    this.master.play().catch(() => { this.playing = false; this.btn(); });
    this.btn(); cancelAnimationFrame(this.raf); this.raf = requestAnimationFrame(() => this.tick());
  },
  pause() { if (!this.alive()) { this.playing = false; return; } this.playing = false; this.master.pause(); this.cands.forEach(c => c.v.pause()); this.btn(); this.paint(); },
  toggle() { this.playing ? this.pause() : this.play(); },
  seek(t) {
    if (!this.alive()) return;
    t = clamp(t, 0, Math.max(0, this.dur - .04));
    this.master.currentTime = t;
    this.cands.forEach(c => { c.v.currentTime = Math.min(t, Math.max(0, c.dur - .04)); });
    this.paint(t);
  },
  tick() {
    if (!this.alive()) { this.playing = false; return; }
    const t = this.master.currentTime;
    this.cands.forEach(c => {
      if (t >= c.dur - .05) { if (!c.v.paused) c.v.pause(); }
      else {
        if (Math.abs(c.v.currentTime - t) > .18) c.v.currentTime = t;       // 以原片为主钟，偏了就拉回来
        if (this.playing && c.v.paused && !this.master.paused) c.v.play().catch(() => { });
      }
    });
    this.paint(t);
    if (this.playing) this.raf = requestAnimationFrame(() => this.tick());
  },
  paint(t) {
    if (!this.alive()) return;
    if (t === undefined) t = this.master.currentTime;
    const ph = $('#ph'), code = $('#tcode'), lanes = $('#lanes');
    if (ph) ph.style.left = (clamp(t / this.dur, 0, 1) * 100) + '%';
    if (code) code.textContent = tc(t) + ' / ' + tc(this.dur);
    if (lanes) { lanes.setAttribute('aria-valuenow', t.toFixed(1)); lanes.setAttribute('aria-valuetext', tc(t)); }
    this.cands.forEach(c => c.col.classList.toggle('ended', t >= c.dur - .05 && c.dur < this.dur - .2));
  },
  btn() { const b = $('#playBtn'); if (b) { b.innerHTML = ico(this.playing ? 'pause' : 'play', 'fill'); b.setAttribute('aria-label', this.playing ? '暂停' : '一起播放'); } },
  applyEar() {
    if (!this.master) return;
    const ear = S.ui.ear;
    this.master.muted = ear !== 'src';
    this.cands.forEach(c => { c.v.muted = ear !== c.id; });
    $$('#s6in .vcol').forEach(col => { const on = col.dataset.k === ear; col.classList.toggle('ear-on', on); const e = col.querySelector('.ear'); if (e) e.innerHTML = ico(on ? 'vol' : 'mute'); });
  }
};
/* 换人核对：score.faces = {A:{photo,orig,ok,frames}}；没有这个字段就什么都不显示 */
const faceList = sc => (sc && sc.faces && typeof sc.faces === 'object') ? Object.keys(sc.faces).map(id => Object.assign({ id }, sc.faces[id])) : [];
const facePct = v => Math.round(clamp(+v || 0, 0, 1) * 100) + '%';
function faceLine(sc) {
  const fs = faceList(sc); if (!fs.length) return '';
  const bad = fs.some(f => f.ok === false);
  return `<small class="${bad ? 'w' : 'g'}">${ico(bad ? 'x' : 'check')}${bad ? '人脸更像原片演员' : '人脸像你的照片'}</small>`;
}
function faceBlock(sc, p) {
  const fs = faceList(sc); if (!fs.length) return '';
  const bad = fs.some(f => f.ok === false);
  const sum = bad ? '这条的脸没换过来，看着还是原片里的演员。' : '脸换成功了，拍出来的人像你给的照片。';
  const tip = curMode(p) === 'video' ? '这条没换成功，再拍一条，或者改用「照着拍」（换人更稳）。' : '这条没换成功，再拍一条，或者换一张更清楚的正脸照。';
  return `<div class="facebox${bad ? ' bad' : ''}"><h5>换人：把拍出来的脸和你的照片比对</h5>
    <p class="fb-sum">${ico(bad ? 'x' : 'check')}<span>${sum}</span></p>
    ${fs.map(f => `<div class="fb-row">${fs.length > 1 ? `<em>人物 ${esc(f.id)}</em>` : ''}<span><b class="w">${facePct(f.photo)}</b> 像你的照片</span><span><b class="c">${facePct(f.orig)}</b> 像原片演员</span></div>`).join('')}
    ${(() => { const m = sc.faces_before && Object.keys(sc.faces_before)[0]; return m && sc.faces && sc.faces[m] ? `<p class="fb-tip">${ico('check')}锁脸前 ${facePct(sc.faces_before[m].photo)} → 锁脸后 ${facePct(sc.faces[m].photo)} 像你的照片（本机换脸，侧脸保留 AI 原样）</p>` : ''; })()}
    ${bad ? `<p class="fb-tip">${tip}</p>` : ''}</div>`;
}
const bestTake = list => list.slice().sort((a, b) => ((b.score && b.score.total) || 0) - ((a.score && a.score.total) || 0) || b.n - a.n)[0];
function curSel(p) {
  const list = okTakes(p);
  if (S.ui.sel && list.some(t => t.id === S.ui.sel)) return S.ui.sel;
  S.ui.sel = (p.chosen && list.some(t => t.id === p.chosen)) ? p.chosen : (bestTake(list) || {}).id || null;
  return S.ui.sel;
}
const srcCuts = p => p.analysis ? p.analysis.shots.slice(1).map(s => s.start) : [];
// 按当前选中的那条看有没有导出过正式版（不用 chosen 代替，也不算换脸前原版）
const exportedTake = p => { const s = curSel(p); return (p.exports || []).some(e => e.take === s && !e.raw) ? s : null; };
function s6(ph) {
  const box = $('#s6in'), p = S.p;
  const list = p ? okTakes(p) : [];
  if (!p || !list.length || !p.analysis) { if (memo('s6', 'none')) { player.stop(); box.innerHTML = ''; S.memo.s6side = ''; } return; }
  const D = (p.window && p.window.dur) || 15, sel = curSel(p), best = bestTake(list), cuts = srcCuts(p);
  const src = p.source || {}, a = (src.width || 9) / (src.height || 16), wide = a > 1;
  const c = list.length + 1;
  const hasRaw = list.some(t => t.file_raw), raw = hasRaw && S.ui.rawView;
  const key = p.id + '|' + raw + '|' + JSON.stringify(list.map(t => [t.id, t.file, t.file_raw, t.dur, t.trial, t.score, t.face_lock])) + '|' + D + '|' + (p.window && p.window.file) + '|' + JSON.stringify((p.takes || []).filter(t => t.status === 'failed').map(t => [t.id, t.error]));
  if (memo('s6', key)) {
    const cols = wide ? Math.min(c, c > 3 ? 2 : c) : Math.min(c, 5);
    const pct = t => (clamp(t / D, 0, 1) * 100) + '%';
    const vids = `<button class="vcol src" data-k="src" data-act="earSrc" aria-label="听原片的声音"><div class="frame"><video data-k="src" muted playsinline preload="auto" src="${esc(p.window.file)}"></video><span class="tag cool">原片</span><span class="ear">${ico('mute')}</span></div>
        <div class="vmeta"><strong>原片</strong><span></span><small>${tc(D)}，${cuts.length} 个切点，${p.analysis.lines.length} 句台词</small></div></button>` +
      list.map(t => {
        const sc = t.score, linesBad = sc ? sc.lines_total - sc.lines_ok : 0;
        return `<button class="vcol" data-k="${esc(t.id)}" data-act="pickTake" aria-pressed="false"><div class="frame"><video data-k="${esc(t.id)}" data-dur="${+t.dur || D}" muted playsinline preload="auto" src="${esc(raw && t.file_raw ? t.file_raw : t.file)}"></video><span class="tag warm">${raw && t.file_raw ? '换脸前 · ' : ''}第 ${t.n} 条${t.trial ? ' · 试拍 ' + (+t.dur) + ' 秒' : list.length > 1 && best && t.id === best.id ? ' · 最接近原片' : ''}</span><span class="ear">${ico('mute')}</span><div class="held">这条只拍了前 ${+t.dur} 秒</div></div>
          <div class="vmeta"><strong>第 ${t.n} 条</strong><span class="score">${sc ? Math.round(sc.total) + '<small> 分</small>' : '<small>没打分</small>'}</span>
          ${sc ? `<small class="g">${ico('film')}切点平均差 <span class="num">${(+sc.cut_mean).toFixed(2)}</span> 秒</small>
          ${sc.audio_sync ? `<small class="${sc.audio_sync.ok ? 'g' : 'w'}">${ico(sc.audio_sync.ok ? 'check' : 'alert')}${sc.audio_sync.ok ? '音轨跟原声同步' : '音轨和原声对不上，口型可能不准'}</small>` : `<small class="${linesBad ? 'w' : 'g'}">${ico(linesBad ? 'alert' : 'check')}${sc.lines_total ? (linesBad ? `台词有 ${linesBad} 句对不上` : `台词 ${sc.lines_total} 句全对`) : '没有台词要核对'}</small>`}${faceLine(sc)}` : '<small>这条还没有对比数据</small>'}</div></button>`;
      }).join('');
    const lanes = `<div class="lane src"><span>原片</span><div class="lane-t">${cuts.map(x => `<i style="left:${pct(x)}"></i>`).join('')}</div></div>` +
      list.map(t => `<div class="lane" data-k="${esc(t.id)}"><span>第 ${t.n} 条</span><div class="lane-t">${(+t.dur || D) < D - .2 ? `<em style="left:${pct(+t.dur)};right:0;background:repeating-linear-gradient(90deg,var(--s2) 0 4px,var(--bg) 4px 8px)"></em>` : ''}${((t.score && t.score.cuts) || []).filter(x => x.out != null).map(x => `<i style="left:${pct(x.out)}"></i>`).join('')}</div></div>`).join('') +
      `<div class="guides">${cuts.map(x => `<i style="left:${pct(x)}"></i>`).join('')}<b id="ph"></b></div>`;
    const lost = (p.takes || []).filter(t => t.status === 'failed').map(t => `<div class="lost">${ico('alert')}<span>第 ${t.n} 条没拍成：${esc((t.error && t.error.title) || '原因不明')}</span><button data-act="peek5">去看原因</button></div>`).join('');
    box.innerHTML = `<div class="pick" style="--a:${a.toFixed(4)};--c:${cols};--ar:${src.width || 9}/${src.height || 16}">
      <div>
        <div class="vids${!wide && c > 5 ? ' many' : ''}" id="vids">${vids}</div>
        <div class="transport">
          <div><button class="playbtn" id="playBtn" data-act="play" aria-label="一起播放">${ico('play', 'fill')}</button><div class="tcode" id="tcode"></div></div>
          <div class="lanes" id="lanes" role="slider" tabindex="0" aria-label="播放位置" aria-valuemin="0" aria-valuemax="${D}">${lanes}</div>
          <p class="lanes-tip">${list.length > 1 ? '几条一起放，' : '两边一起放，'}竖线是原片切镜头的位置，越对得齐越像。点哪个画面，就听哪个的声音；按空格播放或暂停。</p>${hasRaw ? `<button class="btn sm ghost rawsw" data-act="rawView">${raw ? '看换脸后（导出的就是这版）' : '看换脸前（AI 原版）'}</button>` : ''}
        </div>${lost}
      </div>
      <aside class="side" id="side"></aside></div>`;
    player.build(D);
    lanesBind(D);
    S.memo.s6side = '';
  }
  // 选中态：不重建视频
  $$('#s6in .vcol[data-act=pickTake]').forEach(col => { const on = col.dataset.k === sel; col.classList.toggle('sel', on); col.setAttribute('aria-pressed', on); });
  $$('#s6in .lane[data-k]').forEach(l => l.classList.toggle('sel', l.dataset.k === sel));
  const t = list.find(x => x.id === sel); if (!t) return;
  const ex = (p.exports || []).filter(e => e.take === sel && !e.raw).slice(-1)[0], exOn = exportedTake(p) === sel && ex;
  if (!memo('s6side', sel + '|' + JSON.stringify([t.score, t.face_lock, t.file_raw, exOn && ex, list.length, t.trial, p.mode, p.analysis.lines.map(l => l.new)]))) return;
  const sc = t.score;
  const rel = u => { try { return decodeURIComponent(String(u).split('/files/')[1].split('/').slice(1).join('\\')); } catch { return String(u || ''); } };
  let why = '这条还没有和原片对比的数据，先自己看一遍。';
  if (sc) {
    const cs = (sc.cuts || []).filter(x => x.diff != null), worst = cs.slice().sort((x, y) => Math.abs(y.diff) - Math.abs(x.diff))[0];
    const parts = [];
    if (cs.length) parts.push(Math.abs(worst.diff) <= .2 ? `${cs.length} 个切点都卡在 0.2 秒以内` : `切点平均差 ${(+sc.cut_mean).toFixed(2)} 秒，差得最多的是第 ${sc.cuts.indexOf(worst) + 1} 个，${worst.diff > 0 ? '晚' : '早'}了 ${Math.abs(worst.diff).toFixed(1)} 秒`);
    if (sc.missing) parts.push(`少切了 ${sc.missing} 次镜头`);
    if (sc.extra) parts.push(`多切了 ${sc.extra} 次镜头`);
    if (faceList(sc).some(f => f.ok === false)) parts.unshift('脸没换成功，还是原片演员的样子');
    if (sc.audio_sync && !sc.audio_sync.ok) parts.unshift('这条 H3 自己重新念了台词，嘴型可能和原声' + (Math.abs(sc.audio_sync.lag_ms) >= 100 ? `差 ${(Math.abs(sc.audio_sync.lag_ms) / 1000).toFixed(1)} 秒` : '对不上') + '，建议再拍一条，有说话的片子用「照着拍」更稳');
    if (sc.lines_total) parts.push(sc.lines_ok === sc.lines_total ? `${sc.lines_total} 句台词都说对了` : `${sc.lines_total - sc.lines_ok} 句台词和你写的对不上`);
    why = parts.length ? parts.join('，') + '。' : '';
  }
  $('#side').innerHTML = `${exOn ? `<div class="done-box"><h4>${ico('check')}已导出</h4><button class="btn sm" data-act="openFolder">${ico('folder')}打开文件夹</button><ul><li>${esc(rel(ex.mp4))}</li>${ex.srt ? `<li>${esc(rel(ex.srt))}</li>` : ''}</ul><p>原画质导出，画面上不加任何水印。发布时按平台要求勾选「AI 生成内容」声明。</p></div>` : ''}
    <h3>第 ${t.n} 条${sc ? ` <span class="num">${Math.round(sc.total)}</span><span class="hint">节奏还原分</span>` : ''}${t.trial ? ' <span class="tag mute">试拍</span>' : ''}</h3>
    ${why ? `<p class="why">${esc(why)}</p>` : ''}
    ${t.face_lock && t.face_lock.error ? `<div class="facebox bad"><h5>锁脸</h5><p class="fb-sum">${ico('alert')}<span>${esc(t.face_lock.error)}</span></p><button class="btn sm" data-act="relock">${ico('refresh')}重新锁脸（不花钱）</button></div>` : ''}
    ${sc ? `<div class="side-t">
    ${faceBlock(sc, p)}
    ${sc.cuts && sc.cuts.length ? `<table class="cmp"><caption>切点：镜头在第几秒切换</caption>${sc.cuts.map((x, i) => `<tr><td>第 ${i + 1} 个</td><td><span class="c">${x.src != null ? (+x.src).toFixed(1) : '—'}</span> <span class="hint">原片</span></td><td><span class="w">${x.out != null ? (+x.out).toFixed(1) : '—'}</span> <span class="hint">这条</span></td><td class="${x.diff == null || Math.abs(x.diff) > .5 ? 'x' : ''}">${x.diff == null ? '没切' : '差 ' + Math.abs(x.diff).toFixed(1) + ' 秒'}</td></tr>`).join('')}</table>` : ''}
    ${sc.lines && sc.lines.length ? `<table class="cmp"><caption>台词：把拍出来的话听写下来核对</caption>${sc.lines.map(l => `<tr><td>${esc(l.text)}</td><td class="${l.ok ? 'v' : 'x'}">${l.ok ? ico('check') + ' 对' : `有出入${l.match != null ? '，像 ' + Math.round(l.match * 100) + '%' : ''}`}</td></tr>`).join('')}</table>` : ''}
    </div>` : ''}
    <div class="side-foot"><span class="hint">${t.trial ? '试拍满意的话，回去把「先试前几秒」关掉，拍整条。' : list.length > 1 ? '都不满意？改一下拉片表或台词，再拍一条。' : '不满意？改一下台词或照片，再拍一条。'}再拍之前还会先报价。</span><button class="btn sm" data-act="reshoot">${ico('refresh')}${t.trial ? '去拍整条' : '改一改，再拍一条'}</button>${t.file_raw ? `<button class="btn sm ghost" data-act="exportRaw">${ico('download')}导出换脸前的原版</button>` : ''}</div>`;
}
function lanesBind(D) {
  const lanes = $('#lanes'); if (!lanes) return;
  const at = e => { const g = lanes.querySelector('.guides').getBoundingClientRect(); return clamp((e.clientX - g.left) / g.width, 0, 1) * D; };
  let drag = false, was = false;
  lanes.onpointerdown = e => { drag = true; was = player.playing; if (was) player.pause(); lanes.setPointerCapture(e.pointerId); player.seek(at(e)); };
  lanes.onpointermove = e => { if (drag) player.seek(at(e)); };
  lanes.onpointerup = lanes.onpointercancel = () => { if (drag && was) player.play(); drag = false; };
  lanes.onkeydown = e => { if (!player.alive()) return; const t = player.master.currentTime; if (e.key === 'ArrowLeft') { e.preventDefault(); player.seek(t - .5); } if (e.key === 'ArrowRight') { e.preventDefault(); player.seek(t + .5); } if (e.key === 'Home') { e.preventDefault(); player.seek(0); } };
}
async function chooseTake(id) {
  const p = S.p; S.ui.sel = id; S.ui.ear = id; player.applyEar(); render();
  if (p.chosen !== id) { try { await api('POST', `/api/projects/${p.id}/choose`, { take: id }); p.chosen = id; } catch { /* 选中只是记一下，导出时会再带上 */ } }
}
async function exportTake(raw) {
  const p = S.p, id = curSel(p); if (!id || S.ui.busy.export) return;
  S.ui.busy.export = true; renderDock(phase()); player.pause();
  try {
    await api('POST', `/api/projects/${p.id}/export`, { take: id, raw: raw === true });
    S.ui.busy.export = false;
    setProject(await api('GET', `/api/projects/${p.id}`));
    toast('导出好了，文件在作品的「导出」文件夹里');
    loadList();
  } catch (e) { S.ui.busy.export = false; showError(e); renderDock(phase()); }
}
async function openFolder() { try { await api('POST', '/api/open-folder', { id: S.p.id, sub: '导出' }); } catch (e) { showError(e); } }

/* ============ 底部操作条：永远只有一个琥珀按钮 ============ */
let dockAct = null, dockSec = null;
function renderDock(ph, pulse) {
  const P = $('#dkP'), Sx = $('#dkS'), H = $('#dkH'), p = S.p, st = S.st, mock = isMock();
  let label = '', sub = '', subCn = false, icon = '', dis = false, busy = false, hint = '', bad = false, sec = '', act = null, sact = null;
  if (ph === 'empty') {
    if (S.ui.busy.upload) { label = '正在上传'; dis = busy = true; hint = '马上就好。'; }
    else { label = '选择原片'; icon = 'upload'; hint = 'MP4 或 MOV，15 秒以内最好。也可以直接把文件拖进来。'; act = () => $('#pickVideo').click(); }
  } else if (ph === 'select') {
    const W = (S.ui.trim && S.ui.trim.dur) || 15;
    label = `就用这 ${W} 秒`; hint = '选好后在你电脑上裁剪，不花钱。'; busy = dis = !!S.ui.busy.window; act = confirmWindow;
    sec = '换一条片子'; sact = newProject;
  } else if (ph === 'proc') { label = '正在本机处理'; dis = busy = true; hint = '不联网，不花钱，稍等几秒。'; }
  else if (ph === 'analyzing') { label = 'AI 正在拉片'; dis = busy = true; hint = '一般不到一分钟。可以关掉网页，回来接着看。'; }
  else if (ph === 'anaerr') { label = '再拉一次'; icon = 'refresh'; hint = '上一次拉片没做成，原因写在上面。'; bad = true; act = startAnalyze; busy = dis = !!S.ui.busy.analyze; }
  else if (ph === 'anaidle') { label = '开始拉片'; sub = mock ? '模拟，不扣费' : '最多 ¥0.05'; subCn = mock; hint = '让 AI 看一遍片子，列出每个镜头怎么拍的。'; act = startAnalyze; busy = dis = !!S.ui.busy.analyze; }
  else if (ph === 'cast') {
    const id = mainPerson(p);
    label = `选人物 ${id} 的照片`; icon = 'user'; hint = '拉片表不用改也能拍。放一张你的照片，就可以看价钱开拍了。'; act = () => pickImage(id);
    if (S.ui.busy.cast) { dis = busy = true; }
  } else if (ph === 'ready') {
    const q = activeQuote(), over = anyOver(p);
    if (okTakes(p).length) { sec = '不拍了，回去挑片'; sact = () => { S.ui.reshoot = false; render(); }; }
    if (over) { label = '有台词太长，先改短'; dis = true; bad = true; hint = `第 ${over.i} 句超了 ${lineOver(over)} 个字，删掉 ${lineOver(over)} 个就能拍。`; }
    else if (S.ui.busy.shoot) { label = '正在提交'; dis = busy = true; hint = '别关网页，几秒就好。'; }
    else if (!q && S.q.err) { label = '价钱没算出来'; dis = true; bad = true; hint = S.q.err.title + '。' + S.q.err.action; }
    else if (!q || S.q.loading || S.ui.dirtyLines.size) { label = '正在算价钱'; dis = busy = true; hint = '价钱算好才能开拍。'; }
    else if (q.blockers && q.blockers.length) { label = '还不能开拍'; dis = true; bad = true; hint = q.blockers[0].text + (q.blockers.length > 1 ? `（还有 ${q.blockers.length - 1} 处）` : ''); }
    else if (q.over_budget) { label = '超出预算，先调一下'; dis = true; bad = true; hint = `这次要 ${yuan(q.sum)}，预算只剩 ${yuan(q.budget_left)}。少拍一条、换便宜的档位，或去设置里调高上限。`; }
    else {
      icon = 'film'; act = shoot;
      const what = S.ui.trial ? `试拍前 ${+q.out_sec} 秒` : `开拍 ${q.takes} 条`;
      if (q.mock) { label = '模拟' + what; sub = '不扣费'; subCn = true; hint = `模拟模式不扣费，拍出来的是样片。真拍的话约 ${yuan(q.sum)}。`; }
      else { label = (S.ui.trial ? '先' : '确认') + what; sub = yuan(q.sum); hint = `这次约 ${yuan(q.sum)}。点了还会再问你一次，确认了才提交、才扣费。`; }
    }
  } else if (ph === 'shooting') {
    const n = (p.takes || []).filter(t => ACTIVE_ST.includes(t.status)).length;
    label = '拍摄中'; dis = busy = true; hint = `${n} 条在拍，一般几分钟一条。可以关掉网页，回来接着看。`;
  } else if (ph === 'failed') {
    label = '回去改一改，再拍'; icon = 'undo'; hint = '没拍成的原因写在卡片下面。再拍之前还会先报价。'; act = () => reshoot();
  } else if (ph === 'pick') {
    const id = curSel(p), t = okTakes(p).find(x => x.id === id);
    if (exportedTake(p) === id) { label = '打开导出文件夹'; icon = 'folder'; hint = `第 ${t.n} 条已经导出。想换一条，点上面别的片子再导出。`; act = openFolder; sec = '复刻下一条'; sact = newProject; }
    else if (t && t.trial && !S.ui.busy.export) {
      label = '试拍满意，去拍整条'; icon = 'film'; hint = '这条只拍了前 ' + (+t.dur) + ' 秒。满意就去拍整条，开拍前还会先报价。'; act = () => reshoot();
      sec = '就导出这条试拍'; sact = exportTake;
    } else {
      label = `导出第 ${t ? t.n : ''} 条`; icon = 'download'; hint = '导出原画质 MP4 和 SRT 字幕，画面不加水印，导出不花钱。'; act = exportTake;
      busy = dis = !!S.ui.busy.export; if (busy) label = '正在导出';
      sec = '不满意，再拍一条'; sact = () => reshoot();
    }
  }
  const html = (busy ? '<span class="spin"></span>' : icon ? ico(icon) : '') + esc(label) + (sub ? `<span class="sub${subCn ? ' cn' : ''}">${esc(sub)}</span>` : '');
  const changedLabel = memo('dockP', html);
  if (changedLabel) P.innerHTML = html;
  P.disabled = dis; dockAct = act;
  Sx.hidden = !sec; Sx.textContent = sec; dockSec = sact;
  H.textContent = hint; H.title = hint; H.classList.toggle('bad', bad);
  const n = ACTIVE_STEP[ph];
  $('#dkN').textContent = n + ' / 6'; $('#dkT').textContent = n === 5 && ph !== 'shooting' ? '拍摄' : NAMES[n - 1];
  if ((pulse || changedLabel) && !dis) { P.classList.remove('pulse'); void P.offsetWidth; P.classList.add('pulse'); }
}
function reshoot() { player.pause(); S.ui.reshoot = true; render(); }
async function startAnalyze() {
  const p = S.p; if (!p || S.ui.busy.analyze) return;
  S.ui.busy.analyze = true; renderDock(phase());
  try { await mutate('POST', `/api/projects/${p.id}/analyze`); } catch (e) { showError(e); }
  finally { S.ui.busy.analyze = false; render(); schedulePoll(); }
}
async function confirmWindow() {
  const p = S.p, T = S.ui.trim; if (!p || !T || S.ui.busy.window) return;
  const v = $('#trimV'); if (v) v.pause();
  S.ui.busy.window = true; renderDock(phase());
  try { await mutate('POST', `/api/projects/${p.id}/window`, { start: T.start, dur: T.dur }); }
  catch (e) { showError(e); }
  finally { S.ui.busy.window = false; render(); schedulePoll(); }
}

/* ============ 上传 ============ */
async function uploadVideo(file) {
  if (!file || S.ui.busy.upload) return;
  if (!/^video\//.test(file.type) && !/\.(mp4|mov|m4v)$/i.test(file.name)) return showError({ title: '这不是视频文件', action: '选一条 MP4 或 MOV 格式的视频。' });
  if (S.p) setProject(null);
  S.ui.busy.upload = true; render();
  const fd = new FormData(); fd.append('file', file);
  try { const p = await api('POST', '/api/projects', fd); S.ui.busy.upload = false; setProject(p); loadList(); }
  catch (e) { S.ui.busy.upload = false; showError(e); render(); }
}
async function useSample() {
  if (S.ui.busy.sample) return;
  S.ui.busy.sample = true; render();
  try { const p = await api('POST', '/api/projects/sample'); S.ui.busy.sample = false; setProject(p); loadList(); loadState(); }
  catch (e) { S.ui.busy.sample = false; showError(e); render(); }
}
let imageTarget = null;
function pickImage(target) { imageTarget = target; const i = $('#pickImage'); i.value = ''; i.click(); }

/* ============ 作品菜单 ============ */
function renderMenu() {
  const m = $('#projMenu'), cur = S.p && S.p.id;
  m.innerHTML = `<button data-act="newProject"><span class="mt">${ico('plus')}</span><span><strong>复刻新的一条</strong><small>传一条新的原片</small></span><span></span></button>` +
    (S.list.length ? '<hr>' + S.list.map(x => `<button data-act="openProject" data-id="${esc(x.id)}" class="${x.id === cur ? 'cur' : ''}"><span class="mt" style="${bg(x.thumb)}"></span><span style="min-width:0"><strong>${esc(x.name)}</strong><small>${esc(x.created || '')} · ${esc(STAGE_CN[x.status] || x.status || '')}</small></span><span class="mp">${yuan(x.spent)}</span></button>`).join('') : '<p>做过的作品会列在这里，随时回来接着弄。</p>');
}
function toggleMenu(on) {
  const m = $('#projMenu'), b = $('#projBtn');
  if (on === undefined) on = m.hidden;
  m.hidden = !on; b.setAttribute('aria-expanded', on);
  if (on) { renderMenu(); const r = b.getBoundingClientRect(); m.style.left = Math.max(12, Math.min(r.left, innerWidth - m.offsetWidth - 12)) + 'px'; loadList().then(() => { if (!m.hidden) renderMenu(); }); }
}

/* ============ 设置抽屉 ============ */
function setDrawer(on) {
  document.body.classList.toggle('set-on', on);
  const d = $('#drawer'); d.setAttribute('aria-hidden', !on); d.inert = !on;
  if (on) { S.ui.keyTest = null; S.ui.okeyTest = null; renderDrawer(true); $('#setClose').focus(); } else $('#setBtn').focus();
}
function renderDrawer(force) {
  const st = S.st, body = $('#setBody'); if (!st) return;
  if (!force && focusIn('#setBody')) return;
  const s = st.settings, kt = S.ui.keyTest, editing = S.ui.keyEdit || !st.has_key;
  const ok = S.ui.okeyTest, oediting = S.ui.okeyEdit || !st.has_okey;
  const key = JSON.stringify([st, S.ui.keyEdit, kt, S.ui.busy.key, S.ui.busy.test, S.p && S.p.spent, S.ui.okeyEdit, ok, S.ui.busy.okey, S.ui.busy.otest]);
  if (!memo('drawer', key) && !force) return;
  body.innerHTML = `
    <div class="set">
      <h3>MiniMax 密钥</h3>
      <p>只存在你电脑的「设置」文件夹里，不进作品、不进日志。这里只显示后 4 位。</p>
      ${editing ? `<div class="keyrow"><input type="password" id="keyIn" placeholder="把密钥粘贴到这里" autocomplete="off" spellcheck="false" aria-label="MiniMax 密钥"><button class="btn${S.ui.busy.key ? ' busy' : ''}" data-act="keySave">${S.ui.busy.key ? '<span class="spin"></span>' : ''}保存</button>${st.has_key ? '<button class="btn ghost" data-act="keyCancel">不换了</button>' : ''}</div>`
      : `<div class="keyrow"><div class="k">•••• ••••&nbsp;<b>${esc(st.key_tail || '')}</b></div><button class="btn${S.ui.busy.test ? ' busy' : ''}" data-act="keyTest">${S.ui.busy.test ? '<span class="spin"></span>' : ''}测试密钥</button><button class="btn ghost" data-act="keyEdit">更换</button></div>`}
      ${kt ? (kt.ok ? `<p class="after ok">${ico('check')} 密钥能用。</p>` : `<p class="after bad"><b>${esc(kt.title)}</b>${esc(kt.action)}</p>`) : `<p class="after">${st.has_key ? '「测试密钥」只查一下能不能用，不花钱。' : '还没填密钥，现在只能模拟。要「按量付费」类型的密钥。'}</p>`}
    </div>
    <div class="set">
      <h3>OpenAI 密钥（可选）</h3>
      <p>有 OpenAI 赠送额度的话填上，让 GPT 来看片写拉片表：细节更准，水印框得更全，花的是你 OpenAI 的额度。国内要开代理（系统代理）才连得上；连不上会自动改用 MiniMax，不耽误拉片。</p>
      ${oediting ? `<div class="keyrow"><input type="password" id="okeyIn" placeholder="把 sk- 开头的密钥粘贴到这里" autocomplete="off" spellcheck="false" aria-label="OpenAI 密钥"><button class="btn${S.ui.busy.okey ? ' busy' : ''}" data-act="okeySave">${S.ui.busy.okey ? '<span class="spin"></span>' : ''}保存</button>${st.has_okey ? '<button class="btn ghost" data-act="okeyCancel">不换了</button>' : ''}</div>`
      : `<div class="keyrow"><div class="k">•••• ••••&nbsp;<b>${esc(st.okey_tail || '')}</b></div><button class="btn${S.ui.busy.otest ? ' busy' : ''}" data-act="okeyTest">${S.ui.busy.otest ? '<span class="spin"></span>' : ''}测试密钥</button><button class="btn ghost" data-act="okeyEdit">更换</button></div>`}
      ${ok ? (ok.ok ? `<p class="after ok">${ico('check')} 能连上，看片会用 ${esc(ok.model)}。</p>` : `<p class="after bad"><b>${esc(ok.title)}</b>${esc(ok.action)}</p>`) : `<p class="after">${st.has_okey ? '「测试密钥」只查一下能不能连上，不花钱。' : '不填也行，默认用 MiniMax 看片。'}</p>`}
      <h3 style="margin-top:1rem">看片用</h3>
      <div class="seg" role="radiogroup" aria-label="看片用哪家" style="--n:2">${[['minimax', 'MiniMax（默认）'], ['gpt', 'GPT（你的 OpenAI 额度）']].map(([v, t]) => `<button role="radio" data-act="setVision" data-v="${v}" aria-checked="${s.vision === v}"${v === 'gpt' && !st.has_okey ? ' disabled' : ''}>${t}</button>`).join('')}</div>
    </div>
    <div class="set">
      <div class="switch"><div><h3>模拟模式</h3><p>不联网、不扣费，用样片走完整个流程。练手和录教程用。${st.has_key ? '' : '填好密钥后才能关掉。'}</p></div><button role="switch" data-act="mockSw" aria-checked="${!!st.mock}" aria-label="模拟模式"${st.has_key ? '' : ' disabled'}></button></div>
      <div class="switch"><div><h3>锁脸</h3><p>${st.face_lock && st.face_lock.available ? `拍完在本机把脸再换一遍，更像你的照片；侧脸保留 AI 原样。不花钱，${st.face_lock.gpu ? '这台电脑有 N 卡，每条约多等 1 分钟。' : '这台电脑没有 N 卡，用 CPU 处理，每条要多等几分钟到十几分钟。'}换脸模型仅限非商业用途。` : '这个版本没带换脸引擎。'}</p></div><button role="switch" data-act="lockSw" aria-checked="${!!(st.settings.face_lock && st.face_lock && st.face_lock.available)}" aria-label="锁脸"${st.face_lock && st.face_lock.available ? '' : ' disabled'}></button></div>
    </div>
    <div class="set">
      <h3>默认画质档位</h3>
      <p>每次开拍前还能再改。</p>
      <div class="seg" role="radiogroup" aria-label="默认画质档位" style="--n:${st.tiers.length}">${st.tiers.map(t => `<button role="radio" data-act="setTier" data-id="${esc(t.id)}" aria-checked="${t.id === s.tier}" title="${esc(t.model + ' · ' + t.resolution)}">${esc(t.name)}</button>`).join('')}</div>
    </div>
    <div class="set">
      <h3>默认一次拍几条</h3>
      <p>建议 1 条。拍出来没法指定「一模一样」，不满意就再拍一条。</p>
      <div class="seg" role="radiogroup" aria-label="默认一次拍几条" style="--n:4">${[1, 2, 3, 4].map(n => `<button role="radio" data-act="setTakes" data-n="${n}" aria-checked="${n === s.takes}">${n} 条</button>`).join('')}</div>
    </div>
    <div class="set">
      <h3>预算上限</h3>
      <p>每个作品累计花到这个数就拦住，开拍按钮会变灰并告诉你原因，不会悄悄超。</p>
      <div class="money"><span>¥</span><input id="budgetIn" class="num" value="${+s.budget}" inputmode="decimal" aria-label="预算上限（元）"><span class="hint">${S.p ? `这个作品已花 <span class="num">${yuan(S.p.spent)}</span>` : `累计已花 <span class="num">${yuan(st.spent_total)}</span>`}</span></div>
    </div>
    <div class="set">
      <h3>配乐</h3>
      <p>「自动」让 H3 按画面气氛自己配；「不要」只留人声和环境声，方便你后期自己加。</p>
      <div class="seg" role="radiogroup" aria-label="配乐" style="--n:2"><button role="radio" data-act="setMusic" data-v="auto" aria-checked="${s.music !== 'none'}">自动</button><button role="radio" data-act="setMusic" data-v="none" aria-checked="${s.music === 'none'}">不要</button></div>
    </div>
    <p class="about">王知风 H3 导演台 · 爆款复刻版 ${esc(st.version ? 'v' + st.version : '')}<br>作者 / 整合发布：王知风　AI 工具群：957732664　官网：huigui.ai</p>`;
}
async function saveSettings(patch, okMsg) {
  try {
    const st = await api('POST', '/api/settings', patch);
    if (st && st.settings) S.st = st; else S.st = await api('GET', '/api/state');
    if ('tier' in patch && !S.p) S.ui.tier = patch.tier;
    if ('takes' in patch && !S.p) S.ui.takes = patch.takes;
    S.memo.s1 = ''; S.q.sig = '';
    renderDrawer(true); renderBar();
    if (S.p && ('budget' in patch || 'mock' in patch || 'key' in patch)) { try { setProject(await api('GET', `/api/projects/${S.p.id}`)); } catch { render(); } } else render();
    if (okMsg) toast(okMsg);
    return true;
  } catch (e) { showError(e); renderDrawer(true); return false; }
}

/* ============ 事件 ============ */
const ACT = {
  pickVideo: () => { if (!S.ui.busy.upload) { const i = $('#pickVideo'); i.value = ''; i.click(); } },
  sample: useSample,
  trimPlay: () => { const v = $('#trimV'); if (!v) return; if (v.paused) { v.currentTime = S.ui.trim.start; v.play().catch(() => { }); } else v.pause(); },
  adv: () => { if (S.ui.adv) { clearTimeout(shotSaveT); saveShots(); } S.ui.adv = !S.ui.adv; if (document.activeElement) document.activeElement.blur(); render(); },
  pickCast: b => pickImage(b.dataset.person),
  pickScene: () => pickImage('#scene'),
  dropCast: async b => { try { await mutate('DELETE', `/api/projects/${S.p.id}/cast/${encodeURIComponent(b.dataset.person)}`); } catch (e) { showError(e); } },
  pickAngle: b => pickImage('angle:' + b.dataset.person),
  copyAnglePrompt: b => copyText(ANGLE_PROMPTS[b.dataset.k], '提示词已复制：连同主照片发给 GPT 或豆包，生成好再传回来'),
  dropAngle: async b => { try { await mutate('DELETE', `/api/projects/${S.p.id}/cast/${encodeURIComponent(b.dataset.person)}/angles/${b.dataset.i}`); } catch (e) { showError(e); } },
  dropScene: async () => { try { await mutate('DELETE', `/api/projects/${S.p.id}/scene`); } catch (e) { showError(e); } },
  lineReset: b => { const d = b.closest('.dlg'), l = S.p.analysis.lines.find(x => String(x.i) === d.dataset.line), inp = d.querySelector('input'); inp.value = l.text; onLineInput(inp); inp.focus(); },
  tier: b => { S.ui.tier = b.dataset.id; render(); },
  mode: b => setMode(b.dataset.id),
  swap: b => setSwap(b.dataset.id),
  audio: b => setAudio(b.dataset.id),
  nMinus: () => { S.ui.takes = clamp(curTakes() - 1, 1, 4); render(); },
  nPlus: () => { S.ui.takes = clamp(curTakes() + 1, 1, 4); render(); },
  requote: () => ensureQuote(true),
  promptSave: async () => {
    const p = S.p, v = $('#prompt').value; if (S.ui.busy.prompt) return;
    S.ui.busy.prompt = true; render();
    try { S.ui.promptDirty = false; await mutate('POST', `/api/projects/${p.id}/prompt`, { text: v }); toast('提示词已保存，开拍时用你改的这版'); }
    catch (e) { S.ui.promptDirty = true; showError(e); }
    finally { S.ui.busy.prompt = false; render(); }
  },
  promptReset: async () => { try { S.ui.promptDirty = false; await mutate('POST', `/api/projects/${S.p.id}/prompt`, { reset: true }); toast('已恢复成自动拼的提示词'); } catch (e) { showError(e); } },
  retry: b => retryTake(b.closest('.take').dataset.take),
  cancel: b => cancelTake(b.closest('.take').dataset.take),
  play: () => player.toggle(),
  rawView: () => { S.ui.rawView = !S.ui.rawView; render(); },
  lockSw: () => saveSettings({ face_lock: !S.st.settings.face_lock }, S.st.settings.face_lock ? '已关掉锁脸：拍完直接用 AI 原版' : '已打开锁脸：拍完在本机把脸再换一遍'),
  earSrc: () => { S.ui.ear = S.ui.ear === 'src' ? null : 'src'; player.applyEar(); },
  pickTake: (b, e) => { const id = b.dataset.k; if (e.target.closest('.ear') && S.ui.ear === id) { S.ui.ear = null; player.applyEar(); return; } chooseTake(id); },
  reshoot: () => reshoot(),
  exportRaw: () => exportTake(true),
  relock: () => takeAction(curSel(S.p), 'relock', '正在重新锁脸，好了会自动换上'),
  refinish: b => takeAction(b.closest('.take').dataset.take, 'refinish', '正在重新下载，不扣费'),
  peek5: () => { S.ui.peek.add(5); render(); setTimeout(() => $('#s5').scrollIntoView({ behavior: 'smooth', block: 'start' }), 60); },
  openFolder,
  newProject: () => { toggleMenu(false); newProject(); },
  openProject: b => { toggleMenu(false); if (!S.p || S.p.id !== b.dataset.id) openProject(b.dataset.id); },
  keyEdit: () => { S.ui.keyEdit = true; S.ui.keyTest = null; renderDrawer(true); $('#keyIn').focus(); },
  keyCancel: () => { S.ui.keyEdit = false; renderDrawer(true); },
  keySave: async () => {
    const v = $('#keyIn').value.trim();
    if (!v) { $('#keyIn').focus(); return toast('先把密钥粘贴进来'); }
    S.ui.busy.key = true; renderDrawer(true);
    const ok = await saveSettings({ key: v });
    S.ui.busy.key = false; if (ok) { S.ui.keyEdit = false; S.ui.keyTest = null; toast('密钥已保存。点「测试密钥」看看能不能用'); }
    renderDrawer(true);
  },
  keyTest: async () => {
    if (S.ui.busy.test) return;
    S.ui.busy.test = true; S.ui.keyTest = null; renderDrawer(true);
    try { await api('POST', '/api/settings/test-key'); S.ui.keyTest = { ok: true }; } catch (e) { S.ui.keyTest = e; }
    S.ui.busy.test = false; renderDrawer(true);
  },
  okeyEdit: () => { S.ui.okeyEdit = true; S.ui.okeyTest = null; renderDrawer(true); $('#okeyIn').focus(); },
  okeyCancel: () => { S.ui.okeyEdit = false; renderDrawer(true); },
  okeySave: async () => {
    const v = $('#okeyIn').value.trim();
    if (!v) { $('#okeyIn').focus(); return toast('先把 OpenAI 密钥粘贴进来'); }
    S.ui.busy.okey = true; renderDrawer(true);
    const ok = await saveSettings({ okey: v });
    S.ui.busy.okey = false; if (ok) { S.ui.okeyEdit = false; S.ui.okeyTest = null; toast('已保存，以后用 GPT 看片。点「测试密钥」看看能不能连上'); }
    renderDrawer(true);
  },
  okeyTest: async () => {
    if (S.ui.busy.otest) return;
    S.ui.busy.otest = true; S.ui.okeyTest = null; renderDrawer(true);
    try { const r = await api('POST', '/api/settings/test-okey'); S.ui.okeyTest = { ok: true, model: r.model }; } catch (e) { S.ui.okeyTest = e; }
    S.ui.busy.otest = false; renderDrawer(true);
  },
  setVision: b => saveSettings({ vision: b.dataset.v }, b.dataset.v === 'gpt' ? '以后用 GPT 看片（你的 OpenAI 额度）' : '以后用 MiniMax 看片'),
  mockSw: () => saveSettings({ mock: !S.st.mock }, S.st.mock ? '已切到真拍：开拍会扣费，每次都会先问你' : '已切到模拟模式，不扣费'),
  setTier: b => { S.ui.tier = b.dataset.id; saveSettings({ tier: b.dataset.id }); },
  setTakes: b => { S.ui.takes = +b.dataset.n; saveSettings({ takes: +b.dataset.n }); },
  setMusic: b => saveSettings({ music: b.dataset.v })
};
document.addEventListener('click', e => {
  const b = e.target.closest('[data-act]');
  if (b && !b.disabled && !b.classList.contains('busy')) { ACT[b.dataset.act] && ACT[b.dataset.act](b, e); }
  if (!e.target.closest('#projMenu') && !e.target.closest('#projBtn')) toggleMenu(false);
});
document.addEventListener('input', e => {
  const el = e.target, k = el.dataset && el.dataset.in;
  if (k === 'line') onLineInput(el);
  else if (k === 'desc') onDescInput(el);
  else if (k === 'prompt') { if (!S.ui.promptDirty) { S.ui.promptDirty = true; const b = $('[data-act=promptSave]'); if (b) b.disabled = false; } }
  else if (el.closest && el.closest('#shots') && el.dataset.f === 'action') onShotEdit(el);
});
document.addEventListener('change', e => {
  const el = e.target, k = el.dataset && el.dataset.in;
  if (k === 'autoAnalyze') saveSettings({ auto_analyze: el.checked });
  else if (k === 'trial') { S.ui.trial = el.checked; render(); }
  else if (el.id === 'budgetIn') { const v = parseFloat(el.value); if (v > 0 && isFinite(v)) saveSettings({ budget: Math.round(v * 100) / 100 }, `预算上限改成 ¥${Math.round(v * 100) / 100}`); else { el.value = S.st.settings.budget; toast('预算要填一个大于 0 的数'); } }
  else if (el.closest && el.closest('#shots') && el.tagName === 'SELECT') onShotEdit(el);
});
document.addEventListener('focusout', e => { if (e.target.closest && e.target.closest('#shots,#s3in,#promptFold,#setBody')) setTimeout(() => { if (S.p) render(); }, 0); });
document.addEventListener('mouseover', e => { const el = e.target.closest && e.target.closest('[data-shot]'); hotShot(el ? el.dataset.shot : null); });
let hot = null;
function hotShot(i) { if (i === hot) return; hot = i; $$('#s2in [data-shot]').forEach(el => el.classList.toggle('hot', el.dataset.shot === i)); }
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { if (document.body.classList.contains('set-on')) setDrawer(false); toggleMenu(false); }
  if (e.key === 'Enter' && e.target.id === 'drop') ACT.pickVideo();
  if (e.key === 'Enter' && e.target.id === 'keyIn') ACT.keySave();
  if (e.key === 'Enter' && e.target.id === 'budgetIn') e.target.blur();
  if (e.code === 'Space' && S.phase === 'pick' && !$('#ask').open && !/INPUT|TEXTAREA|SELECT|BUTTON|SUMMARY/.test(document.activeElement.tagName)) { e.preventDefault(); player.toggle(); }
});
$('#dkP').onclick = () => { if (dockAct) dockAct(); };
$('#dkS').onclick = () => { if (dockSec) dockSec(); };
$('#projBtn').onclick = () => toggleMenu();
$('#setBtn').onclick = () => setDrawer(true);
$('#setClose').onclick = $('#scrim').onclick = () => setDrawer(false);
$('#pickVideo').onchange = e => uploadVideo(e.target.files[0]);
$('#pickImage').onchange = e => { if (imageTarget) uploadImage(e.target.files[0], imageTarget); };
$$('.step-head').forEach((h, i) => h.onclick = () => { const s = h.parentElement; if (s.dataset.s !== 'done') return; S.ui.peek.has(i + 1) ? S.ui.peek.delete(i + 1) : S.ui.peek.add(i + 1); renderSteps(phase()); });

/* 拖放：空状态下整页都能接原片；照片拖到人物框里 */
let dragDepth = 0;
const hasFiles = e => e.dataTransfer && [...(e.dataTransfer.types || [])].includes('Files');
const slotAt = e => e.target.closest && e.target.closest('.slot');
window.addEventListener('dragenter', e => { if (!hasFiles(e)) return; e.preventDefault(); dragDepth++; if (S.phase === 'empty') $('#dropveil').hidden = false; });
window.addEventListener('dragover', e => { if (!hasFiles(e)) return; e.preventDefault(); const s = slotAt(e); $$('.slot.over').forEach(x => x !== s && x.classList.remove('over')); if (s) s.classList.add('over'); e.dataTransfer.dropEffect = (S.phase === 'empty' || s) ? 'copy' : 'none'; });
window.addEventListener('dragleave', e => { if (!hasFiles(e)) return; dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) { $('#dropveil').hidden = true; $$('.slot.over').forEach(x => x.classList.remove('over')); } });
window.addEventListener('drop', e => {
  if (!hasFiles(e)) return; e.preventDefault(); dragDepth = 0; $('#dropveil').hidden = true;
  const f = e.dataTransfer.files[0], s = slotAt(e); $$('.slot.over').forEach(x => x.classList.remove('over'));
  if (s) return uploadImage(f, s.dataset.act === 'pickScene' ? '#scene' : s.dataset.person);
  if (S.phase === 'empty') uploadVideo(f);
});
document.addEventListener('visibilitychange', () => { if (!document.hidden && S.p && ['proc', 'analyzing', 'shooting'].includes(phase())) { pollFail = 0; schedulePoll(); } });

/* ============ 启动 ============ */
(async function boot() {
  hydrateIcons();
  render();
  try { S.st = await api('GET', '/api/state'); } catch (e) { showError(e); }
  if (S.st) { S.ui.tier = S.st.settings.tier; S.ui.takes = S.st.settings.takes; }
  await loadList();
  S.memo = {};
  const last = store.get('h3dt.last');
  const pick = S.list.find(x => x.id === last) || S.list[0];
  if (pick) await openProject(pick.id); else render();
  renderDrawer(true);
})();
})();

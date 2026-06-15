/* === Theme Switcher === */
const THEMES = [
  {key:'default', label:'紫夜', icon:'🟣'},
  {key:'ocean', label:'深海', icon:'🔵'},
  {key:'forest', label:'森林', icon:'🟢'},
  {key:'ember', label:'余烬', icon:'🔴'},
];

function initTheme() {
  const saved = localStorage.getItem('nw-theme') || 'default';
  applyTheme(saved);
  injectThemeUI();
}

function applyTheme(key) {
  document.documentElement.setAttribute('data-theme', key);
  localStorage.setItem('nw-theme', key);
}

function injectThemeUI() {
  const targets = document.querySelectorAll('.theme-switcher-wrap');
  const current = localStorage.getItem('nw-theme') || 'default';
  targets.forEach(el => {
    el.innerHTML = `<div class="theme-switcher">
      <button class="theme-btn" onclick="toggleThemeMenu(this)" title="切换主题">🎨</button>
      <div class="theme-menu" id="themeMenu">
        ${THEMES.map(t => `<button class="theme-opt${t.key === current ? ' active' : ''}" data-key="${t.key}" onclick="selectTheme('${t.key}', this)">${t.icon} ${t.label}</button>`).join('')}
      </div>
    </div>`;
  });
  document.addEventListener('click', function _close(e) {
    const m = document.getElementById('themeMenu');
    if (m && !e.target.closest('.theme-switcher')) m.classList.remove('show');
  });
}

function toggleThemeMenu(btn) {
  const m = document.getElementById('themeMenu');
  if (m) m.classList.toggle('show');
}

function selectTheme(key, btn) {
  applyTheme(key);
  document.querySelectorAll('.theme-opt').forEach(o => o.classList.remove('active'));
  btn.classList.add('active');
  const m = document.getElementById('themeMenu');
  if (m) m.classList.remove('show');
}

/* === Back to Top === */
function initBackTop() {
  const btn = document.getElementById('backTop');
  if (!btn) return;
  const toggle = () => btn.classList.toggle('show', window.scrollY > 300);
  window.addEventListener('scroll', toggle, {passive:true});
  btn.addEventListener('click', () => window.scrollTo({top:0, behavior:'smooth'}));
}

/* === Lightbox === */
function initLightbox() {
  let lb = document.getElementById('nwLightbox');
  if (!lb) {
    lb = document.createElement('div');
    lb.id = 'nwLightbox';
    lb.className = 'lightbox';
    lb.innerHTML = '<button class="close-lb" onclick="closeLightbox()">✕</button><img id="lbImg" src="">';
    lb.addEventListener('click', function(e) { if (e.target === this) closeLightbox(); });
    document.body.appendChild(lb);
  }
  document.addEventListener('click', function(e) {
    const img = e.target.closest('.lightbox-trigger');
    if (img) { e.preventDefault(); openLightbox(img.src || img.href); }
  });
}

function openLightbox(src) {
  const lb = document.getElementById('nwLightbox');
  const img = document.getElementById('lbImg');
  if (lb && img) { img.src = src; lb.classList.add('show'); }
}

function closeLightbox() {
  const lb = document.getElementById('nwLightbox');
  if (lb) lb.classList.remove('show');
}

/* === Nav User Display === */
function renderNavUser(username, role, avatar) {
  const display = document.getElementById('authDisplay');
  if (!display) return;
  if (username) {
    const aHtml = avatar ? '<img src="' + avatar + '" style="width:28px;height:28px;border-radius:50%;vertical-align:middle;margin-right:4px;object-fit:cover">' : '';
    display.innerHTML = '<span data-u="' + esc(username) + '" data-r="' + (role || '用户') + '" style="cursor:pointer;display:flex;align-items:center;gap:4px">' + aHtml + '<span class="user">' + username + '</span></span>';
  } else {
    display.innerHTML = '<span class="guest">访客</span>';
  }
}

function esc(s) { return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

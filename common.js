/* === Theme System === */
const THEMES = [
  {key:'default', label:'紫夜', icon:'🟣'},
  {key:'ocean', label:'深海', icon:'🔵'},
  {key:'forest', label:'森林', icon:'🟢'},
  {key:'ember', label:'余烬', icon:'🔴'},
];

const THEME_COLORS = {
  default: {
    bg:'#2f2a48', bgCard:'rgba(42,36,64,.6)', bgCard2:'rgba(38,32,60,.5)', bgCard3:'rgba(34,28,56,.35)',
    bgCard4:'rgba(35,28,58,.45)', bgCard5:'rgba(40,34,62,.96)', bgCardHover:'rgba(45,38,68,.5)',
    border:'#484070', border2:'#4e4880', border3:'#3e3860', border4:'rgba(72,64,112,.3)',
    text:'#e4e0f0', textDim:'#9a94b8', textMuted:'#7a7498', textLight:'#c0b8d8',
    input:'#282448', inputBorder:'#484070',
    accent:'rgba(75,65,130,.55)', accentHover:'rgba(85,75,150,.65)',
    grad1:'radial-gradient(ellipse at 40% 15%, rgba(120,100,200,.15) 0%, transparent 55%)',
    grad2:'radial-gradient(ellipse at 60% 85%, rgba(90,110,190,.1) 0%, transparent 50%)',
    dot:'#5cd85c', dotShadow:'0 0 8px #5cd85c',
  },
  ocean: {
    bg:'#1a2a3a', bgCard:'rgba(22,40,60,.6)', bgCard2:'rgba(18,38,58,.5)', bgCard3:'rgba(16,32,50,.35)',
    bgCard4:'rgba(18,34,52,.45)', bgCard5:'rgba(18,34,52,.96)', bgCardHover:'rgba(25,48,72,.5)',
    border:'#2a5070', border2:'#306080', border3:'#1e4058', border4:'rgba(42,80,112,.3)',
    text:'#d8e8f0', textDim:'#88a0b8', textMuted:'#688098', textLight:'#a8c0d8',
    input:'#182838', inputBorder:'#2a5070',
    accent:'rgba(40,80,120,.5)', accentHover:'rgba(50,100,140,.6)',
    grad1:'radial-gradient(ellipse at 40% 15%, rgba(60,140,200,.15) 0%, transparent 55%)',
    grad2:'radial-gradient(ellipse at 60% 85%, rgba(40,100,160,.1) 0%, transparent 50%)',
    dot:'#50b8e0', dotShadow:'0 0 8px #50b8e0',
  },
  forest: {
    bg:'#1a2a22', bgCard:'rgba(26,42,34,.6)', bgCard2:'rgba(22,38,30,.5)', bgCard3:'rgba(20,34,28,.35)',
    bgCard4:'rgba(22,36,30,.45)', bgCard5:'rgba(20,34,28,.96)', bgCardHover:'rgba(30,52,40,.5)',
    border:'#2a5040', border2:'#306050', border3:'#1e4030', border4:'rgba(42,80,64,.3)',
    text:'#d8f0e0', textDim:'#88b898', textMuted:'#689878', textLight:'#a8d0b8',
    input:'#182820', inputBorder:'#2a5040',
    accent:'rgba(40,100,60,.5)', accentHover:'rgba(50,130,80,.6)',
    grad1:'radial-gradient(ellipse at 40% 15%, rgba(60,200,120,.15) 0%, transparent 55%)',
    grad2:'radial-gradient(ellipse at 60% 85%, rgba(40,160,90,.1) 0%, transparent 50%)',
    dot:'#60d090', dotShadow:'0 0 8px #60d090',
  },
  ember: {
    bg:'#2a1a1a', bgCard:'rgba(44,28,28,.6)', bgCard2:'rgba(40,24,24,.5)', bgCard3:'rgba(38,20,20,.35)',
    bgCard4:'rgba(40,22,22,.45)', bgCard5:'rgba(38,22,22,.96)', bgCardHover:'rgba(56,34,34,.5)',
    border:'#503030', border2:'#603838', border3:'#402020', border4:'rgba(80,48,48,.3)',
    text:'#f0d8d8', textDim:'#b88888', textMuted:'#987070', textLight:'#d0a8a8',
    input:'#281818', inputBorder:'#503030',
    accent:'rgba(120,50,30,.5)', accentHover:'rgba(150,60,40,.6)',
    grad1:'radial-gradient(ellipse at 40% 15%, rgba(200,80,60,.15) 0%, transparent 55%)',
    grad2:'radial-gradient(ellipse at 60% 85%, rgba(160,60,40,.1) 0%, transparent 50%)',
    dot:'#e08050', dotShadow:'0 0 8px #e08050',
  },
};

let themeOverrideEl = null;

function initTheme() {
  if (!themeOverrideEl) {
    themeOverrideEl = document.createElement('style');
    themeOverrideEl.id = 'nw-theme-override';
    document.head.appendChild(themeOverrideEl);
  }
  const saved = localStorage.getItem('nw-theme') || 'default';
  applyTheme(saved);
  injectThemeUI();
}

function applyTheme(key) {
  document.documentElement.setAttribute('data-theme', key);
  localStorage.setItem('nw-theme', key);
  if (themeOverrideEl) themeOverrideEl.textContent = buildThemeCSS(key);
  updateStatusDot(key);
}

function updateStatusDot(key) {
  const dot = document.getElementById('statusDot');
  if (!dot) return;
  const c = THEME_COLORS[key] || THEME_COLORS.default;
  dot.style.background = c.dot;
  dot.style.boxShadow = c.dotShadow;
}

function buildThemeCSS(key) {
  const c = THEME_COLORS[key] || THEME_COLORS.default;
  return `body {
  background: ${c.bg} !important;
  background-image: ${c.grad1}, ${c.grad2} !important;
}
.card, .top-bar, .overlay-content, .modal-box, .detail-body, .reply-form, .submit-box,
.post-item, .reply-card, .sub-item, .tech-sub, .tier-header {
  background: ${c.bgCard} !important;
  border-color: ${c.border} !important;
}
.feature, .ip-box, .badge, .uc, .msg-item, .row, .act-item {
  border-color: ${c.border} !important;
}
input, textarea, select {
  background: ${c.input} !important;
  border-color: ${c.inputBorder} !important;
  color: ${c.text} !important;
}
.uc { background: ${c.bgCard5} !important; border-color: ${c.border2} !important; }
.cat-tab, .tab, .page-btn, .btn-ghost { border-color: ${c.border} !important; color: ${c.textDim} !important; }
.cat-tab.active, .tab.active, .page-btn.active { background: ${c.accent} !important; }
.btn-primary { background: ${c.accent} !important; }
.btn-primary:hover { background: ${c.accentHover} !important; }
.feature:hover, .post-item:hover { border-color: ${c.border2} !important; }
.card-done { background: rgba(50,38,18,.4) !important; border-color: rgba(180,140,40,.3) !important; }
.card-pending { border-color: rgba(200,168,48,.35) !important; }
.card-approved { border-color: rgba(100,200,120,.35) !important; }
.card-rejected { opacity: .55; }
`;
}

function injectThemeUI() {
  const targets = document.querySelectorAll('.theme-switcher-wrap');
  const current = localStorage.getItem('nw-theme') || 'default';
  targets.forEach(el => {
    el.innerHTML = `<div class="theme-switcher">
      <button class="theme-btn" onclick="toggleThemeMenu(this)" title="切换主题">🎨 切换主题</button>
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

/* === Unread Message Badge === */
function initUnreadBadge() {
  if (!localStorage.getItem('token')) return;
  checkUnread();
  setInterval(checkUnread, 30000);
}

async function checkUnread() {
  const token = localStorage.getItem('token');
  if (!token) return;
  try {
    const r = await fetch('/api/me', {headers:{'Authorization':'Bearer ' + token}});
    const d = await r.json();
    if (!d.ok || !d.user) return;
    document.querySelectorAll('.unread-badge').forEach(el => {
      const n = d.user.unread || 0;
      el.textContent = n > 99 ? '99+' : n;
      el.style.display = n > 0 ? 'inline' : 'none';
    });
  } catch(e) {}
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

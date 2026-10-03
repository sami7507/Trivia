"""Triavia — light, professional theme. (Streamlit's own widgets are themed by .streamlit/config.toml.)"""
CSS = """
<style>
:root {
  --bg:#f5f7fb; --card:#ffffff; --border:#e2e8f0; --text:#0f172a; --soft:#475569; --muted:#64748b;
  --brand:#2563eb; --brand-dark:#1d4ed8; --violet:#7c3aed;
}
#MainMenu, footer {visibility:hidden;}
/* Streamlit's fixed top bar covered the first row of the page — remove it and pad properly */
header[data-testid="stHeader"] {display:none;}
.stApp {background:var(--bg);}
.block-container {padding-top: 1.8rem; padding-bottom: 2rem; max-width: 1100px;}
h1,h2,h3,h4 {letter-spacing:-0.02em; color:var(--text);}

/* ── App header ── */
.brandbar {display:flex; align-items:center; gap:.85rem;}
.brandbar .logo-sm {width:46px;height:46px;border-radius:13px;display:grid;place-items:center;font-size:1.5rem;
  color:#fff;background:linear-gradient(135deg,var(--brand),var(--violet));box-shadow:0 6px 16px rgba(37,99,235,.28);flex:none;}
.brandbar .name {font-size:1.55rem;font-weight:800;line-height:1.1;letter-spacing:-.02em;
  background:linear-gradient(90deg,var(--brand),var(--violet));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.brandbar .tag {color:var(--muted);font-size:.85rem;margin-top:2px;}
div[data-testid="stHorizontalBlock"]:has(#hdr-marker) {align-items:center;margin-bottom:.4rem;}
div[data-testid="stHorizontalBlock"]:has(#hdr-marker) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(#hdr-marker) div[data-testid="stMarkdownContainer"] p {margin:0 !important;}
div[data-testid="stHorizontalBlock"]:has(#hdr-marker) div[data-testid="stVerticalBlock"] {gap:0;}
.userchip {text-align:right;color:var(--soft);font-size:.92rem;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}

/* ── Welcome: brand panel (left third) + sign-in (right two thirds) ── */
div[data-testid="stHorizontalBlock"]:has(#hero-marker) {align-items:center;padding-top:.4rem;}
.brandpanel {position:relative;overflow:hidden;min-height:520px;border-radius:26px;padding:2.4rem 2rem;color:#fff;
  display:flex;flex-direction:column;justify-content:center;
  background:linear-gradient(155deg,#1e40af 0%,#4f46e5 55%,#7c3aed 100%);box-shadow:0 22px 50px rgba(79,70,229,.28);}
.brandpanel:before {content:"";position:absolute;right:-70px;top:-70px;width:240px;height:240px;border-radius:50%;background:rgba(255,255,255,.09);}
.brandpanel:after {content:"";position:absolute;left:-60px;bottom:-80px;width:220px;height:220px;border-radius:50%;background:rgba(255,255,255,.07);}
.brandpanel > * {position:relative;z-index:1;}
.bp-logo {width:120px;height:120px;border-radius:32px;display:grid;place-items:center;font-size:3.8rem;margin-bottom:1.5rem;
  background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.30);box-shadow:0 12px 30px rgba(15,23,42,.22);}
.bp-name {font-size:3.6rem;font-weight:800;letter-spacing:-.03em;line-height:1;color:#fff;}
.bp-tag {font-size:1.15rem;font-weight:600;margin-top:.7rem;color:#fff;opacity:.96;}
.bp-sub {font-size:.95rem;line-height:1.6;margin-top:.8rem;color:#fff;opacity:.85;}
.bp-pill {align-self:flex-start;margin-top:1.5rem;padding:.3rem .85rem;border-radius:999px;font-size:.8rem;font-weight:600;
  background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);color:#fff;}

/* sign-in card: the block that directly contains the marker */
div[data-testid="stVerticalBlock"]:has(> div.element-container .logincard-marker) {
  background:var(--card);border:1px solid var(--border);border-radius:20px;padding:1.7rem 1.7rem 1.3rem;
  box-shadow:0 14px 40px rgba(15,23,42,.08);}
/* Streamlit gives each field a fixed pixel width; make them fill the card's inner width instead of overflowing it */
div[data-testid="stVerticalBlock"]:has(> div.element-container .logincard-marker) > div.element-container,
div[data-testid="stVerticalBlock"]:has(> div.element-container .logincard-marker) > div.element-container > div {width:100% !important;}

.cards {display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;margin:1.8rem 0 1.2rem;}
.card {background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.1rem 1.25rem;
  box-shadow:0 1px 3px rgba(15,23,42,.05);}
.card .ic {font-size:1.5rem;} .card h4 {margin:.4rem 0 .2rem;color:var(--text);} .card p {color:var(--muted);margin:0;font-size:.92rem;}

.pill {display:inline-block;padding:.25rem .75rem;border-radius:999px;font-size:.8rem;font-weight:600;}
.pill.ok {background:#dcfce7;color:#166534;} .pill.warn {background:#fef3c7;color:#92400e;}

.result {border-radius:18px;padding:1.5rem 1.6rem;color:#fff;margin:.5rem 0 1rem;
  box-shadow:0 12px 30px rgba(15,23,42,.18);animation:pop .35s ease-out;}
.result .lvl {font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;opacity:.9;}
.result .name {font-size:2.2rem;font-weight:800;line-height:1.1;margin:.2rem 0 .5rem;}
.result .act {font-size:1rem;opacity:.96;}
.result .meta {margin-top:.8rem;display:flex;gap:1.4rem;flex-wrap:wrap;font-size:.9rem;opacity:.95;}
@keyframes pop {from{opacity:0;transform:translateY(8px) scale(.99)} to{opacity:1;transform:none}}
.override {background:#fef2f2;border:1px solid #fecaca;color:#7f1d1d;border-radius:12px;padding:.8rem 1rem;margin-bottom:1rem;font-size:.92rem;}
.flags {display:flex;gap:.5rem;flex-wrap:wrap;margin:.2rem 0 .6rem;}
.flag {padding:.25rem .8rem;border-radius:999px;font-size:.82rem;font-weight:600;background:#fee2e2;color:#b91c1c;border:1px solid #fecaca;}
.flag.none {background:#dcfce7;color:#166534;border-color:#bbf7d0;}

.or {display:flex;align-items:center;gap:.8rem;color:var(--muted);font-size:.8rem;margin:.6rem 0;}
.or:before,.or:after {content:"";flex:1;height:1px;background:var(--border);}
.disclaimer {color:var(--muted);font-size:.82rem;text-align:center;margin-top:2rem;}
div[data-testid="stForm"] {background:var(--card);border:1px solid var(--border);border-radius:16px;box-shadow:0 1px 3px rgba(15,23,42,.05);}

/* ── Footer: 5 columns. Every column is built the same way — heading, then one element per item ── */
/* (Do NOT change the column `gap`: Streamlit sizes columns assuming 1rem and a bigger gap wraps the last one.) */
div[data-testid="stHorizontalBlock"]:has(.fmark) {margin-top:2.6rem;padding-top:1.8rem;border-top:1px solid var(--border);align-items:flex-start;}
div[data-testid="stHorizontalBlock"]:has(.fmark) div[data-testid="stVerticalBlock"] {gap:.1rem;}
div[data-testid="stHorizontalBlock"]:has(.fmark) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.fmark) div[data-testid="stMarkdownContainer"] p {margin:0 !important;}
.fh {display:block;margin:0 0 .55rem;padding:0;font-size:.88rem;line-height:1.2;letter-spacing:.12em;
  text-transform:uppercase;color:var(--brand);font-weight:800;}
div[data-testid="stHorizontalBlock"]:has(.fmark) div[data-testid="stMarkdownContainer"] p.fblurb {margin:.1rem 0 1rem !important;color:var(--muted);font-size:.88rem;line-height:1.55;}
.fsocial {display:flex;gap:.5rem;flex-wrap:wrap;}
.fsocial a {padding:.28rem .8rem;border:1px solid #cbd5e1;border-radius:999px;color:var(--soft) !important;background:#fff;
  font-size:.8rem;line-height:1.4;text-decoration:none !important;transition:all .15s;}
.fsocial a:hover {border-color:var(--brand);color:var(--brand) !important;background:#eff6ff;}
a.flink {display:block;padding:.2rem 0;font-size:.88rem;line-height:1.5;color:var(--soft) !important;text-decoration:none !important;}
a.flink:hover {color:var(--brand) !important;text-decoration:underline !important;}
a.flink.hl {color:var(--brand) !important;font-weight:600;}
div[data-testid="stHorizontalBlock"]:has(.fmark) .stButton > button {
  background:transparent !important;border:none !important;box-shadow:none !important;
  padding:.2rem 0 !important;min-height:0 !important;height:auto !important;
  color:var(--soft) !important;font-size:.88rem !important;font-weight:400 !important;line-height:1.5 !important;}
div[data-testid="stHorizontalBlock"]:has(.fmark) .stButton > button p {font-size:.88rem !important;line-height:1.5 !important;text-align:left;}
div[data-testid="stHorizontalBlock"]:has(.fmark) .stButton > button:hover {color:var(--brand) !important;text-decoration:underline;}
div[data-testid="stHorizontalBlock"]:has(.fmark) .stButton > button:focus {box-shadow:none !important;}
.fsmall {color:var(--muted);font-size:.85rem;margin-top:.8rem;text-align:center;} .fsmall a {color:var(--brand);}
.fcopy {color:var(--muted);font-size:.8rem;text-align:center;margin:2rem 0 .6rem;}

/* ── Main navigation (a horizontal radio drawn as tabs, so the footer can switch sections) ── */
div[data-testid="stRadio"] div[role="radiogroup"] {gap:.2rem;border-bottom:1px solid var(--border);flex-wrap:wrap;}
div[data-testid="stRadio"] label[data-baseweb="radio"] {padding:.6rem 1rem;margin:0;cursor:pointer;
  border-bottom:3px solid transparent;border-radius:10px 10px 0 0;transition:background .15s;}
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {display:none;}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {background:rgba(37,99,235,.06);}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {border-bottom-color:var(--brand);background:rgba(37,99,235,.09);}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {color:var(--brand-dark);}
div[data-testid="stRadio"] label[data-baseweb="radio"] p {font-weight:600;font-size:.98rem;}

@media (max-width: 640px) {
  .brandbar .name {font-size:1.3rem;} .brandbar .tag {font-size:.78rem;}
  .brandpanel {min-height:0;padding:1.8rem 1.4rem;} .bp-logo {width:84px;height:84px;font-size:2.6rem;margin-bottom:1rem;}
  .bp-name {font-size:2.6rem;} .result .name {font-size:1.7rem;} .block-container{padding:1rem .8rem 3rem;}
}
</style>
"""

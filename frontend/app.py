"""
Triavia — Streamlit frontend.
Run:  streamlit run frontend/app.py      (backend must be running)
"""
import html
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

APP_NAME = "Triavia"
TAGLINE = "Smart triage support, in seconds."
NAV = ["🩺 Assess", "📊 Analytics", "🗂 History", "🔌 API", "ℹ️ About"]
PRODUCT_LINKS = ["Assess a patient", "Model analytics", "Assessment history", "API guide", "About Triavia"]

st.set_page_config(page_title=f"{APP_NAME} — AI Triage Assistant", page_icon="🩺",
                   layout="wide", initial_sidebar_state="collapsed")

import api_client as api  # after set_page_config: it may read st.secrets on import
import legal
import siteinfo
from presets import CUSTOM_LABEL, NORMAL_ADULT, PRESET_LIST, PRESETS, random_patient
from styles import CSS

AUTHOR, EMAIL = siteinfo.AUTHOR, siteinfo.EMAIL

st.markdown(CSS, unsafe_allow_html=True)

COMPLAINTS = {
    "chest_pain": "Chest pain", "shortness_of_breath": "Shortness of breath",
    "abdominal_pain": "Abdominal pain", "headache": "Headache", "fever": "Fever",
    "trauma": "Trauma / injury", "dizziness": "Dizziness", "syncope": "Fainting (syncope)",
    "palpitations": "Palpitations", "back_pain": "Back pain",
    "nausea_vomiting": "Nausea / vomiting", "laceration": "Cut / laceration",
    "fracture": "Suspected fracture", "allergic_reaction": "Allergic reaction",
    "altered_mental_status": "Confusion / altered mental status",
}
ARRIVALS = {"walk_in": "Walk-in", "ambulance": "Ambulance", "police": "Police", "helicopter": "Helicopter"}
CONSCIOUS = {"alert": "Alert", "verbal": "Responds to voice",
             "pain_response": "Responds to pain only", "unresponsive": "Unresponsive"}

DEFAULTS = NORMAL_ADULT


def init_state():
    st.session_state.setdefault("page", "welcome")
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("otp_phone", None)     # set once a code has been sent
    st.session_state.setdefault("otp_hint", None)
    st.session_state.setdefault("login_error", None)
    st.session_state.setdefault("form", dict(DEFAULTS))     # plain dict — NOT widget state
    st.session_state.setdefault("form_ver", 0)
    st.session_state.setdefault("preset_choice", CUSTOM_LABEL)
    st.session_state.setdefault("nav_choice", NAV[0])
    st.session_state.setdefault("nav_ver", 0)


# The form never relies on writing to widget keys (that can show a widget's minimum value in the browser).
# Instead every field gets `value=` from this dict, and loading new values bumps `form_ver`, which gives
# every widget a brand-new key — so the browser always starts them at exactly these values.
def form_values():
    base = dict(DEFAULTS)
    saved = st.session_state.get("form")
    if isinstance(saved, dict):
        base.update({k: v for k, v in saved.items() if k in base and v is not None})
    return base


def _load(values: dict, choice: str):
    st.session_state["form"] = {**DEFAULTS, **values}
    st.session_state["form_ver"] = st.session_state.get("form_ver", 0) + 1
    st.session_state["preset_choice"] = choice
    st.session_state["result"] = None


def apply_preset():
    choice = st.session_state[f"preset_{st.session_state['form_ver']}"]
    _load(PRESETS[choice], choice)


def apply_random():
    _load(random_patient(), CUSTOM_LABEL)


@st.cache_data(ttl=20, show_spinner=False)
def cached_health():
    return api.health()


@st.cache_data(ttl=60, show_spinner=False)
def cached_providers():
    return api.providers() or {"google": False, "mobile": True, "guest": True,
                               "sms_delivery": "console", "auth_required": True}


# ───────────────────────── Session helpers ─────────────────────────
def start_session(data):
    st.session_state.update(token=data["access_token"], user=data["user"], page="app",
                            result=None, otp_phone=None, otp_hint=None, login_error=None)
    st.rerun()


def logout(message=None):
    for k in ("token", "user", "result", "otp_phone", "otp_hint"):
        st.session_state[k] = None
    st.session_state["page"] = "welcome"
    st.session_state["login_error"] = message
    _load(DEFAULTS, CUSTOM_LABEL)
    st.session_state["nav_choice"] = NAV[0]


def call(fn, *args, **kwargs):
    """Call the API with the current user's token; sign out cleanly if the session expired."""
    try:
        return fn(*args, token=st.session_state.get("token"), **kwargs)
    except api.AuthExpired as e:
        logout(str(e))
        st.rerun()


def handle_oauth_return():
    """Google sign-in redirects back here with ?code=… (or ?auth_error=…)."""
    qp = st.query_params
    code, err = qp.get("code"), qp.get("auth_error")
    if code and not st.session_state.get("token"):
        st.query_params.clear()
        try:
            start_session(api.exchange_code(code))
        except api.ApiError as e:
            st.session_state["login_error"] = str(e)
    elif err:
        st.query_params.clear()
        st.session_state["login_error"] = err


def user_label():
    u = st.session_state.get("user") or {}
    return u.get("name") if u.get("provider") in ("google",) and u.get("name") else (
        u.get("phone_masked") or u.get("email") or u.get("name") or "Signed in")


# ───────────────────────── Welcome / sign-in screen ─────────────────────────
def login_box(prov):
    with st.container():
        st.markdown('<span class="logincard-marker"></span><h3 style="margin:0 0 .2rem">Welcome back 👋</h3>'
                    '<p style="color:#64748b;margin:0 0 .8rem">Sign in to continue to Triavia.</p>', unsafe_allow_html=True)
        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"])

        if prov.get("google"):
            st.link_button("🔵  Continue with Google", api.google_login_url(), use_container_width=True)
            st.markdown('<div class="or"><span>or</span></div>', unsafe_allow_html=True)

        # ── Mobile number + one-time code ──
        if not st.session_state.get("otp_phone"):
            phone = st.text_input("📱 Mobile number", placeholder="+91 98765 43210", key="login_phone",
                                  help="Include your country code, e.g. +91 for India, +1 for US.")
            if st.button("Send code", use_container_width=True, type="primary"):
                try:
                    res = api.request_otp(phone)
                    st.session_state["otp_phone"] = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
                    st.session_state["otp_hint"] = res
                    st.session_state["login_error"] = None
                    st.rerun()
                except api.ApiError as e:
                    st.error(str(e))
        else:
            hint = st.session_state.get("otp_hint") or {}
            st.success(f"Code sent to {st.session_state['otp_phone']}")
            if hint.get("dev_otp"):
                st.info(f"Demo mode — your code is **{hint['dev_otp']}**")
            elif hint.get("delivery") == "console":
                st.caption("Demo mode: SMS isn't configured, so the code is printed in the API console.")
            code = st.text_input("6-digit code", max_chars=6, key="login_code", placeholder="123456")
            c1, c2 = st.columns(2)
            if c1.button("Verify & sign in", type="primary", use_container_width=True):
                try:
                    start_session(api.verify_otp(st.session_state["otp_phone"], code.strip()))
                except api.ApiError as e:
                    st.error(str(e))
            if c2.button("Change number", use_container_width=True):
                st.session_state["otp_phone"] = None
                st.rerun()

        if prov.get("guest"):
            st.markdown('<div class="or"><span>or</span></div>', unsafe_allow_html=True)
            if st.button("👤  Continue as guest", use_container_width=True):
                try:
                    start_session(api.guest_login())
                except api.ApiError as e:
                    st.error(str(e))
            st.caption("Guest sessions are temporary and removed after 24 hours.")


def welcome():
    h = cached_health()
    prov = cached_providers()
    online = bool(h and h.get("status") == "ok")
    pill = ('<div class="bp-pill">● Service online</div>' if online
            else '<div class="bp-pill">● Service waking up — first request may take ~30s</div>')
    left, right = st.columns([1, 2], gap="large")
    with left:
        st.markdown(f"""
        <span id="hero-marker"></span>
        <div class="brandpanel">
          <div class="bp-logo">🩺</div>
          <div class="bp-name">{APP_NAME}</div>
          <div class="bp-tag">{TAGLINE}</div>
          <div class="bp-sub">Enter a patient's vital signs and get an instant urgency level,
             plain-language guidance and the reasons behind it.</div>
          {pill}
        </div>""", unsafe_allow_html=True)
    with right:
        _, mid, _ = st.columns([0.12, 2, 0.12])
        with mid:
            if prov.get("auth_required", True):
                login_box(prov)
            elif st.button("Start assessment  →", type="primary", use_container_width=True):
                st.session_state["page"] = "app"
                st.rerun()

    st.markdown("""
    <div class="cards">
      <div class="card"><div class="ic">⚡</div><h4>Instant result</h4><p>Four urgency levels from Non-Urgent to Resuscitation.</p></div>
      <div class="card"><div class="ic">🔍</div><h4>Explainable</h4><p>See the vitals and derived indicators that drove the decision.</p></div>
      <div class="card"><div class="ic">🛡️</div><h4>Safety net</h4><p>Clinical red-flag rules can escalate — never downgrade — the AI result.</p></div>
    </div>
    <div class="disclaimer">⚠️ Educational demo — not a medical device. Do not use for real clinical decisions.
    No patient names are collected.</div>""", unsafe_allow_html=True)
    footer()


# ───────────────────────── Assess tab ─────────────────────────
def _num(v, lo, hi):
    return max(lo, min(hi, v))


def assess_tab():
    fv, ver = form_values(), st.session_state["form_ver"]
    key = lambda name: f"f_{name}_{ver}"        # new version → brand-new widgets with fresh values
    opts = list(PRESETS)
    choice = st.session_state.get("preset_choice", CUSTOM_LABEL)
    c_pre, c_rnd = st.columns([4, 1])
    c_pre.selectbox(f"Quick start — {len(PRESET_LIST)} example patients (🟣 critical → 🟢 minor)", opts,
                    index=opts.index(choice) if choice in opts else 0, key=f"preset_{ver}", on_change=apply_preset)
    c_rnd.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
    c_rnd.button("🎲 Random patient", on_click=apply_random, use_container_width=True)

    def pick(label, options, names, name, col):
        cur = fv[name] if fv[name] in options else options[0]
        return col.selectbox(label, options, index=options.index(cur), format_func=names.get, key=key(name))

    with st.form("patient_form"):
        st.markdown("##### Patient")
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Age (years)", 1, 120, value=_num(int(fv["age"]), 1, 120), key=key("age"))
        cc = pick("Main complaint", list(COMPLAINTS), COMPLAINTS, "chief_complaint", c2)
        arr = pick("Arrival", list(ARRIVALS), ARRIVALS, "arrival_mode", c3)

        st.markdown("##### Vital signs")
        v1, v2, v3, v4 = st.columns(4)
        hr = v1.number_input("Heart rate (bpm)", 20, 300, value=_num(int(fv["heart_rate"]), 20, 300), key=key("heart_rate"))
        sbp = v2.number_input("Systolic BP (mmHg)", 40, 260, value=_num(int(fv["systolic_bp"]), 40, 260), key=key("systolic_bp"))
        dbp = v3.number_input("Diastolic BP (mmHg)", 20, 160, value=_num(int(fv["diastolic_bp"]), 20, 160), key=key("diastolic_bp"))
        temp = v4.number_input("Temperature (°C)", 34.0, 42.5, value=_num(round(float(fv["temperature"]), 1), 34.0, 42.5),
                               step=0.1, format="%.1f", key=key("temperature"))
        w1, w2, w3, w4 = st.columns(4)
        rr = w1.number_input("Resp. rate (/min)", 5, 60, value=_num(int(fv["respiratory_rate"]), 5, 60), key=key("respiratory_rate"))
        spo2 = w2.number_input("SpO₂ (%)", 50, 100, value=_num(int(fv["oxygen_saturation"]), 50, 100), key=key("oxygen_saturation"))
        pain = w3.slider("Pain (0–10)", 0, 10, value=_num(int(fv["pain_scale"]), 0, 10), key=key("pain_scale"))
        con = pick("Consciousness", list(CONSCIOUS), CONSCIOUS, "consciousness", w4)

        go_btn = st.form_submit_button("Assess urgency", type="primary", use_container_width=True)

    # values the user actually submitted (read from the widgets, not from session state)
    payload = dict(age=int(age), heart_rate=int(hr), systolic_bp=int(sbp), diastolic_bp=int(dbp),
                   temperature=round(float(temp), 1), respiratory_rate=int(rr), oxygen_saturation=int(spo2),
                   pain_scale=int(pain), chief_complaint=cc, arrival_mode=arr, consciousness=con)

    if go_btn:
        p = payload
        st.session_state["form"] = dict(payload)   # keep what was submitted when you switch sections
        if p["diastolic_bp"] >= p["systolic_bp"]:
            st.error("Diastolic BP must be lower than systolic BP.")
        else:
            try:
                with st.spinner("Analysing…"):
                    st.session_state["result"] = call(api.predict, p)
                st.session_state["result_input"] = p
            except api.ApiError as e:
                st.session_state["result"] = None
                st.error(str(e))

    if st.session_state.get("result"):
        show_result(st.session_state["result"])


CARD_TONE = {"#22c55e": "#15803d", "#f59e0b": "#c2570c", "#ef4444": "#dc2626", "#7c3aed": "#6d28d9"}


def show_result(r):
    color = html.escape(CARD_TONE.get(r["color_code"], r["color_code"]))
    st.markdown(f"""
    <div class="result" style="background:linear-gradient(135deg,{color},{color}cc)">
      <div class="lvl">Triage level {r['triage_level']} of 3</div>
      <div class="name">{html.escape(r['triage_label'])}</div>
      <div class="act">{html.escape(r['action_required'])}</div>
      <div class="meta"><span>⏱ Target wait: <b>{html.escape(r['wait_time'])}</b></span>
      <span>🎯 Model confidence: <b>{r['confidence']*100:.0f}%</b></span></div>
    </div>""", unsafe_allow_html=True)

    if r.get("safety_override"):
        items = "".join(f"<li>{html.escape(x)}</li>" for x in r["override_reasons"])
        st.markdown(f'<div class="override">🛡️ <b>Escalated by clinical safety rules</b>'
                    f'<ul style="margin:.4rem 0 0 1rem">{items}</ul></div>', unsafe_allow_html=True)

    d = r["derived_vitals"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Shock index", d["shock_index"], help="HR ÷ systolic BP. Above ~0.9 suggests shock risk.")
    m2.metric("Mean arterial pressure", f"{d['map_mmhg']} mmHg", help="Organ perfusion pressure; <65 is concerning.")
    m3.metric("Pulse pressure", f"{d['pulse_pressure']} mmHg")
    flags = [n for n, on in [("Fever", d["fever"]), ("Hypoxia", d["hypoxia"]), ("Tachycardia", d["tachycardia"])] if on]
    m4.metric("Warning flags", len(flags))
    chips = "".join(f'<span class="flag">{n}</span>' for n in flags) or '<span class="flag none">No warning flags</span>'
    st.markdown(f'<div class="flags">{chips}</div>', unsafe_allow_html=True)

    a, b = st.columns(2)
    probs = r["probabilities"]
    colors = ["#22c55e", "#f59e0b", "#ef4444", "#7c3aed"]
    fig = go.Figure(go.Bar(x=list(probs.values()), y=list(probs), orientation="h",
                           marker_color=colors, text=[f"{v*100:.0f}%" for v in probs.values()],
                           textposition="outside"))
    fig.update_layout(title="Model probability by level", template="plotly_white", height=290,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(range=[0, 1.15], tickformat=".0%"), margin=dict(l=10, r=10, t=45, b=10))
    a.plotly_chart(fig, use_container_width=True)

    ex = r.get("explanation") or []
    if ex:
        ex = sorted(ex, key=lambda e: abs(e["effect"]))          # biggest on top
        xs = [e["effect"] * 100 for e in ex]
        lo, hi = min(0, min(xs)), max(0, max(xs))
        pad = max(6.0, (hi - lo) * 0.3)                          # room for the "+23 pts" labels
        fig2 = go.Figure(go.Bar(
            x=xs, y=[f'{e["feature"]}: {e["value"]}' for e in ex], orientation="h", cliponaxis=False,
            marker_color=["#ef4444" if e["effect"] > 0 else "#22c55e" for e in ex],
            text=[f'{x:+.0f} pts' for x in xs], textposition="outside",
            hovertemplate="%{y}<br>%{x:+.1f} percentage points<extra></extra>"))
        fig2.update_layout(title="Why this result?", template="plotly_white", height=300,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           xaxis=dict(title="← lowers · raises →  (probability points)", zeroline=True,
                                      range=[lo - (pad if lo < 0 else 0), hi + pad]),
                           margin=dict(l=10, r=30, t=45, b=10))
        b.plotly_chart(fig2, use_container_width=True)
        b.caption("Each bar: how much the model's confidence in this level changes versus a normal value. "
                  "Red raises it, green lowers it.")
    else:
        b.info("All values are close to normal, so no single factor stood out.")

    report = {"result": r, "input": st.session_state.get("result_input")}
    st.download_button("⬇ Download assessment (JSON)", json.dumps(report, indent=2),
                       file_name=f"triavia_assessment_{r.get('assessment_id') or 'x'}.json",
                       mime="application/json")
    st.markdown(f'<div class="disclaimer">{html.escape(r["disclaimer"])}</div>', unsafe_allow_html=True)


# ───────────────────────── History tab ─────────────────────────
def history_tab():
    try:
        s, rows = call(api.stats), call(api.history, 100)
    except api.ApiError as e:
        st.error(str(e)); return
    c1, c2, c3 = st.columns(3)
    c1.metric("Assessments stored", s["total"])
    top = max(s["by_level"], key=s["by_level"].get) if s["by_level"] else "—"
    c2.metric("Most common level", top)
    c3.metric("Avg. confidence", f"{s['avg_confidence']*100:.0f}%" if s["avg_confidence"] else "—")
    if not rows:
        st.info("No assessments yet — run one from the Assess tab."); return
    df = pd.DataFrame(rows)
    df["chief_complaint"] = df["chief_complaint"].map(COMPLAINTS).fillna(df["chief_complaint"])
    df["confidence"] = (df["confidence"] * 100).round(0).astype(int).astype(str) + "%"
    df["safety_override"] = df["safety_override"].map({True: "🛡️ yes", False: ""})
    df = df.rename(columns={"id": "ID", "created_at": "Time (UTC)", "age": "Age",
                            "chief_complaint": "Complaint", "triage_level": "Level",
                            "triage_label": "Result", "confidence": "Confidence",
                            "safety_override": "Escalated"})
    st.dataframe(df, use_container_width=True, hide_index=True)
    with st.expander("Danger zone"):
        sure = st.checkbox("I understand this permanently deletes all stored assessments")
        if st.button("Delete all history", disabled=not sure):
            try:
                call(api.clear_history); st.success("History cleared."); st.rerun()
            except api.ApiError as e:
                st.error(str(e))
        st.divider()
        sure2 = st.checkbox("Permanently delete my account and all my data")
        if st.button("Delete my account", disabled=not sure2):
            try:
                call(api.delete_account)
                logout("Your account and data were deleted.")
                st.rerun()
            except api.ApiError as e:
                st.error(str(e))


# ───────────────────────── Analytics tab ─────────────────────────
LEVELS = ["Non-Urgent", "Semi-Urgent", "Urgent", "Resuscitation"]
LEVEL_COLORS = ["#22c55e", "#f59e0b", "#ef4444", "#7c3aed"]


def _dark(fig, h=340):
    fig.update_layout(template="plotly_white", height=h, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=45, b=10))
    return fig


def analytics_tab():
    try:
        m = call(api.metrics)
    except api.ApiError as e:
        st.warning(f"Model metrics unavailable: {e}  (run `python model/train.py`, then restart the API)")
        return

    k = st.columns(4)
    k[0].metric("🎯 Accuracy", f"{m['accuracy']:.2%}")
    k[1].metric("📐 Weighted F1", f"{m['weighted_f1']:.3f}")
    k[2].metric("⚖️ Macro F1", f"{m['macro_f1']:.3f}")
    k[3].metric("📈 ROC-AUC (OvR)", f"{m.get('roc_auc_weighted', m.get('roc_auc_ovr', 0)):.3f}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🤖 Model details")
        st.dataframe(pd.DataFrame({
            "Property": ["Type", "Trees", "Train samples", "Test samples", "CV F1 (mean ± std)", "Data"],
            "Value": [str(m.get("model_type", "—")), str(m.get("n_estimators", "—")),
                      f"{m.get('n_train', 0):,}", f"{m.get('n_test', 0):,}",
                      f"{m['cv_f1_mean']:.3f} ± {m['cv_f1_std']:.3f}", m.get("data_source", "synthetic")],
        }), hide_index=True, use_container_width=True)
    with c2:
        st.markdown("##### 📋 Per-class report")
        cr = m.get("classification_report", {})
        rows = [{"Level": lv, "Precision": round(cr[lv]["precision"], 3), "Recall": round(cr[lv]["recall"], 3),
                 "F1": round(cr[lv]["f1-score"], 3), "Support": int(cr[lv]["support"])}
                for lv in LEVELS if lv in cr]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    t1, t2, t3 = st.tabs(["Confusion matrix", "Feature importance", "Class distribution"])
    with t1:
        cm = m["confusion_matrix"]
        fig = go.Figure(go.Heatmap(z=cm, x=LEVELS, y=LEVELS, colorscale="Blues", text=cm,
                                   texttemplate="%{text}", showscale=False))
        fig.update_layout(xaxis_title="Predicted", yaxis_title="Actual", yaxis_autorange="reversed",
                          title="Confusion matrix (held-out test set)")
        st.plotly_chart(_dark(fig, 420), use_container_width=True)
    with t2:
        fi = m.get("feature_importances", [])[::-1]
        fig = go.Figure(go.Bar(x=[f["importance"] for f in fi],
                               y=[f["feature"].replace("_", " ").title() for f in fi],
                               orientation="h", marker_color="#3b82f6"))
        fig.update_layout(title="Top feature importances (Random Forest)")
        st.plotly_chart(_dark(fig, 480), use_container_width=True)
    with t3:
        cd = m.get("class_distribution", {})
        fig = go.Figure(go.Bar(x=list(cd), y=list(cd.values()), marker_color=LEVEL_COLORS,
                               text=list(cd.values()), textposition="outside"))
        fig.update_layout(title="Triage level distribution (full dataset)")
        st.plotly_chart(_dark(fig, 380), use_container_width=True)


# ───────────────────────── API tab ─────────────────────────
def api_tab():
    base = api.BACKEND_URL
    st.markdown("##### 🔌 Integrate Triavia with your own systems")
    st.markdown(f"**Base URL:** `{base}` · [Interactive docs (Swagger)]({base}/docs) · "
                f"[ReDoc]({base}/redoc)")
    st.dataframe(pd.DataFrame([
        ["POST", "/api/v1/auth/guest · /otp/request · /otp/verify", "Sign in (guest / mobile code); Google via /auth/google/login"],
        ["POST", "/api/v1/predict", "Classify a patient"],
        ["GET", "/api/v1/health", "Liveness + model/database status"],
        ["GET", "/api/v1/metrics", "Model evaluation metrics"],
        ["GET", "/api/v1/history", "Recent anonymous assessments"],
        ["GET", "/api/v1/stats", "Aggregate counts"],
        ["DELETE", "/api/v1/history", "Erase stored assessments"],
        ["POST", "/api/v1/feedback", "Send feedback (public)"],
    ], columns=["Method", "Endpoint", "Purpose"]), hide_index=True, use_container_width=True)
    st.markdown("**Python example**")
    st.code(f'''import httpx

payload = {{
    "age": 65, "heart_rate": 130, "systolic_bp": 85, "diastolic_bp": 55,
    "temperature": 39.2, "respiratory_rate": 28, "oxygen_saturation": 87,
    "pain_scale": 9, "chief_complaint": "chest_pain",
    "arrival_mode": "ambulance", "consciousness": "verbal",
}}
r = httpx.post("{base}/api/v1/predict", json=payload,
               headers={{"Authorization": "Bearer <session token>"}})   # or X-API-Key for services
result = r.json()
print(result["triage_label"], result["confidence"], result["action_required"])
''', language="python")
    st.markdown("**Sample response**")
    st.code('''{
  "triage_level": 3,
  "triage_label": "Resuscitation",
  "confidence": 0.97,
  "probabilities": {"Non-Urgent": 0.0, "Semi-Urgent": 0.0, "Urgent": 0.03, "Resuscitation": 0.97},
  "color_code": "#7c3aed",
  "action_required": "ACTIVATE RESUSCITATION TEAM — airway management, IV ×2, full monitoring",
  "wait_time": "Immediate",
  "derived_vitals": {"shock_index": 1.529, "map_mmhg": 65.0, "pulse_pressure": 30,
                     "fever": true, "hypoxia": true, "tachycardia": true},
  "top_features": [{"feature": "Shock Index", "importance": 0.0214, "rank": 1}],
  "explanation": [{"feature": "Oxygen saturation", "value": "87 %", "effect": 0.31, "direction": "raises"}],
  "safety_override": false, "override_reasons": [], "assessment_id": 1,
  "api_version": "2.0.0"
}''', language="json")


# ───────────────────────── About tab ─────────────────────────
def about_tab():
    st.markdown(f"""
### About {APP_NAME}
**The problem:** Emergency-department overcrowding delays care and worsens outcomes.
**The idea:** {APP_NAME} classifies patients into four urgency levels from vital signs, explains the
decision, and applies a transparent **clinical safety net** (e.g. SpO₂ < 85 %, unresponsive patient)
that can only *raise* the level — never lower it.

**Privacy:** no names or identifiers are collected. Only age, vitals and the result are stored, and you can delete them anytime.
**Limits:** trained on synthetic data — for education, demos and portfolios only. Not a medical device.
""")
    st.markdown("#### 🏗️ Architecture")
    st.code("""
 Browser
    │
    ▼
 Streamlit frontend  (frontend/)           ← Streamlit Cloud
    │  HTTPS + X-API-Key
    ▼
 FastAPI backend  (backend/)               ← Render
    ├─ Pydantic validation · rate limit · CORS · security headers
    ├─ PredictorService → Random Forest (model/artifacts)  + safety-net rules
    └─ SQLite (database/)  — anonymous assessment history

 Training pipeline (model/train.py):
 generate → engineer features → preprocess → Random Forest → 5-fold CV → evaluate → save
""", language=None)
    st.markdown("#### ⚙️ Tech stack")
    st.dataframe(pd.DataFrame({
        "Layer": ["ML", "Backend", "Frontend", "Database", "Deploy"],
        "Technology": ["scikit-learn · Random Forest · 5-fold stratified CV",
                       "FastAPI · Pydantic v2 · Uvicorn",
                       "Streamlit · Plotly · httpx",
                       "SQLite (stdlib sqlite3)",
                       "Backend → Render · Frontend → Streamlit Cloud"]}),
        hide_index=True, use_container_width=True)
    st.markdown("#### 🔮 Roadmap")
    st.info("**SHAP explainability** — per-prediction force plots for clinical trust.")
    st.info("**Time-series model** — sequential vitals for deterioration detection.")
    st.info("**Docker / EMR integration** — containerised on-premise deployment.")
    st.markdown(f"**Author:** {AUTHOR} · [{EMAIL}](mailto:{EMAIL})")


# ───────────────────────── Footer, navigation helpers and pop-ups ─────────────────────────
def go_nav(i: int):
    """Footer → switch section (new radio key = the browser shows exactly this section)."""
    st.session_state["nav_choice"] = NAV[i]
    st.session_state["nav_ver"] += 1
    st.session_state["page"] = "app"
    st.session_state["scroll_top"] = True


def open_dialog(name: str):
    st.session_state["_dialog"] = name


@st.experimental_dialog("Features", width="large")
def dlg_features():
    st.markdown(legal.FEATURES)


@st.experimental_dialog("Privacy Policy", width="large")
def dlg_privacy():
    st.markdown(legal.PRIVACY)


@st.experimental_dialog("Terms of Use", width="large")
def dlg_terms():
    st.markdown(legal.TERMS)


@st.experimental_dialog("Medical Disclaimer", width="large")
def dlg_disclaimer():
    st.markdown(legal.DISCLAIMER)


@st.experimental_dialog("Send feedback")
def dlg_feedback():
    st.caption("Tell me what worked and what should be better — it goes straight to the developer.")
    with st.form("feedback_form", clear_on_submit=False, border=False):
        rating = st.select_slider("How was your experience?", options=[1, 2, 3, 4, 5], value=5,
                                  format_func=lambda n: "⭐" * n)
        message = st.text_area("Your message", max_chars=2000, height=140,
                               placeholder="e.g. The explanation chart is great, but I'd love …")
        contact = st.text_input("Email (optional — only if you'd like a reply)", max_chars=200)
        sent = st.form_submit_button("Send feedback", type="primary", use_container_width=True)
    if sent:        # a form submits every field together, so nothing is lost if you click straight after typing
        if len(message.strip()) < 3:
            st.error("Please write at least a few words.")
        else:
            try:
                api.send_feedback({"message": message, "rating": rating, "contact": contact or None},
                                  st.session_state.get("token"))
                st.success("Thank you! Your feedback was sent. 💙")
            except api.ApiError as e:
                st.error(f"{e} You can also email {EMAIL}.")
    st.markdown(f'<div class="fsmall">Prefer email? <a href="mailto:{EMAIL}?subject={quote("Triavia feedback")}">'
                f'{EMAIL.replace("@", chr(0x200b) + "@")}</a></div>', unsafe_allow_html=True)


DIALOGS = {"features": dlg_features, "privacy": dlg_privacy, "terms": dlg_terms,
           "disclaimer": dlg_disclaimer, "feedback": dlg_feedback}


def _a(label: str, url: str, new_tab: bool = True, cls: str = "flink") -> str:
    tab = ' target="_blank" rel="noopener noreferrer"' if new_tab else ""
    text = html.escape(label).replace("@", "\u200b@")   # zero-width space: stops the markdown renderer auto-linking e-mail text
    return f'<a class="{cls}" href="{html.escape(url, quote=True)}"{tab}>{text}</a>'


def _head(text: str, marker: bool = False):
    st.markdown(f'<div class="fh{" fmark" if marker else ""}">{html.escape(text)}</div>', unsafe_allow_html=True)


def _link(label: str, url: str, new_tab: bool = True, hl: bool = False):
    st.markdown(_a(label, url, new_tab, "flink hl" if hl else "flink"), unsafe_allow_html=True)


def footer():
    signed = bool(st.session_state.get("token"))
    api_base = api.PUBLIC_BACKEND_URL
    mail = f"mailto:{EMAIL}?subject={quote('Triavia — hello')}"

    socials = _a("GitHub", siteinfo.GITHUB_URL, cls="") if siteinfo.GITHUB_URL else ""
    if siteinfo.LINKEDIN_URL:
        socials += _a("LinkedIn", siteinfo.LINKEDIN_URL, cls="")
    socials += _a("Email", mail, new_tab=False, cls="")

    c = st.columns([2.1, 1.1, 1.2, 1.1, 1.5])
    with c[0]:
        _head(APP_NAME, marker=True)
        st.markdown(f'<p class="fblurb">{TAGLINE} An explainable AI assistant that suggests an urgency level '
                    f'from a patient\'s vital signs.</p><div class="fsocial">{socials}</div>', unsafe_allow_html=True)
    with c[1]:
        _head("Product")
        for i, label in enumerate(PRODUCT_LINKS):
            if signed:       # switch section; before sign-in these just open the Features pop-up
                st.button(label, key=f"ft_nav_{i}", on_click=go_nav, args=(i,))
            else:
                st.button(label, key=f"ft_nav_{i}", on_click=open_dialog, args=("features",))
    with c[2]:
        _head("Developers")
        _link("API documentation", f"{api_base}/docs")
        _link("API reference (ReDoc)", f"{api_base}/redoc")
        if siteinfo.GITHUB_URL:
            _link("Source on GitHub", siteinfo.GITHUB_URL)
        _link("MIT licence", "https://opensource.org/license/mit")
    with c[3]:
        _head("Legal")
        for key, label in [("features", "Features"), ("privacy", "Privacy Policy"),
                           ("terms", "Terms of Use"), ("disclaimer", "Medical Disclaimer")]:
            st.button(label, key=f"ft_legal_{key}", on_click=open_dialog, args=(key,))
    with c[4]:
        _head("Contact")
        _link(EMAIL, mail, new_tab=False, hl=True)
        st.button("Send feedback", key="ft_feedback", on_click=open_dialog, args=("feedback",))
        if siteinfo.LINKEDIN_URL:
            _link("LinkedIn", siteinfo.LINKEDIN_URL)
        if siteinfo.GITHUB_URL:
            _link("GitHub profile", siteinfo.GITHUB_URL)

    st.markdown(f'<div class="fcopy">© 2026 {APP_NAME} · Built by {AUTHOR} · Educational demo — '
                f'not a medical device</div>', unsafe_allow_html=True)

    which = st.session_state.pop("_dialog", None)       # open the requested pop-up (once)
    if which in DIALOGS:
        DIALOGS[which]()


# ───────────────────────── Main ─────────────────────────
init_state()
handle_oauth_return()

# A stored page without a session (e.g. after sign-out) always returns to the welcome screen.
needs_login = cached_providers().get("auth_required", True) and not st.session_state["token"]
if needs_login or st.session_state["page"] == "welcome":
    st.session_state["page"] = "welcome"
    welcome()
else:
    left, mid, right = st.columns([5, 2.6, 1.4])
    left.markdown(f'''<span id="hdr-marker"></span><div class="brandbar"><div class="logo-sm">🩺</div>
        <div><div class="name">{APP_NAME}</div><div class="tag">{TAGLINE}</div></div></div>''',
                  unsafe_allow_html=True)
    if st.session_state["token"]:
        mid.markdown(f'<div class="userchip">👤 {html.escape(str(user_label()))}</div>', unsafe_allow_html=True)
        if right.button("Sign out", use_container_width=True):
            logout(); st.rerun()
    elif right.button("← Home", use_container_width=True):
        st.session_state["page"] = "welcome"; st.rerun()
    if st.session_state.pop("scroll_top", False):          # footer links jump back to the top
        components.html("""<script>
          const d = window.parent.document;
          (d.querySelector('section.main') || d.querySelector('[data-testid="stMain"]') ||
           d.querySelector('[data-testid="stAppViewContainer"]')).scrollTo({top: 0, behavior: "smooth"});
        </script>""", height=0)
    choice = st.session_state["nav_choice"]
    section = st.radio("Navigation", NAV, index=NAV.index(choice) if choice in NAV else 0, horizontal=True,
                       key=f"nav_{st.session_state['nav_ver']}", label_visibility="collapsed")
    st.session_state["nav_choice"] = section
    {"🩺 Assess": assess_tab, "📊 Analytics": analytics_tab, "🗂 History": history_tab,
     "🔌 API": api_tab, "ℹ️ About": about_tab}[section]()
    footer()

import streamlit as st
from supabase import create_client, Client
import os, json, urllib.request
from urllib.parse import quote
from dotenv import load_dotenv
from datetime import date, timedelta
import uuid

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

load_dotenv()

def _secret(key):
    try:    return st.secrets[key]
    except: return os.environ.get(key, "")

SUPABASE_URL = _secret("SUPABASE_URL")
SUPABASE_KEY = _secret("SUPABASE_ANON_KEY")
BUCKET_NAME  = "jeju-images"

FAMILY_PRESETS = ["언니", "엄마", "오빠", "나"]
CATEGORIES     = ["맛집", "놀거리", "비행기", "숙소"]
CAT_ICON       = {"맛집": "🍽️", "놀거리": "🎡", "비행기": "✈️", "숙소": "🏨"}
CAT_COLOR      = {"맛집": "#E8756A", "놀거리": "#2AB5AC", "비행기": "#4361EE", "숙소": "#27AE60"}
CAT_BG         = {"맛집": "#FFF0EF", "놀거리": "#E8FAF9", "비행기": "#EEF2FF", "숙소": "#EDFBF0"}
CUISINE_TYPES  = ["한식", "해산물", "고기구이", "중식", "일식", "양식", "분식", "카페·디저트", "기타"]
PRICE_RANGES   = ["₩ (1만원↓)", "₩₩ (1~3만원)", "₩₩₩ (3~5만원)", "₩₩₩₩ (5만원+)"]
PRICE_EST      = {"₩": 8000, "₩₩": 20000, "₩₩₩": 40000, "₩₩₩₩": 70000}
ACTIVITY_TYPES = ["자연·경관", "체험·액티비티", "관광지", "테마파크", "문화·역사", "쇼핑", "기타"]
AIRLINES       = ["제주항공", "티웨이항공", "진에어", "에어서울", "대한항공", "아시아나", "이스타항공", "에어부산", "기타"]
DEP_AIRPORTS   = ["김포(GMP)", "인천(ICN)", "김해(PUS)", "대구(TAE)", "청주(CJJ)"]
ARR_AIRPORTS   = ["제주(CJU)", "부산(PUS)", "도쿄(NRT)", "오사카(KIX)", "방콕(BKK)", "싱가포르(SIN)", "기타"]
ROOM_TYPES     = ["호텔", "펜션", "리조트", "풀빌라", "게스트하우스", "에어비앤비", "기타"]
EXPENSE_CATS   = ["교통", "숙소", "식비", "관광·체험", "쇼핑", "기타"]
STATUSES       = ["검토중", "확정", "예약완료"]
STATUS_COLOR   = {"검토중": "#E67E22", "확정": "#2AB5AC", "예약완료": "#27AE60"}
STATUS_ICON    = {"검토중": "🔍", "확정": "✅", "예약완료": "🔒"}

st.set_page_config(page_title="✈️ 여행 플래너", page_icon="✈️",
                   layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
/* ── Global ─────────────────────────────────────────────────────────────────── */
.stApp,[data-testid="stAppViewContainer"],.main { background:#ffffff !important; }
section[data-testid="stSidebar"] { background:#f8f8f8 !important; }
.main > div { padding:.4rem .8rem; }
h1,h2,h3,h4,p,span,div,label { color:#1a1a1a; }
a { color:#1a1a1a; text-decoration:underline; }
[data-testid="stHeader"] { background:#ffffff !important; }
footer,#MainMenu { visibility:hidden; }

/* ── Tabs ─────────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background:#f0f0f0; border-radius:12px; padding:4px; gap:2px;
    overflow-x:auto; scrollbar-width:none; border:none !important; }
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
.stTabs [data-baseweb="tab"] {
    border-radius:8px !important; font-size:12px !important; padding:7px 12px !important;
    font-weight:700 !important; color:#555 !important; background:transparent !important;
    border:none !important; white-space:nowrap; }
.stTabs [aria-selected="true"] {
    background:#ffffff !important; color:#000000 !important;
    box-shadow:0 1px 4px rgba(0,0,0,.15) !important; }
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display:none !important; }

/* ── Buttons ─────────────────────────────────────────────────────────────────── */
.stButton > button {
    border-radius:8px !important; font-weight:700 !important; font-size:13px !important;
    padding:7px 14px !important; border:1.5px solid #aaa !important;
    background:#ffffff !important; color:#000000 !important;
    box-shadow:none !important; }
.stButton > button:hover { border-color:#000 !important; background:#f5f5f5 !important; }
.stButton > button[kind="primary"] {
    background:#1a1a1a !important; color:#ffffff !important; border-color:#1a1a1a !important; }

/* ── CARD BOX — 각 카드에 둥근 테두리 ──────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius:18px !important;
    border:2px solid #1a1a1a !important;
    background:#ffffff !important;
    overflow:hidden !important;
    margin:8px 0 !important;
    box-shadow:none !important; }
/* 카드 내부 여백 */
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    padding:4px !important; }

/* ── Form ─────────────────────────────────────────────────────────────────────── */
div[data-testid="stForm"] {
    background:#fafafa !important; border-radius:14px !important;
    border:1.5px solid #ccc !important; }
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius:8px !important; border:1.5px solid #ccc !important;
    background:#ffffff !important; font-size:14px !important; color:#000 !important; }
.stSelectbox > div > div { border-radius:8px !important; border:1.5px solid #ccc !important; }
.stNumberInput > div > div > input {
    border-radius:8px !important; border:1.5px solid #ccc !important; color:#000 !important; }

/* ── Expander ────────────────────────────────────────────────────────────────── */
details[data-testid="stExpander"] {
    border-radius:12px !important; border:1.5px solid #ccc !important;
    background:#ffffff !important; }

/* ── Metrics ─────────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background:#f8f8f8; border-radius:12px; padding:14px; border:1.5px solid #ccc; }
[data-testid="stMetricLabel"] { font-size:12px !important; color:#444 !important; }
[data-testid="stMetricValue"] { font-size:22px !important; font-weight:800 !important; color:#000 !important; }

/* ── Chips — 모두 검정 텍스트 ─────────────────────────────────────────────── */
.chip { display:inline-block; border-radius:6px; padding:3px 10px;
    font-size:12px; font-weight:700; margin-right:4px; margin-bottom:4px;
    color:#000000 !important; border:1.5px solid #ccc; background:#f5f5f5; }
.chip-blue   { background:#e8f0ff; border-color:#99b3ff; }
.chip-green  { background:#e8f8ed; border-color:#88ccaa; }
.chip-red    { background:#ffe8e6; border-color:#ffaaaa; }
.chip-gray   { background:#f0f0f0; border-color:#cccccc; }
.chip-orange { background:#fff3e0; border-color:#ffcc88; }
.chip-teal   { background:#e0f5f3; border-color:#88cccc; }

/* ── Badge ────────────────────────────────────────────────────────────────────── */
.badge { background:#f0f0f0; color:#000000 !important; border-radius:6px;
    padding:3px 10px; font-size:12px; font-weight:700; border:1.5px solid #ccc; }

/* ── Voter chip ───────────────────────────────────────────────────────────────── */
.voter-chip { background:#f0f0f0; color:#000000 !important; border-radius:6px;
    padding:2px 9px; font-size:12px; font-weight:600; margin-right:4px;
    border:1px solid #ccc; }

/* ── Meta text ───────────────────────────────────────────────────────────────── */
.meta { font-size:12px; color:#333 !important; line-height:1.6; }

/* ── Countdown ────────────────────────────────────────────────────────────────── */
.countdown { text-align:center; background:#1a1a1a; border-radius:14px;
    padding:16px; color:#fff; margin-bottom:12px; }
.countdown .d { font-size:42px; font-weight:900; line-height:1; color:#fff; }
.countdown .sub { font-size:11px; opacity:.7; margin-top:5px; color:#fff; }

/* ── Edit box ─────────────────────────────────────────────────────────────────── */
.edit-box { background:#fafafa; border:2px dashed #ccc;
    border-radius:12px; padding:16px; margin:8px 0; }

/* ── Name gate ────────────────────────────────────────────────────────────────── */
.name-gate { text-align:center; padding:52px 20px; background:#f8f8f8;
    border-radius:20px; margin:20px 0; border:2px solid #1a1a1a; }

/* ── Schedule ────────────────────────────────────────────────────────────────── */
.sch-col { min-width:155px; flex:1; background:#f8f8f8;
    border-radius:12px; overflow:hidden; border:2px solid #1a1a1a; }
.sch-head { text-align:center; background:#1a1a1a; color:#fff; padding:10px 6px; }
.sch-item { border-left:3px solid #999; background:#fff;
    margin:6px; border-radius:0 8px 8px 0; padding:8px 10px; color:#000; }

/* ── Radio buttons ───────────────────────────────────────────────────────────── */
.stRadio label { color:#000 !important; font-weight:600 !important; }

/* ── Mobile responsive ───────────────────────────────────────────────────────── */
@media (max-width: 640px) {
    .main > div { padding:.2rem .4rem !important; }
    /* Tabs smaller on phone */
    .stTabs [data-baseweb="tab"] {
        font-size:11px !important; padding:6px 9px !important; }
    /* Card title */
    .card-title { font-size:14px !important; }
    /* Smaller meta text */
    .meta { font-size:11px !important; }
    /* Chip smaller */
    .chip { font-size:11px !important; padding:2px 7px !important; }
    .badge { font-size:11px !important; padding:2px 7px !important; }
    /* Buttons compact */
    .stButton > button {
        font-size:12px !important; padding:6px 8px !important; }
    /* Metrics smaller */
    [data-testid="stMetricValue"] { font-size:18px !important; }
    /* Radio compact */
    .stRadio label { font-size:12px !important; }
    /* Countdown */
    .countdown .d { font-size:32px !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def parse_image_paths(image_path):
    if not image_path: return []
    try:
        p = json.loads(image_path)
        return p if isinstance(p, list) else [image_path]
    except: return [image_path]

def safe_idx(lst, val, default=0):
    try: return lst.index(val)
    except: return default

def parse_date_str(s, default=date(2026, 7, 1)):
    try: return date.fromisoformat(s[:10].replace(".", "-"))
    except: return default

def status_chip(status):
    bg = {"검토중": "#fff3e0", "확정": "#e0f5f3", "예약완료": "#e8f8ed"}.get(status, "#f0f0f0")
    bd = {"검토중": "#ffcc88", "확정": "#88cccc", "예약완료": "#88ccaa"}.get(status, "#ccc")
    return f'<span class="chip" style="background:{bg};border-color:{bd};color:#000000;">{status}</span>'

@st.cache_data(ttl=3600)
def geocode_location(query):
    """Nominatim geocoding — returns (lat, lon) or None."""
    if not query or not query.strip():
        return None
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={quote(query.strip())}&format=json&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "JejuTravelPlanner/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None

# ── Supabase ───────────────────────────────────────────────────────────────────
@st.cache_resource
def init_sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_places(sb, category=None):
    q = sb.table("places").select("*").order("created_at", desc=True)
    if category: q = q.eq("category", category)
    return q.execute().data or []

def add_place(sb, payload):
    sb.table("places").insert(payload).execute()

def update_place(sb, place_id, payload):
    sb.table("places").update(payload).eq("id", place_id).execute()

def toggle_vote(sb, place_id, voter, current):
    updated = [v for v in current if v != voter] if voter in current else current + [voter]
    sb.table("places").update({"liked_by": updated}).eq("id", place_id).execute()

def delete_place(sb, place_id, image_path=None):
    if image_path:
        try: sb.storage.from_(BUCKET_NAME).remove(parse_image_paths(image_path))
        except: pass
    sb.table("places").delete().eq("id", place_id).execute()

def upload_image(sb, file_bytes, ext):
    path = f"{uuid.uuid4()}.{ext}"
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp"}.get(ext.lower(), f"image/{ext}")
    try:
        sb.storage.from_(BUCKET_NAME).upload(
            path=path, file=file_bytes,
            file_options={"content-type": mime, "upsert": "false"})
        return path
    except Exception as e:
        err = str(e)
        if "Bucket not found" in err or "bucket" in err.lower():
            st.error(f"❌ 스토리지 버킷 '{BUCKET_NAME}'이 없어요. Supabase → Storage에서 버킷을 만들어주세요. (오류: {err})")
        elif "security policy" in err.lower() or "policy" in err.lower():
            st.error(f"❌ 스토리지 권한 오류. Supabase → Storage → Policies에서 업로드 정책을 추가해주세요. (오류: {err})")
        else:
            st.error(f"❌ 이미지 업로드 실패: {err}")
        return None

def upload_images(sb, file_list):
    if not file_list: return None
    paths = [p for p in (upload_image(sb, b, e) for b, e in file_list) if p]
    if not paths: return None
    return json.dumps(paths) if len(paths) > 1 else paths[0]

def get_img_url(sb, path):
    return sb.storage.from_(BUCKET_NAME).get_public_url(path)

def get_expenses(sb):
    try: return sb.table("expenses").select("*").order("created_at").execute().data or []
    except: return []

def add_expense(sb, payload):
    try: sb.table("expenses").insert(payload).execute()
    except Exception as e: st.error(f"저장 실패: {e}")

def delete_expense(sb, eid):
    try: sb.table("expenses").delete().eq("id", eid).execute()
    except Exception as e: st.error(f"삭제 실패: {e}")

# ── Image widget ───────────────────────────────────────────────────────────────
def show_images(sb, image_path):
    paths = parse_image_paths(image_path)
    if not paths: return
    cols = st.columns(min(len(paths), 3))
    for i, p in enumerate(paths):
        with cols[i % 3]: st.image(get_img_url(sb, p), use_container_width=True)

def inline_uploader(key):
    """st.file_uploader without st.tabs — works safely inside st.form."""
    files = st.file_uploader("이미지 (여러 장)", type=["jpg","jpeg","png","webp"],
                              accept_multiple_files=True, key=key,
                              label_visibility="collapsed")
    if files:
        cols = st.columns(min(len(files), 3))
        for i, f in enumerate(files):
            with cols[i % 3]: st.image(f, use_container_width=True)
        return [(f.getvalue(), f.name.rsplit(".",1)[-1].lower() if "." in f.name else "jpg") for f in files]
    return []

# ── Card actions ───────────────────────────────────────────────────────────────
def card_actions(sb, place, my_name, show_detail=True):
    liked_by = place.get("liked_by") or []
    show_key = f"show_{place['id']}"
    edit_key = f"edit_{place['id']}"
    is_open  = st.session_state.get(show_key, False)
    is_edit  = st.session_state.get(edit_key, False)

    d          = place.get("details") or {}
    status_val = d.get("status", "검토중")
    is_owner   = place["added_by"] == my_name
    conf_lbl   = "해제" if status_val == "확정" else "확정"

    voters_html = "".join(f'<span class="voter-chip">{v}</span>' for v in liked_by)
    if voters_html:
        st.markdown(f'<div style="margin:2px 0 4px 0;">{voters_html}</div>', unsafe_allow_html=True)

    # Row 1: 좋아요 | 보기(접기) | 확정(해제)
    if show_detail:
        c_vote, c_det, c_conf = st.columns([4, 3, 3])
    else:
        c_vote, c_conf = st.columns([5, 5])
        c_det = None

    with c_vote:
        lbl = f"좋아요 {len(liked_by)}명"
        if st.button(lbl, key=f"v_{place['id']}"):
            toggle_vote(sb, place["id"], my_name, liked_by); st.rerun()

    if c_det:
        with c_det:
            if st.button("접기" if is_open else "보기", key=f"det_{place['id']}"):
                st.session_state[show_key] = not is_open; st.rerun()

    with c_conf:
        if st.button(conf_lbl, key=f"conf_{place['id']}"):
            new_s = "검토중" if status_val == "확정" else "확정"
            update_place(sb, place["id"], {"details": {**d, "status": new_s}}); st.rerun()

    # Row 2 (owner only): 수정 | 삭제
    if is_owner:
        c_edit, c_del = st.columns([5, 5])
        with c_edit:
            if st.button("취소" if is_edit else "수정", key=f"edit_btn_{place['id']}"):
                st.session_state[edit_key] = not is_edit; st.rerun()
        with c_del:
            if st.button("삭제", key=f"d_{place['id']}"):
                delete_place(sb, place["id"], place.get("image_path")); st.rerun()

    return st.session_state.get(show_key, False), st.session_state.get(edit_key, False)

# ── Edit forms ─────────────────────────────────────────────────────────────────
def edit_form_restaurant(sb, place, my_name):
    d = place.get("details") or {}
    pid = place["id"]
    st.markdown('<div class="edit-box">', unsafe_allow_html=True)
    st.markdown("**✏️ 맛집 수정**")
    with st.form(f"ef_rst_{pid}"):
        name    = st.text_input("장소 이름 *", value=place.get("name",""), key=f"en_{pid}")
        c1, c2  = st.columns(2)
        with c1: cuisine = st.selectbox("음식 종류", CUISINE_TYPES, index=safe_idx(CUISINE_TYPES, d.get("cuisine")))
        with c2: price_r = st.selectbox("가격대", PRICE_RANGES, index=safe_idx(PRICE_RANGES, next((r for r in PRICE_RANGES if r.startswith(d.get("price_range",""))), PRICE_RANGES[0])))
        c1, c2  = st.columns(2)
        with c1: status  = st.selectbox("상태", STATUSES, index=safe_idx(STATUSES, d.get("status","검토중")))
        with c2: t_day   = st.number_input("여행 몇 일차 (0=미정)", min_value=0, max_value=10, value=int(d.get("travel_day") or 0))
        hours    = st.text_input("영업시간", value=d.get("hours",""), key=f"eh_{pid}")
        location = st.text_input("위치 (동선용)", value=d.get("location","") or "", key=f"eloc_{pid}", placeholder="예: 제주 흑돈가")
        url      = st.text_input("지도 링크", value=place.get("url","") or "", key=f"eu_{pid}")
        notes    = st.text_area("메모", value=place.get("notes","") or "", height=70, key=f"eno_{pid}")
        st.caption("새 사진으로 교체할 경우에만 업로드 (비워두면 기존 유지)")
        new_imgs = inline_uploader(f"ei_rst_{pid}")
        if st.form_submit_button("💾 저장", type="primary", use_container_width=True):
            if not name.strip(): st.error("이름을 입력해주세요!"); return
            img_path = upload_images(sb, new_imgs) if new_imgs else place.get("image_path")
            new_d = {**d, "cuisine": cuisine, "price_range": price_r.split()[0],
                     "hours": hours.strip() or None, "status": status,
                     "location": location.strip() or None,
                     "travel_day": t_day if t_day else None}
            update_place(sb, pid, {"name": name.strip(), "url": url.strip() or None,
                                   "notes": notes.strip() or None, "image_path": img_path, "details": new_d})
            st.session_state[f"edit_{pid}"] = False
            st.success("✅ 수정 완료!"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def edit_form_activity(sb, place, my_name):
    d = place.get("details") or {}
    pid = place["id"]
    st.markdown('<div class="edit-box">', unsafe_allow_html=True)
    st.markdown("**✏️ 놀거리 수정**")
    with st.form(f"ef_act_{pid}"):
        name     = st.text_input("이름 *", value=place.get("name",""), key=f"ean_{pid}")
        c1, c2   = st.columns(2)
        with c1: act_type = st.selectbox("종류", ACTIVITY_TYPES, index=safe_idx(ACTIVITY_TYPES, d.get("activity_type")))
        with c2: price    = st.text_input("이용료", value=str(d["price"]) if d.get("price") else "", key=f"eap_{pid}")
        c1, c2   = st.columns(2)
        with c1: status  = st.selectbox("상태", STATUSES, index=safe_idx(STATUSES, d.get("status","검토중")))
        with c2: t_day   = st.number_input("여행 몇 일차 (0=미정)", min_value=0, max_value=10, value=int(d.get("travel_day") or 0))
        duration = st.text_input("소요 시간", value=d.get("duration","") or "", key=f"ead_{pid}")
        location = st.text_input("위치 (동선용)", value=d.get("location","") or "", key=f"elocat_{pid}", placeholder="예: 제주 만장굴")
        url      = st.text_input("링크", value=place.get("url","") or "", key=f"eau_{pid}")
        notes    = st.text_area("메모", value=place.get("notes","") or "", height=70, key=f"eano_{pid}")
        st.caption("새 사진으로 교체할 경우에만 업로드")
        new_imgs = inline_uploader(f"ei_act_{pid}")
        if st.form_submit_button("💾 저장", type="primary", use_container_width=True):
            if not name.strip(): st.error("이름을 입력해주세요!"); return
            img_path = upload_images(sb, new_imgs) if new_imgs else place.get("image_path")
            price_val = None
            try: price_val = int(price.replace(",","").replace("원","").strip())
            except: pass
            new_d = {**d, "activity_type": act_type, "price": price_val,
                     "duration": duration.strip() or None, "status": status,
                     "location": location.strip() or None,
                     "travel_day": t_day if t_day else None}
            update_place(sb, pid, {"name": name.strip(), "url": url.strip() or None,
                                   "notes": notes.strip() or None, "image_path": img_path, "details": new_d})
            st.session_state[f"edit_{pid}"] = False
            st.success("✅ 수정 완료!"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def edit_form_flight(sb, place, my_name):
    d = place.get("details") or {}
    pid = place["id"]
    st.markdown('<div class="edit-box">', unsafe_allow_html=True)
    st.markdown("**✏️ 항공편 수정**")
    with st.form(f"ef_fl_{pid}"):
        c1, c2  = st.columns(2)
        with c1: plan_no  = st.selectbox("플랜", ["플랜 1","플랜 2","플랜 3","플랜 4","플랜 5"],
                                          index=safe_idx(["플랜 1","플랜 2","플랜 3","플랜 4","플랜 5"], d.get("plan_no","플랜 1")))
        with c2: status   = st.selectbox("상태", STATUSES, index=safe_idx(STATUSES, d.get("status","검토중")))
        st.markdown("**가는 편**")
        c1, c2  = st.columns(2)
        with c1: airline  = st.selectbox("항공사", AIRLINES, index=safe_idx(AIRLINES, d.get("airline")))
        with c2: flight_no = st.text_input("편명", value=d.get("flight_no","") or "", key=f"efn_{pid}")
        c1, c2  = st.columns(2)
        with c1: dep_ap   = st.selectbox("출발지", DEP_AIRPORTS, index=safe_idx(DEP_AIRPORTS, d.get("dep_airport")))
        with c2: arr_ap   = st.selectbox("도착지", ARR_AIRPORTS, index=safe_idx(ARR_AIRPORTS, d.get("arr_airport","제주(CJU)")))
        c1, c2, c3 = st.columns(3)
        with c1: dep_date = st.date_input("출발일", value=parse_date_str(d.get("dep_date",""), date(2026,7,1)))
        with c2: dep_time = st.text_input("출발 시각", value=d.get("dep_time",""), key=f"edt_{pid}")
        with c3: arr_time = st.text_input("도착 시각", value=d.get("arr_time",""), key=f"eat_{pid}")
        price = st.text_input("가격 (1인)", value=str(d["price"]) if d.get("price") else "", key=f"ep_{pid}")
        st.markdown("---")
        st.markdown("**돌아오는 편**")
        c1, c2  = st.columns(2)
        with c1: ret_airline   = st.selectbox("복귀 항공사", AIRLINES, index=safe_idx(AIRLINES, d.get("ret_airline")))
        with c2: ret_flight_no = st.text_input("복귀 편명", value=d.get("ret_flight_no","") or "", key=f"erfn_{pid}")
        c1, c2, c3 = st.columns(3)
        with c1: ret_date     = st.date_input("복귀 출발일", value=parse_date_str(d.get("ret_date",""), date(2026,7,5)))
        with c2: ret_dep_time = st.text_input("복귀 출발 시각", value=d.get("ret_dep_time","") or "", key=f"erdt_{pid}")
        with c3: ret_arr_time = st.text_input("복귀 도착 시각", value=d.get("ret_arr_time","") or "", key=f"erat_{pid}")
        ret_price = st.text_input("복귀 가격", value=str(d["ret_price"]) if d.get("ret_price") else "", key=f"erp_{pid}")
        st.markdown("---")
        booking_url = st.text_input("예약 링크", value=d.get("booking_url","") or "", key=f"ebu_{pid}")
        notes       = st.text_area("메모", value=place.get("notes","") or "", height=60, key=f"efno_{pid}")
        if st.form_submit_button("💾 저장", type="primary", use_container_width=True):
            price_val = None
            try: price_val = int(price.replace(",","").replace("원","").strip())
            except: pass
            ret_price_val = None
            try: ret_price_val = int(ret_price.replace(",","").replace("원","").strip()) if ret_price.strip() else None
            except: pass
            new_d = {**d, "plan_no": plan_no, "status": status,
                     "airline": airline, "dep_airport": dep_ap, "arr_airport": arr_ap,
                     "flight_no": flight_no.strip() or None,
                     "dep_date": dep_date.strftime("%Y.%m.%d (%a)"),
                     "dep_time": dep_time.strip(), "arr_time": arr_time.strip(),
                     "price": price_val, "booking_url": booking_url.strip() or None,
                     "ret_airline": ret_airline, "ret_flight_no": ret_flight_no.strip() or None,
                     "ret_date": ret_date.strftime("%Y.%m.%d (%a)"),
                     "ret_dep_time": ret_dep_time.strip() or None,
                     "ret_arr_time": ret_arr_time.strip() or None,
                     "ret_price": ret_price_val}
            update_place(sb, pid, {"name": f"[{plan_no}] {airline} {dep_time.strip()} 출발",
                                   "notes": notes.strip() or None, "details": new_d})
            st.session_state[f"edit_{pid}"] = False
            st.success("✅ 수정 완료!"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def edit_form_accommodation(sb, place, my_name):
    d = place.get("details") or {}
    pid = place["id"]
    st.markdown('<div class="edit-box">', unsafe_allow_html=True)
    st.markdown("**✏️ 숙소 수정**")
    with st.form(f"ef_acc_{pid}"):
        name = st.text_input("숙소 이름 *", value=place.get("name",""), key=f"eaccn_{pid}")
        c1, c2 = st.columns(2)
        with c1: room_type   = st.selectbox("유형", ROOM_TYPES, index=safe_idx(ROOM_TYPES, d.get("room_type")))
        with c2: price_night = st.text_input("1박 가격", value=str(d["price_per_night"]) if d.get("price_per_night") else "", key=f"eaccpn_{pid}")
        c1, c2 = st.columns(2)
        with c1: check_in  = st.text_input("체크인", value=d.get("check_in","") or "", key=f"eacci_{pid}")
        with c2: check_out = st.text_input("체크아웃", value=d.get("check_out","") or "", key=f"eacco_{pid}")
        c1, c2 = st.columns(2)
        with c1: status  = st.selectbox("상태", STATUSES, index=safe_idx(STATUSES, d.get("status","검토중")))
        with c2: t_day   = st.number_input("여행 몇 일차 (0=미정)", min_value=0, max_value=10, value=int(d.get("travel_day") or 0))
        address     = st.text_input("주소 (동선용)", value=d.get("address","") or "", key=f"eacca_{pid}")
        booking_url = st.text_input("예약 링크", value=d.get("booking_url","") or "", key=f"eaccbu_{pid}")
        notes       = st.text_area("메모", value=place.get("notes","") or "", height=70, key=f"eaccno_{pid}")
        st.caption("새 사진으로 교체할 경우에만 업로드")
        new_imgs = inline_uploader(f"ei_acc_{pid}")
        if st.form_submit_button("💾 저장", type="primary", use_container_width=True):
            if not name.strip(): st.error("이름을 입력해주세요!"); return
            img_path = upload_images(sb, new_imgs) if new_imgs else place.get("image_path")
            price_val = None
            try: price_val = int(price_night.replace(",","").replace("원","").strip())
            except: pass
            new_d = {**d, "room_type": room_type, "price_per_night": price_val,
                     "check_in": check_in.strip() or None, "check_out": check_out.strip() or None,
                     "address": address.strip() or None, "booking_url": booking_url.strip() or None,
                     "status": status, "travel_day": t_day if t_day else None}
            update_place(sb, pid, {"name": name.strip(), "notes": notes.strip() or None,
                                   "image_path": img_path, "details": new_d})
            st.session_state[f"edit_{pid}"] = False
            st.success("✅ 수정 완료!"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ── Card renderers ──────────────────────────────────────────────────────────────
def _cat_label(cat):
    """작은 카테고리 텍스트 레이블."""
    c = CAT_COLOR.get(cat, "#777")
    bg = CAT_BG.get(cat, "#F5F2EE")
    labels = {"맛집": "맛집", "놀거리": "놀거리", "비행기": "항공", "숙소": "숙소"}
    label = labels.get(cat, cat)
    return (f'<span style="font-size:10px;font-weight:700;color:{c};'
            f'background:{bg};border-radius:6px;padding:2px 7px;">{label}</span>')


def card_restaurant(sb, place, my_name):
    d = place.get("details") or {}
    img_paths = parse_image_paths(place.get("image_path"))
    chips = status_chip(d.get("status","검토중"))
    if d.get("cuisine"):     chips += f' <span class="chip chip-blue">{d["cuisine"]}</span>'
    if d.get("price_range"): chips += f' <span class="chip chip-red">{d["price_range"].split()[0]}</span>'
    if d.get("travel_day"):  chips += f' <span class="chip chip-gray">Day {d["travel_day"]}</span>'
    thumb = (f'<img src="{get_img_url(sb, img_paths[0])}" '
             f'style="width:60px;height:60px;object-fit:cover;border-radius:10px;'
             f'flex-shrink:0;border:1px solid #ddd;">') if img_paths else ""
    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:10px;padding:4px 2px 8px;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">'
            f'<span class="card-title" style="font-size:16px;font-weight:800;color:#000000;">{place["name"]}</span>'
            f'<span class="badge" style="flex-shrink:0;">{place["added_by"]}</span></div>'
            f'<div>{chips}</div></div>'
            f'{thumb}</div>',
            unsafe_allow_html=True)
        is_open, is_edit = card_actions(sb, place, my_name)
    if is_edit:
        edit_form_restaurant(sb, place, my_name)
    elif is_open:
        if d.get("hours"):     st.markdown(f"**영업시간:** {d['hours']}")
        if place.get("url"):   st.markdown(f"[지도 보기]({place['url']})")
        if place.get("notes"): st.markdown(f"**메모:** {place['notes']}")
        if img_paths:          show_images(sb, place.get("image_path"))


def card_activity(sb, place, my_name):
    d = place.get("details") or {}
    img_paths = parse_image_paths(place.get("image_path"))
    chips = status_chip(d.get("status","검토중"))
    if d.get("activity_type"): chips += f' <span class="chip chip-teal">{d["activity_type"]}</span>'
    if d.get("price"):         chips += f' <span class="chip chip-green">{int(d["price"]):,}원</span>'
    if d.get("duration"):      chips += f' <span class="chip chip-gray">{d["duration"]}</span>'
    if d.get("travel_day"):    chips += f' <span class="chip chip-gray">Day {d["travel_day"]}</span>'
    thumb = (f'<img src="{get_img_url(sb, img_paths[0])}" '
             f'style="width:60px;height:60px;object-fit:cover;border-radius:10px;'
             f'flex-shrink:0;border:1px solid #ddd;">') if img_paths else ""
    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:10px;padding:4px 2px 8px;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">'
            f'<span class="card-title" style="font-size:16px;font-weight:800;color:#000000;">{place["name"]}</span>'
            f'<span class="badge" style="flex-shrink:0;">{place["added_by"]}</span></div>'
            f'<div>{chips}</div></div>'
            f'{thumb}</div>',
            unsafe_allow_html=True)
        is_open, is_edit = card_actions(sb, place, my_name)
    if is_edit:
        edit_form_activity(sb, place, my_name)
    elif is_open:
        if place.get("url"):   st.markdown(f"[지도/사이트]({place['url']})")
        if place.get("notes"): st.markdown(f"**메모:** {place['notes']}")
        if img_paths:          show_images(sb, place.get("image_path"))


def card_flight(sb, place, my_name):
    d         = place.get("details") or {}
    dep_ap    = d.get("dep_airport", "?")
    arr_ap    = d.get("arr_airport", "CJU")
    airline   = d.get("airline", "?")
    dep_time  = d.get("dep_time", "?")
    arr_time  = d.get("arr_time", "?")
    dep_date  = d.get("dep_date", "")
    plan_no   = d.get("plan_no", "")
    status    = d.get("status", "검토중")
    price_str = f"{int(d['price']):,}원" if d.get("price") else "-"

    plan_badge = (f'<span style="background:#1a1a1a;color:#ffffff;border-radius:6px;'
                  f'padding:3px 10px;font-size:12px;font-weight:700;margin-right:8px;">{plan_no}</span>') if plan_no else ""
    bg_s = {"검토중": "#fff3e0", "확정": "#e0f5f3", "예약완료": "#e8f8ed"}.get(status, "#f0f0f0")
    bd_s = {"검토중": "#ffcc88", "확정": "#88cccc", "예약완료": "#88ccaa"}.get(status, "#ccc")
    st_chip = f'<span class="chip" style="background:{bg_s};border-color:{bd_s};color:#000000;">{status}</span>'
    notes_preview = (place.get("notes") or "")[:30]

    html  = '<div style="padding:4px 2px 8px;">'
    html += f'<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">'
    html += f'<span style="font-size:15px;font-weight:800;color:#000000;">{plan_badge}{dep_ap} → {arr_ap}</span>'
    html += f'<span class="badge">{place["added_by"]}</span></div>'
    html += f'<div style="margin-bottom:6px;">{st_chip}'
    if notes_preview:
        html += f' <span style="font-size:12px;color:#333;">· {notes_preview}</span>'
    html += '</div>'
    html += f'<div class="meta">{airline} · {dep_time} → {arr_time}'
    if dep_date: html += f' · {dep_date}'
    html += '</div>'
    html += f'<div style="font-size:14px;font-weight:800;color:#000000;margin-top:4px;">{price_str} / 1인</div>'
    html += '</div>'

    if d.get("ret_dep_time"):
        ret_airline  = d.get("ret_airline", airline)
        ret_dep_time = d.get("ret_dep_time")
        ret_arr_time = d.get("ret_arr_time", "?")
        ret_date     = d.get("ret_date", "")
        html += f'<div style="border-top:2px solid #e0e0e0;margin-top:4px;padding-top:10px;">'
        html += f'<div style="font-size:12px;color:#333;margin-bottom:4px;">돌아오는 편 · {ret_airline}</div>'
        html += f'<div style="font-size:14px;font-weight:800;color:#000;">{arr_ap} {ret_dep_time} → {dep_ap} {ret_arr_time}</div>'
        html += f'<div class="meta">{ret_date}</div>'
        if d.get("ret_price"):
            html += f'<div style="font-size:14px;font-weight:800;color:#000;">{int(d["ret_price"]):,}원 / 1인</div>'
        html += '</div>'

    if d.get("booking_url"):
        html += f'<div style="margin-top:8px;"><a href="{d["booking_url"]}" target="_blank" style="font-size:13px;color:#000;font-weight:700;">예약 링크 보기</a></div>'

    with st.container(border=True):
        st.markdown(html, unsafe_allow_html=True)
        _, is_edit = card_actions(sb, place, my_name, show_detail=False)
    if is_edit:
        edit_form_flight(sb, place, my_name)


def card_accommodation(sb, place, my_name):
    d = place.get("details") or {}
    img_paths = parse_image_paths(place.get("image_path"))
    chips = status_chip(d.get("status","검토중"))
    if d.get("room_type"):       chips += f' <span class="chip chip-green">{d["room_type"]}</span>'
    if d.get("price_per_night"): chips += f' <span class="chip chip-red">{int(d["price_per_night"]):,}원/박</span>'
    if d.get("travel_day"):      chips += f' <span class="chip chip-gray">Day {d["travel_day"]}</span>'
    check_str = ""
    if d.get("check_in") or d.get("check_out"):
        check_str = (f'<div class="meta" style="margin-top:4px;">'
                     f'체크인 {d.get("check_in","")} · 체크아웃 {d.get("check_out","")}</div>')
    thumb = (f'<img src="{get_img_url(sb, img_paths[0])}" '
             f'style="width:60px;height:60px;object-fit:cover;border-radius:10px;'
             f'flex-shrink:0;border:1px solid #ddd;">') if img_paths else ""
    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:10px;padding:4px 2px 8px;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">'
            f'<span class="card-title" style="font-size:16px;font-weight:800;color:#000000;">{place["name"]}</span>'
            f'<span class="badge" style="flex-shrink:0;">{place["added_by"]}</span></div>'
            f'<div>{chips}</div>'
            f'{check_str}</div>'
            f'{thumb}</div>',
            unsafe_allow_html=True)
        is_open, is_edit = card_actions(sb, place, my_name)
    if is_edit:
        edit_form_accommodation(sb, place, my_name)
    elif is_open:
        if d.get("address"):     st.markdown(f"**주소:** {d['address']}")
        if d.get("booking_url"): st.markdown(f"[예약 링크]({d['booking_url']})")
        if place.get("notes"):   st.markdown(f"**메모:** {place['notes']}")
        if img_paths:            show_images(sb, place.get("image_path"))


# ── Add forms ──────────────────────────────────────────────────────────────────
def form_restaurant(sb, my_name):
    st.markdown("#### 🍽️ 맛집 추가")
    with st.form("form_restaurant", clear_on_submit=True):
        name  = st.text_input("장소 이름 *", placeholder="예: 흑돈가")
        c1,c2 = st.columns(2)
        with c1: cuisine = st.selectbox("음식 종류", CUISINE_TYPES)
        with c2: price_r = st.selectbox("가격대", PRICE_RANGES)
        hours    = st.text_input("영업시간", placeholder="예: 11:00~21:00")
        location = st.text_input("위치 (동선용)", placeholder="예: 제주 흑돈가")
        url      = st.text_input("지도 링크 (선택)")
        notes    = st.text_area("메모", placeholder="추천 이유 등", height=70)
        st.caption("**사진 (여러 장 가능)**")
        img_files = inline_uploader("rst")
        if st.form_submit_button("✅ 추가하기", type="primary", use_container_width=True):
            if not name.strip(): st.error("이름을 입력해주세요!"); return
            add_place(sb, {"added_by": my_name, "category": "맛집", "name": name.strip(),
                           "url": url.strip() or None, "notes": notes.strip() or None,
                           "liked_by": [], "image_path": upload_images(sb, img_files),
                           "details": {"cuisine": cuisine, "price_range": price_r.split()[0],
                                       "hours": hours.strip() or None, "status": "검토중",
                                       "location": location.strip() or None}})
            st.success(f"✅ '{name}' 추가!"); st.rerun()


def form_activity(sb, my_name):
    st.markdown("#### 🎡 놀거리 추가")
    with st.form("form_activity", clear_on_submit=True):
        name     = st.text_input("이름 *", placeholder="예: 한라산 성판악")
        c1, c2   = st.columns(2)
        with c1: act_type = st.selectbox("종류", ACTIVITY_TYPES)
        with c2: price    = st.text_input("이용료", placeholder="예: 10000")
        duration = st.text_input("소요 시간", placeholder="예: 약 2시간")
        location = st.text_input("위치 (동선용)", placeholder="예: 제주 만장굴")
        url      = st.text_input("링크 (선택)")
        notes    = st.text_area("메모", height=70)
        st.caption("**사진 (여러 장 가능)**")
        img_files = inline_uploader("act")
        if st.form_submit_button("✅ 추가하기", type="primary", use_container_width=True):
            if not name.strip(): st.error("이름을 입력해주세요!"); return
            price_val = None
            try: price_val = int(price.replace(",","").replace("원","").strip())
            except: pass
            add_place(sb, {"added_by": my_name, "category": "놀거리", "name": name.strip(),
                           "url": url.strip() or None, "notes": notes.strip() or None,
                           "liked_by": [], "image_path": upload_images(sb, img_files),
                           "details": {"activity_type": act_type, "price": price_val,
                                       "duration": duration.strip() or None, "status": "검토중",
                                       "location": location.strip() or None}})
            st.success(f"✅ '{name}' 추가!"); st.rerun()


def form_flight(sb, my_name):
    st.markdown("#### ✈️ 항공편 추가")
    with st.form("form_flight", clear_on_submit=True):
        c1, c2  = st.columns(2)
        with c1: plan_no = st.selectbox("플랜 번호", ["플랜 1","플랜 2","플랜 3","플랜 4","플랜 5"])
        with c2: status  = st.selectbox("상태", STATUSES)
        st.markdown("**가는 편**")
        c1, c2  = st.columns(2)
        with c1: airline   = st.selectbox("항공사", AIRLINES)
        with c2: flight_no = st.text_input("편명 (선택)", placeholder="7C101")
        c1, c2  = st.columns(2)
        with c1: dep_ap = st.selectbox("출발지", DEP_AIRPORTS)
        with c2: arr_ap = st.selectbox("도착지", ARR_AIRPORTS)
        c1, c2, c3 = st.columns(3)
        with c1: dep_date = st.date_input("출발일", value=date(2026, 7, 1))
        with c2: dep_time = st.text_input("출발 시각", placeholder="07:30")
        with c3: arr_time = st.text_input("도착 시각", placeholder="09:00")
        price = st.text_input("가격 (1인, 원)", placeholder="89000")
        st.markdown("---")
        st.markdown("**돌아오는 편**")
        c1, c2  = st.columns(2)
        with c1: ret_airline   = st.selectbox("복귀 항공사", AIRLINES)
        with c2: ret_flight_no = st.text_input("복귀 편명 (선택)", placeholder="7C102")
        c1, c2, c3 = st.columns(3)
        with c1: ret_date     = st.date_input("복귀 출발일", value=date(2026, 7, 5))
        with c2: ret_dep_time = st.text_input("복귀 출발 시각", placeholder="20:00")
        with c3: ret_arr_time = st.text_input("복귀 도착 시각", placeholder="21:30")
        ret_price = st.text_input("복귀 가격 (1인 / 선택)", placeholder="79000")
        st.markdown("---")
        booking_url = st.text_input("예약 링크 (선택)")
        notes       = st.text_area("메모 (선택)", height=60)
        if st.form_submit_button("✅ 항공편 추가", type="primary", use_container_width=True):
            if not dep_time.strip(): st.error("출발 시각을 입력해주세요!"); return
            price_val = None
            try: price_val = int(price.replace(",","").replace("원","").strip())
            except: pass
            ret_price_val = None
            try: ret_price_val = int(ret_price.replace(",","").replace("원","").strip()) if ret_price.strip() else None
            except: pass
            add_place(sb, {"added_by": my_name, "category": "비행기",
                           "name": f"[{plan_no}] {airline} {dep_time.strip()} 출발",
                           "url": None, "notes": notes.strip() or None,
                           "liked_by": [], "image_path": None,
                           "details": {"plan_no": plan_no, "status": status,
                                       "airline": airline, "dep_airport": dep_ap, "arr_airport": arr_ap,
                                       "flight_no": flight_no.strip() or None,
                                       "dep_date": dep_date.strftime("%Y.%m.%d (%a)"),
                                       "dep_time": dep_time.strip(), "arr_time": arr_time.strip(),
                                       "price": price_val, "booking_url": booking_url.strip() or None,
                                       "ret_airline": ret_airline,
                                       "ret_flight_no": ret_flight_no.strip() or None,
                                       "ret_date": ret_date.strftime("%Y.%m.%d (%a)"),
                                       "ret_dep_time": ret_dep_time.strip() or None,
                                       "ret_arr_time": ret_arr_time.strip() or None,
                                       "ret_price": ret_price_val}})
            st.success("✅ 항공편 추가 완료!"); st.rerun()


def form_accommodation(sb, my_name):
    st.markdown("#### 🏨 숙소 추가")
    with st.form("form_accommodation", clear_on_submit=True):
        name = st.text_input("숙소 이름 *", placeholder="예: 오션뷰 펜션")
        c1, c2 = st.columns(2)
        with c1: room_type   = st.selectbox("유형", ROOM_TYPES)
        with c2: price_night = st.text_input("1박 가격 (원)", placeholder="150000")
        c1, c2 = st.columns(2)
        with c1: check_in  = st.text_input("체크인", placeholder="15:00")
        with c2: check_out = st.text_input("체크아웃", placeholder="11:00")
        address     = st.text_input("주소 (동선용)", placeholder="예: 제주시 애월읍")
        booking_url = st.text_input("예약 링크 (선택)")
        notes       = st.text_area("메모", height=70)
        st.caption("**사진 (여러 장 가능)**")
        img_files = inline_uploader("acc")
        if st.form_submit_button("✅ 추가하기", type="primary", use_container_width=True):
            if not name.strip(): st.error("이름을 입력해주세요!"); return
            price_val = None
            try: price_val = int(price_night.replace(",","").replace("원","").strip())
            except: pass
            add_place(sb, {"added_by": my_name, "category": "숙소", "name": name.strip(),
                           "url": None, "notes": notes.strip() or None,
                           "liked_by": [], "image_path": upload_images(sb, img_files),
                           "details": {"room_type": room_type, "price_per_night": price_val,
                                       "check_in": check_in.strip() or None,
                                       "check_out": check_out.strip() or None,
                                       "address": address.strip() or None,
                                       "booking_url": booking_url.strip() or None,
                                       "status": "검토중"}})
            st.success(f"✅ '{name}' 추가!"); st.rerun()


# ── Guards ─────────────────────────────────────────────────────────────────────
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ `.env` 파일에 `SUPABASE_URL`과 `SUPABASE_ANON_KEY`를 설정해주세요!")
    st.stop()

sb = init_sb()

# ── Name gate ──────────────────────────────────────────────────────────────────
if "my_name" not in st.session_state:
    st.session_state.my_name = st.query_params.get("name", "")

if not st.session_state.my_name:
    st.markdown(
        '<div class="name-gate">'
        '<div style="font-size:52px;margin-bottom:10px;">✈️</div>'
        '<div style="font-size:26px;font-weight:800;color:#1a1a1a;margin-bottom:4px;">여행 플래너</div>'
        '<div style="font-size:14px;color:#999;margin-bottom:24px;">함께 계획하는 가족 여행</div>'
        '<div style="font-size:13px;color:#777;font-weight:600;">이름을 선택해주세요</div>'
        '</div>',
        unsafe_allow_html=True)
    cols = st.columns(4)
    for i, p in enumerate(FAMILY_PRESETS):
        with cols[i]:
            if st.button(p, use_container_width=True, key=f"gate_{p}"):
                st.session_state.my_name = p; st.query_params["name"] = p; st.rerun()
    custom = st.text_input("또는 직접 입력", placeholder="이름 입력 후 Enter")
    if custom:
        st.session_state.my_name = custom; st.query_params["name"] = custom; st.rerun()
    st.stop()

my_name = st.session_state.my_name

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ✈️ 여행 플래너")
    new_name = st.text_input("👤 이름", value=my_name)
    col_p = st.columns(2)
    for i, p in enumerate(FAMILY_PRESETS):
        with col_p[i % 2]:
            if st.button(p, key=f"sb_{p}", use_container_width=True):
                st.session_state.my_name = p; st.query_params["name"] = p; st.rerun()
    if new_name and new_name != my_name:
        st.session_state.my_name = new_name; st.query_params["name"] = new_name
        my_name = new_name; st.rerun()

    st.markdown("---")
    travel_date = st.date_input("✈️ 여행 날짜", value=date(2026, 7, 1))
    days_left = (travel_date - date.today()).days
    if days_left > 0:
        st.markdown(f'<div class="countdown"><div class="d">D-{days_left}</div>'
                    f'<div class="sub">{travel_date.strftime("%Y.%m.%d")}</div></div>',
                    unsafe_allow_html=True)
    elif days_left == 0: st.success("🎉 오늘 출발!")
    else: st.info("여행 완료 ✅")

    st.markdown("---")
    all_sb = get_places(sb)
    st.markdown("### 현황")
    for cat in CATEGORIES:
        n = sum(1 for p in all_sb if p["category"] == cat)
        booked = sum(1 for p in all_sb if p["category"] == cat and (p.get("details") or {}).get("status") == "예약완료")
        st.markdown(f"{CAT_ICON[cat]} **{cat}** — {n}개 {'🔒' + str(booked) if booked else ''}")

    st.markdown("---")
    st.markdown("### 📋 예약 체크리스트")
    for cat in CATEGORIES:
        cat_places = [p for p in all_sb if p["category"] == cat]
        if not cat_places: continue
        for p in cat_places:
            status_val = (p.get("details") or {}).get("status", "검토중")
            icon = "🔒" if status_val == "예약완료" else "✅" if status_val == "확정" else "🔍"
            st.markdown(f"{icon} {p['name'][:16]}", help=f"상태: {status_val}")

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="padding:12px 0 10px;">'
    f'<div style="font-size:22px;font-weight:800;color:#1a1a1a;line-height:1.2;">제주도 여행 플래너</div>'
    f'<div style="font-size:13px;color:#555;margin-top:4px;">'
    f'<strong style="color:#1a1a1a;">{my_name}</strong>님과 함께해요</div>'
    f'</div>',
    unsafe_allow_html=True)

tab_list, tab_map, tab_schedule, tab_best, tab_expense, tab_add = st.tabs(
    ["전체 목록", "지도", "일정", "베스트", "경비", "추가"])

# ── 전체 목록 ──────────────────────────────────────────────────────────────────
with tab_list:
    sel = st.radio("카테고리", ["전체"] + CATEGORIES, horizontal=True,
                   label_visibility="collapsed")
    sort_by = st.radio("정렬", ["최신순", "투표순", "상태순"], horizontal=True,
                       label_visibility="collapsed")

    cat_filter = None if sel == "전체" else sel
    places = get_places(sb, cat_filter)

    if sort_by == "투표순":
        places = sorted(places, key=lambda p: len(p.get("liked_by") or []), reverse=True)
    elif sort_by == "상태순":
        order = {"예약완료": 0, "확정": 1, "검토중": 2}
        places = sorted(places, key=lambda p: order.get((p.get("details") or {}).get("status","검토중"), 9))

    if not places:
        st.markdown(
            '<div style="text-align:center;padding:40px 20px;">'
            '<div style="font-size:15px;font-weight:600;color:#1a1a1a;">아직 등록된 장소가 없어요</div>'
            '<div style="font-size:13px;margin-top:4px;color:#555;">추가 탭에서 첫 장소를 추가해보세요</div>'
            '</div>', unsafe_allow_html=True)

    if cat_filter == "비행기":
        plans: dict = {}
        for p in places:
            pn = (p.get("details") or {}).get("plan_no", "미분류")
            plans.setdefault(pn, []).append(p)
        for plan_name in sorted(plans.keys()):
            st.markdown(f"**{plan_name}**")
            for place in plans[plan_name]:
                card_flight(sb, place, my_name)
    else:
        for place in places:
            cat = place["category"]
            if cat == "맛집":    card_restaurant(sb, place, my_name)
            elif cat == "놀거리": card_activity(sb, place, my_name)
            elif cat == "비행기": card_flight(sb, place, my_name)
            elif cat == "숙소":   card_accommodation(sb, place, my_name)

# ── 지도 ───────────────────────────────────────────────────────────────────────
with tab_map:
    st.markdown(
        '<div style="font-size:18px;font-weight:800;color:#1a1a1a;margin-bottom:4px;">지도</div>'
        '<div style="font-size:13px;color:#555;margin-bottom:12px;">등록된 맛집·놀거리·숙소 위치</div>',
        unsafe_allow_html=True)
    if not FOLIUM_AVAILABLE:
        st.warning("지도 기능을 사용하려면:\n```\npip install folium streamlit-folium\n```")
    else:
        map_places = [p for p in get_places(sb) if p["category"] in ("맛집", "놀거리", "숙소")]
        if not map_places:
            st.markdown(
                '<div style="text-align:center;padding:40px 20px;color:#999;">'
                '<div style="font-size:40px;margin-bottom:8px;">📍</div>'
                '<div style="font-weight:600;">표시할 장소가 없어요</div>'
                '<div style="font-size:13px;margin-top:4px;">맛집·놀거리·숙소를 추가하면 여기에 표시돼요</div>'
                '</div>', unsafe_allow_html=True)
        else:
            # 범례
            leg_html = '<div style="display:flex;gap:14px;margin-bottom:10px;flex-wrap:wrap;">'
            for cat, dot in [("맛집","#E8756A"), ("놀거리","#2AB5AC"), ("숙소","#27AE60")]:
                cnt = sum(1 for p in map_places if p["category"] == cat)
                leg_html += (f'<span style="display:flex;align-items:center;gap:5px;font-size:12px;font-weight:600;color:#555;">'
                             f'<span style="width:10px;height:10px;border-radius:50%;background:{dot};display:inline-block;"></span>'
                             f'{CAT_ICON[cat]} {cat} {cnt}개</span>')
            leg_html += '</div>'
            st.markdown(leg_html, unsafe_allow_html=True)

            JEJU_CENTER = [33.4996, 126.5312]
            m = folium.Map(location=JEJU_CENTER, zoom_start=11,
                           tiles="CartoDB positron")
            MARKER_COLOR = {"맛집": "red", "놀거리": "blue", "숙소": "green"}

            failed_places = []
            for place in map_places:
                d   = place.get("details") or {}
                cat = place["category"]
                loc_str = d.get("location") or d.get("address") or ""
                coords = geocode_location(loc_str) if loc_str else None
                if not coords:
                    coords = geocode_location(f"제주 {place['name']}")
                if coords:
                    lat, lon = coords
                    status = d.get("status", "검토중")
                    sc = STATUS_COLOR.get(status, "#ccc")
                    icon_emoji = CAT_ICON.get(cat, "📌")
                    search_q = loc_str or place["name"]
                    maps_url = f"https://www.google.com/maps/search/{quote(search_q)}"

                    popup_html = (
                        f'<div style="min-width:160px;font-family:-apple-system,sans-serif;padding:4px;">'
                        f'<b style="font-size:13px;color:#1a1a1a;">{icon_emoji} {place["name"]}</b><br>'
                        f'<span style="color:{sc};font-size:11px;">{STATUS_ICON.get(status,"")} {status}</span>'
                        f'<span style="font-size:11px;color:#999;"> · {place["added_by"]}</span><br>'
                    )
                    if cat == "맛집" and d.get("cuisine"):
                        popup_html += f'<span style="font-size:11px;color:#666;">{d["cuisine"]}</span><br>'
                    elif cat == "놀거리" and d.get("activity_type"):
                        popup_html += f'<span style="font-size:11px;color:#666;">{d["activity_type"]}</span><br>'
                    elif cat == "숙소" and d.get("room_type"):
                        popup_html += f'<span style="font-size:11px;color:#666;">{d["room_type"]}</span><br>'
                    if place.get("notes"):
                        popup_html += f'<span style="font-size:11px;color:#888;">📝 {(place["notes"] or "")[:40]}</span><br>'
                    popup_html += (f'<a href="{maps_url}" target="_blank" '
                                   f'style="font-size:11px;color:#4361EE;">🗺️ 구글 지도에서 보기</a></div>')

                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_html, max_width=220),
                        tooltip=f"{icon_emoji} {place['name']}",
                        icon=folium.Icon(color=MARKER_COLOR.get(cat, "gray"), icon="info-sign")
                    ).add_to(m)
                else:
                    failed_places.append(place["name"])

            st_folium(m, use_container_width=True, height=460)

            if failed_places:
                st.caption(f"⚠️ 위치를 찾지 못한 장소: {', '.join(failed_places)}"
                           " — 위치(동선용) 또는 주소를 정확히 입력해주세요.")

# ── 일정 ───────────────────────────────────────────────────────────────────────
with tab_schedule:
    st.markdown(
        '<div style="font-size:18px;font-weight:800;color:#1a1a1a;margin-bottom:2px;">여행 일정</div>'
        '<div style="font-size:13px;color:#555;margin-bottom:12px;">확정·예약완료 항목만 표시돼요</div>',
        unsafe_allow_html=True)

    CONFIRMED = {"확정", "예약완료"}
    all_places_sch   = get_places(sb)
    conf_all         = [p for p in all_places_sch if (p.get("details") or {}).get("status") in CONFIRMED]
    conf_flights     = [p for p in conf_all if p["category"] == "비행기"]
    conf_scheduled   = [p for p in conf_all if p["category"] != "비행기"
                        and (p.get("details") or {}).get("travel_day")]
    conf_unscheduled = [p for p in conf_all if p["category"] != "비행기"
                        and not (p.get("details") or {}).get("travel_day")]

    if not conf_flights and not conf_scheduled and not conf_unscheduled:
        st.markdown(
            '<div style="text-align:center;padding:40px 20px;color:#999;">'
            '<div style="font-size:40px;margin-bottom:8px;">📅</div>'
            '<div style="font-weight:600;">확정된 일정이 없어요</div>'
            '<div style="font-size:13px;margin-top:4px;">전체 목록에서 ✅확정 버튼을 눌러보세요</div>'
            '</div>', unsafe_allow_html=True)
    else:
        # 확정 항공편
        if conf_flights:
            st.markdown('<div style="font-size:14px;font-weight:700;color:#1a1a1a;margin-bottom:6px;">✈️ 확정 항공편</div>', unsafe_allow_html=True)
            for p in conf_flights:
                d = p.get("details") or {}
                plan = d.get("plan_no", "")
                status_val = d.get("status", "확정")
                sc = STATUS_COLOR.get(status_val, "#2AB5AC")
                st.markdown(
                    f'<div style="background:#FAFAF9;border:1px solid #F0EDE8;border-radius:14px;'
                    f'padding:10px 14px;margin:4px 0;color:#1a1a1a;">'
                    f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                    f'<span style="font-weight:700;color:#1a1a1a;font-size:13px;">{plan}</span>'
                    f'<span style="font-size:11px;color:{sc};font-weight:600;">'
                    f'{STATUS_ICON.get(status_val,"")} {status_val}</span></div>'
                    f'<div style="font-size:13px;font-weight:600;margin-top:2px;">'
                    f'{d.get("airline","")} &nbsp; {d.get("dep_airport","")} {d.get("dep_time","")} → {d.get("arr_airport","")} {d.get("arr_time","")}</div>'
                    + (f'<div style="font-size:11px;color:#999;margin-top:2px;">↩️ 복귀 {d.get("ret_dep_time","")} → {d.get("ret_arr_time","")} · {d.get("ret_date","")}</div>' if d.get("ret_dep_time") else "")
                    + '</div>',
                    unsafe_allow_html=True)
            st.markdown("<div style='margin:8px 0;'></div>", unsafe_allow_html=True)

        # 달력 그리드
        if conf_scheduled:
            travel_date = date(2026, 7, 1)  # fallback — user can change via sidebar
            days = sorted(set(int((p.get("details") or {}).get("travel_day", 0)) for p in conf_scheduled))

            html = '<div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:12px;">'
            for day in days:
                actual_date = travel_date + timedelta(days=day - 1)
                date_label  = f"{actual_date.month}/{actual_date.day}"
                weekday     = ["월", "화", "수", "목", "금", "토", "일"][actual_date.weekday()]
                day_places  = [p for p in conf_scheduled
                               if int((p.get("details") or {}).get("travel_day", 0)) == day]

                locs = []
                for p in day_places:
                    pd = p.get("details") or {}
                    loc = pd.get("location") or pd.get("address") or p["name"]
                    locs.append(loc)
                maps_url = ("https://www.google.com/maps/dir/" +
                            "/".join(quote(l) for l in locs)) if len(locs) >= 2 else ""

                html += '<div class="sch-col">'
                html += '<div class="sch-head">'
                html += f'<div style="font-weight:800;font-size:13px;">Day {day}</div>'
                html += f'<div style="font-size:11px;opacity:.7;margin-top:2px;">{date_label} ({weekday})</div>'
                if maps_url:
                    html += f'<div style="margin-top:5px;"><a href="{maps_url}" target="_blank" style="color:#fff;font-size:10px;opacity:.85;text-decoration:underline;">🗺️ 동선 보기</a></div>'
                html += '</div>'

                for p in day_places:
                    d   = p.get("details") or {}
                    icon = CAT_ICON.get(p["category"], "📌")
                    sc   = STATUS_COLOR.get(d.get("status", "확정"), "#2AB5AC")
                    bc   = CAT_COLOR.get(p["category"], "#ccc")
                    sub  = ""
                    if p["category"] == "맛집" and d.get("cuisine"):
                        sub = d["cuisine"]
                    elif p["category"] == "놀거리" and d.get("price"):
                        sub = f"{int(d['price']):,}원"
                    elif p["category"] == "숙소" and d.get("check_in"):
                        sub = f"체크인 {d['check_in']}"
                    html += f'<div class="sch-item" style="border-left-color:{bc};">'
                    html += f'<div style="font-size:12px;font-weight:700;">{icon} {p["name"]}</div>'
                    if sub:
                        html += f'<div style="font-size:10px;color:#999;">{sub}</div>'
                    html += f'<div style="font-size:10px;color:{sc};margin-top:2px;">{STATUS_ICON.get(d.get("status","확정"),"")} {d.get("status","확정")}</div>'
                    html += '</div>'

                html += '</div>'
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        if conf_unscheduled:
            st.markdown('<div style="font-size:13px;font-weight:700;color:#1a1a1a;margin:8px 0 4px;">📋 일차 미배정</div>', unsafe_allow_html=True)
            for p in conf_unscheduled:
                icon = CAT_ICON.get(p["category"], "📌")
                st.markdown(
                    f'<div style="background:#FAFAF9;border:1px solid #F0EDE8;border-radius:12px;'
                    f'padding:8px 14px;margin:3px 0;font-size:13px;color:#555;">'
                    f'{icon} <b>{p["name"]}</b> · ✏️ 일차 배정하면 달력에 표시돼요</div>',
                    unsafe_allow_html=True)

# ── 베스트 픽 ──────────────────────────────────────────────────────────────────
with tab_best:
    st.markdown(
        '<div style="font-size:18px;font-weight:800;color:#1a1a1a;margin-bottom:2px;">베스트 픽</div>'
        '<div style="font-size:13px;color:#555;margin-bottom:12px;">가족 투표 TOP 10</div>',
        unsafe_allow_html=True)
    all_places = get_places(sb)
    voted = sorted([p for p in all_places if p.get("liked_by")],
                   key=lambda p: len(p["liked_by"]), reverse=True)
    if not voted:
        st.markdown(
            '<div style="text-align:center;padding:40px 20px;color:#999;">'
            '<div style="font-size:40px;margin-bottom:8px;">💕</div>'
            '<div style="font-weight:600;">아직 투표된 장소가 없어요</div>'
            '<div style="font-size:13px;margin-top:4px;">좋아요를 눌러보세요!</div>'
            '</div>', unsafe_allow_html=True)
    else:
        for i, place in enumerate(voted[:10]):
            liked_by = place["liked_by"]
            d = place.get("details") or {}
            medal = f"{i+1}위"
            detail_str = ""
            if place["category"] == "비행기":
                detail_str = f" · {d.get('dep_time','')}→{d.get('arr_time','')}"
                if d.get("price"): detail_str += f" · {int(d['price']):,}원"
            elif place["category"] == "숙소" and d.get("price_per_night"):
                detail_str = f" · {int(d['price_per_night']):,}원/박"
            voters = "  ".join(liked_by)
            st.markdown(
                f'<div style="background:#FAFAF9;border:1.5px solid #E2DDD8;border-radius:14px;'
                f'padding:12px 16px;margin:5px 0;">'
                f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                f'<div style="flex:1;min-width:0;">'
                f'<span style="font-size:13px;font-weight:800;color:#1a1a1a;">{medal} {place["name"]}</span>'
                f'<span style="font-size:12px;color:#999;">{detail_str}</span>'
                f'</div>'
                f'<span class="badge" style="flex-shrink:0;">{place["added_by"]}</span>'
                f'</div>'
                f'<div style="font-size:11px;color:#999;margin-top:5px;">{voters}</div>'
                f'</div>',
                unsafe_allow_html=True)

    st.markdown("---")
    if st.button("텍스트로 내보내기"):
        out = "✈️ 여행 플랜 정리\n\n"
        for cat in CATEGORIES:
            cat_places = [p for p in all_places if p["category"] == cat]
            if not cat_places: continue
            out += f"\n{CAT_ICON[cat]} {cat}\n{'─'*24}\n"
            for p in sorted(cat_places, key=lambda x: len(x.get("liked_by") or []), reverse=True):
                d = p.get("details") or {}
                votes = len(p.get("liked_by") or [])
                out += f"{'⭐'*votes if votes else '  '} {p['name']} (by {p['added_by']})\n"
                if cat == "비행기":
                    out += f"   {d.get('airline','')} {d.get('dep_time','')}→{d.get('arr_time','')}"
                    if d.get("price"): out += f"  {int(d['price']):,}원/인"
                    out += "\n"
                elif cat == "숙소" and d.get("price_per_night"):
                    out += f"   {int(d['price_per_night']):,}원/박\n"
                if p.get("url"):   out += f"   🔗 {p['url']}\n"
                if p.get("notes"): out += f"   📝 {p['notes']}\n"
                out += "\n"
        st.text_area("복사해서 공유하세요!", out, height=300)

# ── 경비 ───────────────────────────────────────────────────────────────────────
with tab_expense:
    st.markdown(
        '<div style="font-size:18px;font-weight:800;color:#1a1a1a;margin-bottom:2px;">경비 관리</div>'
        '<div style="font-size:13px;color:#555;margin-bottom:12px;">여행 경비를 한눈에 확인해요</div>',
        unsafe_allow_html=True)

    with st.expander("➕ 경비 직접 추가"):
        with st.form("form_expense", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: exp_name   = st.text_input("항목명 *", placeholder="예: 항공권")
            with c2: exp_cat    = st.selectbox("카테고리", EXPENSE_CATS)
            c1, c2 = st.columns(2)
            with c1: exp_amount = st.number_input("금액 (원)", min_value=0, step=1000, value=0)
            with c2: exp_extra  = st.checkbox("여윳돈 항목")
            exp_note = st.text_input("특이사항", placeholder="예: 1인 기준, 공동경비 등")
            if st.form_submit_button("추가", type="primary", use_container_width=True):
                if not exp_name.strip(): st.error("항목명을 입력해주세요!")
                else:
                    add_expense(sb, {"added_by": my_name, "category": exp_cat,
                                     "name": exp_name.strip(), "amount": int(exp_amount),
                                     "is_extra": exp_extra, "note": exp_note.strip() or None})
                    st.success("✅ 추가!"); st.rerun()

    expenses = get_expenses(sb)
    if expenses:
        total_normal = sum(e.get("amount",0) for e in expenses if not e.get("is_extra"))
        total_extra  = sum(e.get("amount",0) for e in expenses if e.get("is_extra"))
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("계획 경비", f"{total_normal:,}원")
        with c2: st.metric("여윳돈",   f"{total_extra:,}원")
        with c3: st.metric("합계",     f"{total_normal+total_extra:,}원")
        st.markdown("---")
        for cat in EXPENSE_CATS:
            cat_exps = [e for e in expenses if e.get("category") == cat]
            if not cat_exps: continue
            st.markdown(f"**{cat}**")
            for e in cat_exps:
                c1, c2 = st.columns([5, 1])
                with c1:
                    extra_tag = " `여윳돈`" if e.get("is_extra") else ""
                    note_str  = f" · {e['note']}" if e.get("note") else ""
                    st.markdown(f"{'💸' if e.get('is_extra') else '💳'} **{e['name']}** "
                                f"{int(e.get('amount',0)):,}원{extra_tag}{note_str}  \n"
                                f"<span style='color:#aaa;font-size:11px;'>by {e['added_by']}</span>",
                                unsafe_allow_html=True)
                with c2:
                    if e.get("added_by") == my_name:
                        if st.button("🗑️", key=f"del_exp_{e['id']}"):
                            delete_expense(sb, e["id"]); st.rerun()

    st.markdown("---")
    st.markdown('<div style="font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:4px;">👤 인원별 예상 경비</div>', unsafe_allow_html=True)
    st.caption("장소별 가격을 체크하면 예상 경비를 계산해요.")

    all_places_exp = get_places(sb)

    def get_place_price(p):
        d = p.get("details") or {}
        cat = p["category"]
        if cat == "비행기" and d.get("price"):
            total = int(d["price"]) + (int(d["ret_price"]) if d.get("ret_price") else 0)
            return total, f"✈️ {p['name']} · {total:,}원/인 (왕복)"
        if cat == "숙소" and d.get("price_per_night"):
            return int(d["price_per_night"]), f"🏨 {p['name']} · {int(d['price_per_night']):,}원/박"
        if cat == "놀거리" and d.get("price"):
            return int(d["price"]), f"🎡 {p['name']} · {int(d['price']):,}원"
        if cat == "맛집" and d.get("price_range"):
            pr = d["price_range"].split()[0]
            est = PRICE_EST.get(pr, 0)
            if est: return est, f"🍽️ {p['name']} · 약 {est:,}원 ({pr})"
        return None, None

    priced = []
    for p in all_places_exp:
        price, label = get_place_price(p)
        if price and label:
            priced.append({"id": p["id"], "price": price, "label": label,
                           "liked_by": p.get("liked_by") or []})

    if not priced:
        st.info("가격이 등록된 장소가 없어요.")
    else:
        person_tabs = st.tabs(FAMILY_PRESETS)
        for ti, person in enumerate(FAMILY_PRESETS):
            with person_tabs[ti]:
                total = 0
                for pp in priced:
                    default = person in pp["liked_by"]
                    checked = st.checkbox(pp["label"], value=default, key=f"rtn_{person}_{pp['id']}")
                    if checked: total += pp["price"]
                st.markdown("---")
                st.metric(f"{person} 예상 경비", f"{total:,}원")
                my_exps = [e for e in expenses if e.get("added_by") == person and not e.get("is_extra")]
                if my_exps:
                    manual_total = sum(e.get("amount",0) for e in my_exps)
                    if st.checkbox(f"직접 입력 경비 포함 ({manual_total:,}원)", key=f"inc_manual_{person}"):
                        st.metric("직접 입력 포함 합계", f"{total+manual_total:,}원")

# ── 추가하기 ───────────────────────────────────────────────────────────────────
with tab_add:
    st.markdown(
        '<div style="font-size:18px;font-weight:800;color:#1a1a1a;margin-bottom:12px;">장소 추가</div>',
        unsafe_allow_html=True)
    cat_sel = st.radio("카테고리 선택", CATEGORIES, horizontal=True,
                       label_visibility="collapsed")
    st.markdown("")
    if cat_sel == "맛집":    form_restaurant(sb, my_name)
    elif cat_sel == "놀거리": form_activity(sb, my_name)
    elif cat_sel == "비행기": form_flight(sb, my_name)
    elif cat_sel == "숙소":   form_accommodation(sb, my_name)

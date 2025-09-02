import os

# Synonyms mapping (soft): canonicalize for counting and filtering
SYNONYMS = {
    "hj":"handjob", "hand job":"handjob",
    "blow job":"blowjob", "bj":"blowjob",
    "cow girl":"cowgirl", "cum shot":"cumshot"
}

def canon_tag(t:str)->str:
    # version "baseline" (sera redéfinie APRÈS read_state() pour intégrer les bans)
    t = (t or '').strip().lower()
    return SYNONYMS.get(t, t)


from time import monotonic
_RATE_LIMIT = {}

def ratelimited(key, per=1.0):
    now = monotonic()
    last = _RATE_LIMIT.get(key, 0)
    if now - last < per:
        return True
    _RATE_LIMIT[key] = now
    return False

import re, json, logging, base64, mimetypes, unicodedata, hashlib, subprocess, threading, time
from datetime import datetime
from urllib.parse import quote_from_bytes, unquote_to_bytes
from flask import Flask, request, render_template, send_file, abort, jsonify, session, redirect, url_for

APP_NAME = "MiniVid"
DEF_EXT = ".mp4,.webm,.mkv,.avi,.flv,.m2ts"
MEDIA_DIRS = [p for p in (os.environ.get("MEDIA_DIRS") or "").split("|") if p.strip()]
MEDIA_NAMES = [p for p in (os.environ.get("MEDIA_NAMES") or "").split("|") if p.strip()]
if not MEDIA_NAMES or len(MEDIA_NAMES) != len(MEDIA_DIRS):
    MEDIA_NAMES = [f"Dossier {i+1}" for i in range(len(MEDIA_DIRS))]
ALLOWED_EXT = set([(os.environ.get("MINI_ALLOWED_EXT") or DEF_EXT).lower().split(",")][0])
DATA_DIR = os.environ.get("DATA_DIR") or "/data"
THUMB_DIR = os.environ.get("THUMB_DIR") or "/cache/thumbs"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

MINI_USER = os.environ.get("MINI_USER")
MINI_PASS = os.environ.get("MINI_PASS")
SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-" + hashlib.sha256(os.urandom(16)).hexdigest()
AUTH_ENABLED = bool(MINI_USER and MINI_PASS)

# Playback strategy
PLAYBACK = (os.environ.get("MINI_PLAYBACK") or "direct").strip().lower()   # direct|auto|remux
ALLOW_TRANSCODE = (os.environ.get("MINI_TRANSCODE","0").lower() in ("1","true","yes","on"))
FIREFOX_FALLBACK = (os.environ.get("MINI_FIREFOX_MKV_FALLBACK","1").lower() in ("1","true","yes","on"))
AUTOSCAN = (os.environ.get("MINI_AUTOSCAN","1").lower() in ("1","true","yes","on"))
SCAN_INTERVAL = int(os.environ.get("MINI_SCAN_INTERVAL","3600"))  # secondes

# Thumbs
MINI_THUMB_OFFSET = int(os.environ.get("MINI_THUMB_OFFSET", "5"))
MINI_THUMB_MAX    = int(os.environ.get("MINI_THUMB_MAX", "30"))

MIME_MAP = {
    "mp4":"video/mp4",
    "mkv":"video/x-matroska",
    "webm":"video/webm",
    "m2ts":"video/mp2t",
    "avi":"video/x-msvideo",
    "flv":"video/x-flv",
}

LOG = logging.getLogger("minivid")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

# ---- Async scan state (non-blocking maintenance) ----
import threading as _th
import time as _time

SCAN_STATE = {
    "running": False,
    "started": 0,
    "finished": 0,
    "kind": "",
    "progress": 0,
    "message": ""
}
SCAN_LOCK = _th.Lock()

def _run_scan(kind: str, fn):
    with SCAN_LOCK:
        if SCAN_STATE["running"]:
            return False
        SCAN_STATE.update({
            "running": True,
            "started": int(_time.time()),
            "finished": 0,
            "kind": kind,
            "progress": 0,
            "message": "Scan démarré…"
        })
    try:
        fn()
        with SCAN_LOCK:
            SCAN_STATE["progress"] = 100
            SCAN_STATE["message"] = "Scan terminé"
    except Exception as e:
        with SCAN_LOCK:
            SCAN_STATE["message"] = f"Erreur: {e}"
    finally:
        with SCAN_LOCK:
            SCAN_STATE["running"] = False
            SCAN_STATE["finished"] = int(_time.time())
    return True

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TPL_DIR  = os.path.abspath(os.path.join(BASE_DIR, "templates"))
ST_DIR   = os.path.abspath(os.path.join(BASE_DIR, "static"))

app = Flask(__name__, template_folder=TPL_DIR, static_folder=ST_DIR)
app.secret_key = SECRET_KEY
LOG.info("Template dir: %s | Static dir: %s", TPL_DIR, ST_DIR)

# ---------- Surrogate-safe helpers ----------
_SURR_RE = re.compile(r'[\ud800-\udfff]')

def strip_surrogates(s: str) -> str:
    try:
        s2 = s.encode('utf-8','surrogatepass').decode('utf-8','replace')
    except Exception:
        try:
            s2 = s.encode('utf-8','ignore').decode('utf-8','ignore')
        except Exception:
            s2 = s
    return _SURR_RE.sub('�', s2)

def safe_display_name(s: str) -> str:
    try:
        s = unicodedata.normalize('NFC', s)
    except Exception:
        pass
    return strip_surrogates(s)

def urlq(s: str) -> str:
    if s is None: return ""
    if not isinstance(s, str): s = str(s)
    b = s.encode('utf-8','surrogatepass')
    return quote_from_bytes(b)

@app.template_filter("datetime")
def _fmt_dt(ts):
    try:
        ts = int(ts)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "—"

@app.template_filter("filesize")
def _fmt_filesize(n):
    try:
        n = int(n)
        if n >= 1073741824:
            return f"{n/1073741824:.1f} Go"
        else:
            return f"{n/1048576:.1f} Mo"
    except Exception:
        return str(n)


def tagify(text):
    """Return up to 5 single-word tags derived from filename.
    Filters: dates, tokens with digits, 2-letter tokens (except '4k'),
    pronouns (FR/EN), and common video words (video/videos/vid/vids/vidéo/vidéos).
    """
    try:
        import unicodedata, re, os
        PRONOUNS = {
            "i","me","my","mine","myself","you","your","yours","yourself",
            "he","him","his","himself","she","her","hers","herself",
            "it","its","itself","we","us","our","ours","ourselves",
            "they","them","their","theirs","themselves",
            "je","me","moi","mon","ma","mes","tu","toi","ton","ta","tes",
            "il","elle","on","se","soi","son","sa","ses","nous","notre","nos",
            "vous","votre","vos","ils","elles","leur","leurs",
            "for","the","of"
        }
        AUTO_STOP = {"video","videos","vid","vids","vidéo","vidéos"}

        base = os.path.splitext(os.path.basename(text or ""))[0]
        base = unicodedata.normalize("NFKC", base)

        words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", base)

        out, seen = [], set()
        for w in words:
            lo = w.lower()
            if lo in PRONOUNS or lo in AUTO_STOP:
                continue
            if len(lo) == 2 and lo != "4k":
                continue
            if any(c.isdigit() for c in lo):
                continue
            if re.fullmatch(r"(?:\d{4}[-_.]\d{2}[-_.]\d{2})|(?:\d{2}[-_.]\d{2}[-_.]\d{4})|(?:\d{8})", lo):
                continue
            if len(lo) <= 1 or lo in seen:
                continue
            seen.add(lo)
            out.append(w)
            if len(out) >= 5:
                break
        # filtrage final via bans (sera défini plus bas)
        return _tagify_filter_banned(out)
    except Exception as e:
        LOG.warning("tagify error: %s", e)
        return []


def p_label(h:int)->str:
    try: h=int(h)
    except Exception: return ""
    if h >= 2160: return "2160p"
    if h >= 1440: return "1440p"
    if h >= 1080: return "1080p"
    if h >= 720:  return "720p"
    if h >= 480:  return "480p"
    if h >= 360:  return "360p"
    return f"{h}p" if h>0 else ""

def id_for(root_idx: int, rel: str) -> str:
    raw = f"{root_idx}|{rel}"
    b = raw.encode("utf-8", "surrogatepass")
    return base64.urlsafe_b64encode(b).decode("ascii")

def id_to_parts(vid: str):
    b = base64.urlsafe_b64decode(vid.encode("ascii"))
    s = b.decode("utf-8", "surrogatepass")
    i, rel = s.split("|", 1)
    return int(i), rel

# ---------- Scan ----------
MEDIA = []
def scan_media():
    global MEDIA
    items = []
    for ridx, root in enumerate(MEDIA_DIRS):
        if not root or not os.path.isdir(root):
            continue
        for dp, _, files in os.walk(root):
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in ALLOWED_EXT:
                    continue
                full = os.path.join(dp, fn)
                try:
                    st = os.stat(full)
                except Exception:
                    continue
                rel = os.path.relpath(full, root)
                item = {
                    "id": id_for(ridx, rel),
                    "root": ridx,
                    "root_name": MEDIA_NAMES[ridx] if ridx < len(MEDIA_NAMES) else f"Dossier {ridx+1}",
                    "dir": os.path.dirname(rel).replace("\\","/").strip(".") or "",
                    "name": safe_display_name(fn),
                    "ext": ext[1:].lower(),
                    "size": st.st_size,
                    "mtime": int(st.st_mtime),
                    "tags": tagify(fn),
                }
                items.append(item)
    MEDIA = items
    LOG.info("Scanned %d items across %d roots", len(MEDIA), len(MEDIA_DIRS))

# --- Auto scan thread ---
def _autoscan_loop():
    while True:
        try:
            time.sleep(max(30, SCAN_INTERVAL))
            if AUTOSCAN and SCAN_INTERVAL > 0:
                LOG.info("[autoscan] rescanning media…")
                scan_media()
        except Exception as e:
            LOG.warning("[autoscan] error: %s", e)

# démarrage du thread après le scan initial
try:
    if AUTOSCAN and SCAN_INTERVAL > 0:
        t_autoscan = threading.Thread(target=_autoscan_loop, daemon=True)
        t_autoscan.start()
        LOG.info("Auto-refresh actif (intervalle: %ss)", SCAN_INTERVAL)
except Exception as _e:
    LOG.warning("Impossible de démarrer l'auto-refresh: %s", _e)

# ---------- State ----------
def read_state():
    path = os.path.join(DATA_DIR, "state.json")
    if not os.path.exists(path):
        return {"played":{}, "progress":{}, "fav":{}, "utags":{}, "lists":{}, "meta":{}, "prefs":{"hide_tags":[]}, "banned_tags":[]}
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"played":{}, "progress":{}, "fav":{}, "utags":{}, "lists":{}, "meta":{}, "prefs":{"hide_tags":[] }, "banned_tags":[]}

def write_state(st):
    tmp = os.path.join(DATA_DIR, "state.tmp.json")
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    os.replace(tmp, os.path.join(DATA_DIR, "state.json"))

# ---------- Banned tags (ENV + UI) ----------
def _env_banned_tags():
    raw = (os.environ.get("MINI_BANNED_TAGS") or "").strip()
    if not raw:
        return set()
    return {t.strip().lower() for t in re.split(r"[,\s;]+", raw) if t.strip()}

def get_banned_tags():
    st = read_state()
    ui = st.get("banned_tags")
    if isinstance(ui, list) and any(ui):
        return {str(t).strip().lower() for t in ui if str(t).strip()}
    return _env_banned_tags()

def set_banned_tags(tags_iterable):
    tags = {str(t).strip().lower() for t in (tags_iterable or []) if str(t).strip()}
    st = read_state()
    st["banned_tags"] = sorted(tags)
    write_state(st)
    return st["banned_tags"]

def clear_banned_tags():
    st = read_state()
    st["banned_tags"] = []
    write_state(st)
    return []

# Redéfinition de canon_tag pour intégrer bans + synonymes
def canon_tag(t:str)->str:
    t = (t or '').strip().lower()
    if not t:
        return ""
    t = SYNONYMS.get(t, t)
    if t in get_banned_tags():
        return ""
    return t

def _tagify_filter_banned(words):
    banned = get_banned_tags()
    seen = set()
    out = []
    for w in words:
        ct = canon_tag(w)
        if not ct or ct in banned or ct in seen:
            continue
        seen.add(ct)
        out.append(w)
    return out

# --- API: état utilisateur (favoris, lu/non-lu, tags, préférences) ---

@app.route("/api/fav", methods=["POST"])
def api_fav():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    try:
        data = request.get_json(force=True, silent=True) or {}
        vid = (data.get("vid") or "").strip()
        val = bool(data.get("fav"))
        if not vid:
            return jsonify(ok=False, error="missing_vid"), 400
        st = read_state()
        fav = st.get("fav", {}) or {}
        if val:
            fav[vid] = True
        else:
            fav.pop(vid, None)
        st["fav"] = fav
        write_state(st)
        return jsonify(ok=True, fav=bool(fav.get(vid)))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route("/api/played", methods=["POST"])
def api_played():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    try:
        data = request.get_json(force=True, silent=True) or {}
        vid = (data.get("vid") or "").strip()
        val = bool(data.get("played"))
        if not vid:
            return jsonify(ok=False, error="missing_vid"), 400
        st = read_state()
        played = st.get("played", {}) or {}
        if val:
            played[vid] = True
        else:
            played.pop(vid, None)
        st["played"] = played
        write_state(st)
        return jsonify(ok=True, played=bool(played.get(vid)))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route("/api/tag", methods=["POST"])
def api_tag_add():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    try:
        data = request.get_json(force=True, silent=True) or {}
        vid = (data.get("vid") or "").strip()
        tags = data.get("tags") or []
        if not vid or not isinstance(tags, list):
            return jsonify(ok=False, error="bad_payload"), 400
        norm = []
        for t in tags:
            t = canon_tag(t)
            if t and len(t) <= 40:
                norm.append(t)
        if not norm:
            return jsonify(ok=True, tags=[])
        st = read_state()
        ut = st.get("utags", {}) or {}
        cur = set([canon_tag(x) for x in (ut.get(vid) or [])])
        for t in norm:
            cur.add(t)
        ut[vid] = sorted(cur)[:20]
        st["utags"] = ut
        write_state(st)
        return jsonify(ok=True, tags=ut[vid])
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route("/api/prefs", methods=["POST"])
def api_prefs():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    try:
        data = request.get_json(force=True, silent=True) or {}
        st = read_state()
        prefs = st.get("prefs", {}) or {}
        hide = set(prefs.get("hide_tags", []) or [])
        for t in data.get("hide_tags_add", []) or []:
            t = canon_tag(t)
            if t:
                hide.add(t)
        for t in data.get("hide_tags_remove", []) or []:
            t = canon_tag(t)
            if t in hide:
                hide.remove(t)
        prefs["hide_tags"] = sorted(hide)
        st["prefs"] = prefs
        write_state(st)
        return jsonify(ok=True, prefs=prefs)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# --- Banned tags API ---
@app.route("/api/banned_tags", methods=["GET"])
def api_banned_get():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    ui = read_state().get("banned_tags", [])
    env = sorted(list(_env_banned_tags()))
    src = "ui" if ui else "env"
    return jsonify(ok=True, source=src, tags=(ui if ui else env))

@app.route("/api/banned_tags", methods=["POST"])
def api_banned_set():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    data = request.get_json(force=True, silent=True) or {}
    tags = data.get("tags")
    if tags is None and data.get("csv"):
        tags = [t for t in re.split(r"[,\s;]+", str(data.get("csv"))) if t]
    if not isinstance(tags, list):
        return jsonify(ok=False, error="bad_payload", hint="use {'tags': ['a','b']} or {'csv':'a,b'}"), 400
    new_list = set_banned_tags(tags)
    return jsonify(ok=True, source="ui", tags=new_list)

@app.route("/api/banned_tags", methods=["DELETE"])
def api_banned_clear():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    clear_banned_tags()
    return jsonify(ok=True, source="env", tags=sorted(list(_env_banned_tags())))

# --- Journal/helper & storage files ---
SCAN_CACHE_FILE = os.path.join(DATA_DIR if 'DATA_DIR' in globals() else '/data', 'scan_cache.json')
THUMB_PROGRESS = {"total":0,"done":0,"running":False,"last_error":""}
EVENTS_LOG = os.path.join(DATA_DIR if 'DATA_DIR' in globals() else '/data', 'events_log.json')

def _load_json(path, default):
    try:
        with open(path,'r',encoding='utf-8') as f: return json.load(f)
    except Exception:
        return default

def _save_json(path, obj):
    try:
        with open(path,'w',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False, indent=2)
    except Exception: pass

def _log_event(event: str, **kv):
    try:
        ev = _load_json(EVENTS_LOG, [])
        ev.append({
            "ts": int(time.time()),
            "event": event,
            **kv
        })
        _save_json(EVENTS_LOG, ev[-200:])
    except Exception:
        pass

# ---------- Auth ----------
def auth_required():
    if not AUTH_ENABLED:
        return True
    return bool(session.get("user"))

@app.route("/login", methods=["GET","POST"])
def login():
    try:
        if not AUTH_ENABLED:
            return render_template("login.html", error=None, enabled=False)
        error = None
        if request.method == "POST":
            u = request.form.get("username","")
            p = request.form.get("password","")
            remember = bool(request.form.get("remember"))
            if u == MINI_USER and p == MINI_PASS:
                session["user"] = u
                if remember:
                    session.permanent = True
                    app.permanent_session_lifetime = 60*60*24*30
                return redirect(url_for("browse"))
            error = "Identifiants invalides"
        return render_template("login.html", error=error, enabled=True)
    except Exception as e:
        return jsonify(error="login_render_failed", exc=str(e), template_dir=TPL_DIR), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("browse"))

# ---------- Routes ----------
@app.route("/")
def root():
    return redirect(url_for("browse"))

@app.route("/health")
def health():
    return jsonify(ok=True, count=len(MEDIA), tpl=TPL_DIR, st=ST_DIR,
                   have_index=os.path.exists(os.path.join(TPL_DIR,'index.html')),
                   have_watch=os.path.exists(os.path.join(TPL_DIR,'watch.html')),
                   have_login=os.path.exists(os.path.join(TPL_DIR,'login.html')))

@app.route("/browse")
def browse():
    if not auth_required():
        return redirect(url_for("login"))
    per  = (request.args.get("per") or "all").strip().lower()
    if per not in ("all","12","24","48","96"): per = "all"
    readf = (request.args.get("read") or "all").strip().lower()
    if readf not in ("all","unread","read"): readf = "all"
    mix  = (request.args.get("mix") or "all").strip().lower()
    if mix not in ("all","folders_first","videos_first"): mix = "all"
    page = int((request.args.get("page") or "1") or 1)
    sort = (request.args.get("sort") or "date").strip().lower()
    q    = (request.args.get("q") or "").strip()
    tag  = strip_surrogates((request.args.get("tag") or "").strip())
    utag = strip_surrogates((request.args.get("utag") or "").strip())
    tags_param = strip_surrogates((request.args.get("tags") or "").strip())
    sel_tags = [t.strip() for t in tags_param.split(",") if t.strip()]
    listq= strip_surrogates((request.args.get("list") or "").strip())
    fav_only = (request.args.get("fav") or "0") in ("1","true","yes")
    rootq_raw = request.args.get("root")
    dir_in = request.args.get("dir") or ""
    try:
        dirq = unquote_to_bytes(dir_in).decode('utf-8','surrogatepass')
    except Exception:
        dirq = dir_in
    root_index = int(rootq_raw) if (rootq_raw is not None and str(rootq_raw).isdigit()) else None
    dirq_q = urlq(dirq) if dirq else ""

    state = read_state()
    played = state.get("played",{}); fav = state.get("fav",{}); utags_state = state.get("utags",{}); lists_state = state.get("lists",{}); meta = state.get("meta",{})
    roots = [{"idx":i, "name":safe_display_name(MEDIA_NAMES[i])} for i in range(len(MEDIA_DIRS))]

    items = MEDIA[:]
    # --- ensure ctags are present for each video item ---
    utags_state = (state.get("utags", {}) or {})
    for v in items:
        if v.get("kind") != "video":
            continue
        vt = (v.get("tags") or [])
        vu = (utags_state.get(v.get("id")) or [])
        ctags = []
        seen = set()
        banned = get_banned_tags()
        for t in vt + vu:
            key = (canon_tag(t) or "").strip().lower()
            if not key or key in banned or key in seen:
                continue
            seen.add(key)
            ctags.append(t)
        if not ctags:
            try:
                ctags = tagify(v.get("name","")) or []
            except Exception:
                ctags = []
        v["ctags"] = ctags[:8]

    for it in items:
        if not isinstance(it, dict) or not it.get("id"):
            try:
                app.logger.warning("Skipping item without id: %r", it)
            except Exception:
                pass
            continue
        it["utags"] = utags_state.get(it["id"], [])
        it["fav"] = bool(fav.get(it["id"]))
        it["played"] = bool(played.get(it["id"]))
        m = meta.get(it["id"], {})
        if isinstance(m, dict) and m.get("w") and m.get("h"):
            it["res"] = f"{m['w']}×{m['h']}"; it["p"] = p_label(m.get("h"))
            it["w"]=m.get("w"); it["h"]=m.get("h")
        else:
            it["res"] = ""; it["p"] = ""

    if root_index is not None:
        items = [i for i in items if i["root"] == root_index]
    if dirq:
        items = [i for i in items if (i["dir"] or "") == dirq]
    if q:
        ql = q.lower(); items = [i for i in items if ql in i["name"].lower()]
    if tag:
        items = [i for i in items if tag.lower() in [t.lower() for t in i.get("tags",[])] or tag.lower() in [t.lower() for t in (state.get("utags",{}).get(i["id"],[]) or [])]]
    if utag:
        items = [i for i in items if utag.lower() in [t.lower() for t in (state.get("utags",{}).get(i["id"],[]) or [])]]
    if sel_tags:
        def _has_all(it):
            alltags = [t.lower() for t in (it.get("tags",[]) or [])] + [t.lower() for t in (state.get("utags",{}).get(it["id"],[]) or [])]
            return all(t.lower() in alltags for t in sel_tags)
        items = [i for i in items if _has_all(i)]
    if listq:
        vids = set(lists_state.get(listq, []))
        items = [i for i in items if i["id"] in vids]
    if fav_only:
        items = [i for i in items if i.get("fav")]

    # folders
    folders = []
    if (not tag and not utag and not listq):
        def child_of(it):
            d = it["dir"]
            if dirq == "":
                return d.split("/",1)[0] if d else ""
            else:
                if not d.startswith(dirq): return ""
                rest = d[len(dirq):].lstrip("/")
                return rest.split("/",1)[0] if rest else ""
        buckets = {}
        for it in items:
            chid = child_of(it)
            if chid:
                buckets.setdefault(chid, []).append(it)
        for name_raw, vids in buckets.items():
            latest = max(v["mtime"] for v in vids) if vids else 0
            folders.append({
                "kind": "folder",
                "name": safe_display_name(name_raw),
                "name_raw": name_raw,
                "name_q": urlq(name_raw),
                "latest": latest,
                "count": len(vids),
                "size": 0
            })

    if readf == "read":
        items = [i for i in items if i.get("played")]
    elif readf == "unread":
        items = [i for i in items if not i.get("played")]

    # sort videos
    if sort == "date":
        items.sort(key=lambda x: x["mtime"], reverse=True)
    elif sort == "size":
        items.sort(key=lambda x: x.get("size",-1), reverse=True)
    elif sort == "status_unread":
        items.sort(key=lambda x: (x.get("played", False), x["name"].lower()))
    elif sort == "status_read":
        items.sort(key=lambda x: (not x.get("played", False), x["name"].lower()))
    else:
        items.sort(key=lambda x: x["name"].lower())
    # resolution sorting
    if sort == "res_desc":
        items.sort(key=lambda x: (x.get("h") or 0, x.get("w") or 0), reverse=True)
    elif sort == "res_asc":
        items.sort(key=lambda x: (x.get("h") or 0, x.get("w") or 0))

    # combined list
    combined = []
    if not (tag or utag or listq):
        for f in folders:
            next_dir_q = (dirq_q + "%2F" + f["name_q"]) if dirq_q else f["name_q"]
            f["url"] = f"/browse?root={(root_index if root_index is not None else '')}&dir={next_dir_q}&mix={mix}&sort={sort}&read={readf}&per={per}"
            combined.append(f)
    for v in items:
        # Only list videos for the CURRENT directory (non-recursive)
        if (not tag and not utag and not listq):
            if dirq == "":
                _tops = set([f.get("name_raw", f.get("name")) for f in folders])
                _dir = v.get("dir", "") or ""
                _top = _dir.split("/", 1)[0] if _dir else ""
                if _top in _tops:
                    continue
            else:
                if v.get("dir", "") != dirq:
                    continue
        ctags_src = (v.get("utags",[]) or []) + (v.get("tags",[]) or [])
        seen=set(); disp=[]
        banned = get_banned_tags()
        for t in ctags_src:
            key = (canon_tag(t) or "").strip().lower()
            if not key or key in banned or key in seen:
                continue
            seen.add(key); disp.append(t)
        ctags = disp[:5]
        combined.append({
            "kind":"video",
            "id": v["id"], "name": v["name"], "mtime": v["mtime"], "size": v["size"],
            "ext": v["ext"], "res": v.get("res",""), "p": v.get("p",""),
            "tags": v.get("tags",[]), "utags": v.get("utags",[]), "ctags": ctags,
            "fav": v.get("fav", False), "played": v.get("played", False)
        })

    if mix == "all":
        if sort == "date":
            combined.sort(key=lambda x: (x["latest"] if x["kind"]=="folder" else x.get("mtime",0)), reverse=True)
        elif sort == "size":
            combined.sort(key=lambda x: (x.get("size",0)), reverse=True)
        elif sort == "status_unread":
            def key(x):
                played = x.get("played", False) if x["kind"]=="video" else True
                name = x["name"].lower()
                return (played, name)
            combined.sort(key=key)
        elif sort == "status_read":
            def key(x):
                played = x.get("played", False) if x["kind"]=="video" else False
                name = x["name"].lower()
                return (not played, name)
            combined.sort(key=key)
        else:
            combined.sort(key=lambda x: x["name"].lower())
    elif mix == "folders_first":
        combined.sort(key=lambda x: (x["kind"]!="folder", x["name"].lower()))
    elif mix == "videos_first":
        combined.sort(key=lambda x: (x["kind"]!="video", x["name"].lower()))

    total_items = len(combined)
    per_val = 0 if per in ("all","0","") else int(per)
    if per_val > 0:
        pages = max(1, (total_items + per_val - 1)//per_val)
        page = max(1, min(page, pages))
        start = (page-1)*per_val
        combined_page = combined[start:start+per_val]
    else:
        pages = 1; page = 1; combined_page = combined

    hide = set((state.get("prefs",{}) or {}).get("hide_tags", []))
    counts = {}; ucounts = {}
    for i in items:
        for t in i.get("tags",[]) or []:
            k = (canon_tag(t) or "").strip().lower()
            if not k:
                continue
            counts[k] = counts.get(k,0)+1
        for t in (state.get("utags",{}).get(i["id"],[]) or []):
            k = (canon_tag(t) or "").strip().lower()
            if not k:
                continue
            ucounts[k] = ucounts.get(k,0)+1
    popular = [(k,v) for k,v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True) if k not in hide][:50]
    upopular = [(k,v) for k,v in sorted(ucounts.items(), key=lambda kv: kv[1], reverse=True) if k not in hide][:50]

    crumbs = []
    parent_url = None
    if dirq:
        accum_raw = []
        for seg in dirq.split('/'):
            accum_raw.append(seg)
            crumbs.append({
                "label": safe_display_name(seg),
                "url": f"/browse?root={(root_index if root_index is not None else '')}&dir={'%2F'.join(urlq(s) for s in accum_raw)}&read={readf}&per={per}&mix={mix}&sort={sort}"
            })
        if len(accum_raw) > 1:
            prev = accum_raw[:-1]
            parent_q = "%2F".join(urlq(s) for s in prev)
            parent_url = f"/browse?root={(root_index if root_index is not None else '')}&dir={parent_q}&read={readf}&per={per}&mix={mix}&sort={sort}"
        else:
            parent_url = f"/browse?root={(root_index if root_index is not None else '')}&read={readf}&per={per}&mix={mix}&sort={sort}"

    app.logger.info("Listing items: total=%s page=%s/%s combined_page=%s", total_items, page, pages, len(combined_page))
    try:
        items = mark_duplicates(items)
    except Exception:
        pass
    return render_template("index.html", sel_tags=sel_tags, popular=popular,
        utags=state.get("utags",{}),
        grid=combined_page, folder_total=len([x for x in combined if x['kind']=='folder']), video_total=len([x for x in combined if x['kind']=='video']), total_items=total_items,upopular=upopular, lists=[],
        q=q, tag=tag, utag=utag, listq=listq, fav_only=fav_only,
        sort=sort, dirq_q=dirq_q, crumbs=crumbs, parent_url=parent_url,
        rootq=rootq_raw, root_index=root_index, roots=roots, auth=AUTH_ENABLED, user=session.get("user"),
        per=per, page=page, pages=pages, readf=readf, mix=mix
    )

def _ctype_for(path):
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    if PLAYBACK == "direct" and ext in ("mkv","avi","flv","m2ts"):
        return "application/octet-stream"
    if ext in MIME_MAP:
        return MIME_MAP[ext]
    mt = mimetypes.guess_type(path)[0] or ""
    if mt.startswith("video/"):
        return mt
    return "video/*"

@app.route("/download/<vid>")
def download(vid):
    if not auth_required():
        return redirect(url_for("login"))
    try:
        ridx, rel = id_to_parts(vid)
    except Exception:
        abort(404)
    if ridx < 0 or ridx >= len(MEDIA_DIRS):
        abort(404)
    full = os.path.normpath(os.path.join(MEDIA_DIRS[ridx], rel))
    if not os.path.exists(full):
        abort(404)
    fname = os.path.basename(full)
    return send_file(full, mimetype="application/octet-stream", as_attachment=True, download_name=fname)

@app.route("/thumb/<vid>.jpg")
def thumb(vid):
    try:
        ridx, rel = id_to_parts(vid)
    except Exception:
        abort(404)
    if ridx < 0 or ridx >= len(MEDIA_DIRS):
        abort(404)
    full = os.path.normpath(os.path.join(MEDIA_DIRS[ridx], rel))
    if not os.path.exists(full):
        abort(404)

    out = os.path.join(THUMB_DIR, f"{vid}.jpg")
    if not os.path.exists(out):
        duration_sec = None
        probe_json = None
        try:
            probe = subprocess.run(
                [
                    "ffprobe","-v","error",
                    "-show_entries","stream=width,height:format=duration",
                    "-select_streams","v:0",
                    "-of","json", full
                ],
                capture_output=True, text=True,
                timeout=int(os.environ.get("MINI_FFPROBE_TIMEOUT","10"))
            )
            if probe.returncode == 0 and probe.stdout:
                probe_json = json.loads(probe.stdout)
                dur = (probe_json.get("format") or {}).get("duration")
                if dur is not None:
                    try:
                        duration_sec = float(dur)
                    except Exception:
                        duration_sec = None
        except Exception:
            pass

        offset = MINI_THUMB_OFFSET
        try:
            if duration_sec and duration_sec > 0:
                cand = int(duration_sec * 0.10)
                if cand < MINI_THUMB_OFFSET: cand = MINI_THUMB_OFFSET
                if cand > MINI_THUMB_MAX:    cand = MINI_THUMB_MAX
                offset = cand
        except Exception:
            pass

        try:
            cmd = [
                "ffmpeg","-y","-loglevel","error",
                "-ss", str(offset), "-i", full,
                "-frames:v","1",
                "-vf","scale='min(320,iw)':'-2'",
                out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=int(os.environ.get("MINI_FFPROBE_TIMEOUT","10")))
        except Exception:
            pass

        try:
            w = h = None
            if probe_json and (probe_json.get("streams") or []):
                w = probe_json["streams"][0].get("width")
                h = probe_json["streams"][0].get("height")
            if not (w and h):
                probe2 = subprocess.run(
                    ["ffprobe","-v","error","-select_streams","v:0",
                     "-show_entries","stream=width,height","-of","json", full],
                    capture_output=True, text=True,
                    timeout=int(os.environ.get("MINI_FFPROBE_TIMEOUT","10"))
                )
                if probe2.returncode == 0 and probe2.stdout:
                    jd2 = json.loads(probe2.stdout)
                    if jd2.get("streams"):
                        w = jd2["streams"][0].get("width"); h = jd2["streams"][0].get("height")
            if w and h:
                st = read_state()
                st.setdefault("meta",{})[vid] = {"w": int(w), "h": int(h)}
                write_state(st)
        except Exception:
            pass

    if not os.path.exists(out):
        return send_file(os.path.join(ST_DIR,"placeholder.svg"))
    return send_file(out, mimetype="image/jpeg")


def _range_stream(path, start, end, chunk=8192):
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            data = f.read(min(chunk, remaining))
            if not data: break
            remaining -= len(data)
            yield data

@app.route("/stream/<vid>")
def stream(vid):
    try:
        ridx, rel = id_to_parts(vid)
    except Exception:
        abort(404)
    full = os.path.normpath(os.path.join(MEDIA_DIRS[ridx], rel))
    if not os.path.exists(full):
        abort(404)
    size = os.path.getsize(full)
    range_header = request.headers.get("Range", None)
    if not range_header:
        return send_file(full, mimetype=_ctype_for(full), as_attachment=False)
    m = re.match(r"bytes=(\d+)-(\d*)", range_header or "")
    if not m:
        return send_file(full, mimetype=_ctype_for(full), as_attachment=False)
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else size-1
    end = min(end, size-1)
    length = end - start + 1
    resp = app.response_class(_range_stream(full, start, end), status=206, mimetype=_ctype_for(full), direct_passthrough=True)
    resp.headers.add("Content-Range", f"bytes {start}-{end}/{size}")
    resp.headers.add("Accept-Ranges", "bytes")
    resp.headers.add("Content-Length", str(length))
    return resp

@app.route("/play/<vid>")
def play(vid):
    try:
        ridx, rel = id_to_parts(vid)
    except Exception:
        abort(404)
    full = os.path.normpath(os.path.join(MEDIA_DIRS[ridx], rel))
    ext = os.path.splitext(full)[1].lower().lstrip('.')
    mode = PLAYBACK
    ua = (request.headers.get("User-Agent") or "").lower()
    if mode == "direct" and FIREFOX_FALLBACK and ("firefox" in ua) and ext in ("mkv","m2ts","avi","flv"):
        return redirect(url_for("remux", vid=vid))
    if mode == "direct":
        return redirect(url_for("stream", vid=vid))
    if mode == "remux":
        return redirect(url_for("remux", vid=vid))
    if ext in ("mp4","webm"):
        return redirect(url_for("stream", vid=vid))
    return redirect(url_for("remux", vid=vid))

def _probe_streams(path):
    try:
        p = subprocess.run(
            ["ffprobe","-v","error","-select_streams","v:0,a:0","-show_entries","stream=codec_name,codec_type,width,height","-of","json", path],
            capture_output=True, text=True, timeout=int(os.environ.get("MINI_FFPROBE_TIMEOUT","10"))
        )
        if p.returncode == 0 and p.stdout:
            jd = json.loads(p.stdout)
            v = next((s for s in jd.get("streams",[]) if s.get("codec_type")=="video"), {})
            a = next((s for s in jd.get("streams",[]) if s.get("codec_type")=="audio"), {})
            return v.get("codec_name",""), a.get("codec_name",""), v.get("width"), v.get("height")
    except Exception as e:
        LOG.warning("ffprobe failed: %s", e)
    return "", "", None, None

def _gen_ffmpeg(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        while True:
            chunk = p.stdout.read(64*1024)
            if not chunk:
                break
            yield chunk
    finally:
        try:
            p.kill()
        except Exception:
            pass

@app.route("/remux/<vid>")
def remux(vid):
    if not auth_required():
        return redirect(url_for("login"))
    try:
        ridx, rel = id_to_parts(vid)
    except Exception:
        abort(404)
    if ridx < 0 or ridx >= len(MEDIA_DIRS):
        abort(404)
    full = os.path.normpath(os.path.join(MEDIA_DIRS[ridx], rel))
    if not os.path.exists(full):
        abort(404)
    vcodec, acodec, w, h = _probe_streams(full)
    out_args = ["-movflags","+frag_keyframe+empty_moov","-f","mp4","-"]
    base_cmd = ["ffmpeg","-loglevel","error","-nostdin","-y","-i", full]
    if vcodec in ("h264","avc1"):
        vpart = ["-c:v","copy"]
        apart = ["-c:a","copy"] if acodec in ("aac","mp3","mp2","mp4a","mpga") else ["-c:a","aac","-b:a","160k"]
        cmd = base_cmd + vpart + apart + out_args
    else:
        if not ALLOW_TRANSCODE:
            return jsonify(ok=False, error="unsupported_codec", detail={"video_codec":vcodec,"audio_codec":acodec,"hint":"Set MINI_TRANSCODE=1 to enable H.264/AAC on-the-fly."}), 415
        vf = []
        try:
            if w and h and (w>1280 or h>720):
                vf = ["-vf","scale='min(1280,iw)':-2"]
        except Exception:
            pass
        cmd = base_cmd + ["-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p"] + vf + ["-c:a","aac","-b:a","160k"] + out_args
    LOG.info("ffmpeg cmd: %s", " ".join(cmd))
    resp = app.response_class(_gen_ffmpeg(cmd), mimetype="video/mp4", direct_passthrough=True)
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Accept-Ranges"] = "none"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp

@app.route("/watch/<vid>")
def watch(vid):
    if not auth_required():
        return redirect(url_for("login"))
    try:
        ridx, rel = id_to_parts(vid)
    except Exception:
        abort(404)
    if ridx < 0 or ridx >= len(MEDIA_DIRS):
        abort(404)
    full = os.path.normpath(os.path.join(MEDIA_DIRS[ridx], rel))
    if not os.path.exists(full):
        abort(404)

    name = safe_display_name(os.path.basename(full))
    ext = os.path.splitext(full)[1].lower().lstrip('.')
    st = read_state()
    fav = bool((st.get("fav", {}) or {}).get(vid))
    played = bool((st.get("played", {}) or {}).get(vid))
    ut = (st.get("utags", {}) or {}).get(vid, [])
    tags = []
    for it in MEDIA:
        if it.get("id") == vid:
            tags = it.get("tags", [])
            break
    meta = (st.get("meta", {}) or {}).get(vid, {})
    res = f"{meta.get('w')}×{meta.get('h')}" if meta.get("w") and meta.get("h") else ""
    back = request.args.get("back") or "/browse"

    ua = (request.headers.get("User-Agent") or "").lower()
    ff_like = any(x in ua for x in ("firefox","librewolf","waterfox","iceweasel"))
    unsupported_ext = ext in ("mkv","m2ts","avi","flv")

    # Choisir l'URL de lecture intelligemment
    play_url = url_for("stream", vid=vid)
    unsupported = False

    if ff_like and unsupported_ext:
        # On tente le remux/transcode côté serveur
        vcodec, acodec, w, h = _probe_streams(full)
        can_copy = (vcodec in ("h264","avc1")) and (acodec in ("aac","mp3","mp2","mp4a","mpga"))
        if can_copy:
            play_url = url_for("remux", vid=vid)  # remux rapide -> MP4
        else:
            if ALLOW_TRANSCODE:
                play_url = url_for("remux", vid=vid)  # transcode on-the-fly H.264/AAC
            else:
                # Ici, on ne peut pas transcoder -> on prévient l’utilisateur
                unsupported = True
                play_url = None  # on laisse le bandeau de fallback

    return render_template(
        "watch.html",
        vid=vid, name=name, ctype=_ctype_for(full), back=back,
        tags=tags, utags=ut, fav=fav, played=played, res=res,
        play_url=play_url, ext=ext, unsupported=unsupported
    )


# ===== Read-only JSON API (public with optional key) =====
API_READ_KEY = os.environ.get("API_READ_KEY","").strip()

def api_key_ok():
    if not API_READ_KEY:
        return True
    k = request.args.get("key") or request.headers.get("X-Api-Key")
    return (k or "").strip() == API_READ_KEY

@app.route("/api/items", methods=["GET"])
def api_items():
    if not api_key_ok():
        return jsonify(ok=False, error="forbidden"), 403
    root = request.args.get("root")
    tags = set([t for t in (request.args.get("tags","").split(",")) if t])
    items = list(MEDIA)
    if root is not None:
        try:
            ri = int(root)
            items = [i for i in items if str(i.get("root_idx")) == str(ri)]
        except Exception:
            pass
    if tags:
        def normalize_tag(t): return canon_tag(t)
        items = [i for i in items if tags.intersection(set([normalize_tag(t) for t in (i.get("tags") or [])]))]
    return jsonify(ok=True, items=[{k:v for k,v in it.items() if k not in ("path",)} for it in items])

@app.route("/api/tags/popular", methods=["GET"])
def api_tags_popular():
    if not api_key_ok():
        return jsonify(ok=False, error="forbidden"), 403
    root = request.args.get("root")
    items = list(MEDIA)
    if root is not None:
        try:
            ri = int(root)
            items = [i for i in items if str(i.get("root_idx")) == str(ri)]
        except Exception:
            pass
    counts = {}
    for it in items:
        for t in (it.get("tags") or []):
            k = (canon_tag(t) or "").strip().lower()
            if not k:
                continue
            counts[k] = counts.get(k,0)+1
    top = sorted(counts.items(), key=lambda kv:(-kv[1], kv[0]))[:70]
    return jsonify(ok=True, tags=[{"tag":k, "count":v} for k,v in top])

def _dupe_key(it):
    try:
        name = (it.get("name") or "").lower()
        size = int(it.get("size") or 0)
        dur  = float(it.get("duration") or 0)
        return name, size, dur
    except Exception:
        return "",0,0.0

def mark_duplicates(items):
    seen = {}
    for it in items:
        name,size,dur = _dupe_key(it)
        bucket = (round(dur/5.0), round(size/ (1024*1024*20)))
        arr = seen.setdefault(bucket, [])
        arr.append(it)
    for bucket, arr in seen.items():
        if len(arr) < 2:
            continue
        for i in range(len(arr)):
            for j in range(i+1,len(arr)):
                a,b = arr[i], arr[j]
                try:
                    if abs((a.get("duration") or 0) - (b.get("duration") or 0)) <= 5 and \
                       abs((a.get("size") or 0) - (b.get("size") or 0)) <= int(0.02*(a.get("size") or 1)+1):
                        an = (a.get("name") or "").lower()
                        bn = (b.get("name") or "").lower()
                        if an[:8]==bn[:8] or len(set(an.replace('_',' ').split()) & set(bn.replace('_',' ').split()))>=2:
                            a["dupe"]=True; b["dupe"]=True
                except Exception:
                    pass
    return items

# --- Maintenance panel ---
@app.route("/maintenance", methods=["GET"])
def maintenance():
    if not auth_required():
        return redirect(url_for("login"))
    return render_template("maintenance.html", auth=AUTH_ENABLED, user=session.get("user"))

# --- Full rescan (async + journal) ---
@app.route("/api/maintenance/rescan", methods=["POST"])
def api_maintenance_rescan():
    if ratelimited("maint_rescan_full_"+(request.remote_addr or "x")):
        return jsonify(ok=False, error="rate_limited"), 429
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401

    with SCAN_LOCK:
        if SCAN_STATE.get("running"):
            return jsonify(ok=False, error="already_running"), 409

    def _job():
        t0 = time.time()
        try:
            SCAN_STATE.update({"kind":"full","message":"Scan complet en cours…","progress":10, "running":True})
            scan_media()
            SCAN_STATE["progress"] = 95
            took = int((time.time()-t0)*1000)
            _log_event("rescan_full", items=len(MEDIA), changed=None, took_ms=took)
            SCAN_STATE.update({"message":"Scan terminé","progress":100})
        except Exception as e:
            SCAN_STATE.update({"message":f"Erreur: {e}"})
        finally:
            SCAN_STATE["running"] = False
            SCAN_STATE["finished"] = int(time.time())

    with SCAN_LOCK:
        SCAN_STATE.update({
            "running": True, "started": int(time.time()),
            "finished": 0, "kind": "full", "progress": 0, "message": "Démarrage…"
        })
    threading.Thread(target=_job, daemon=True).start()
    return jsonify(ok=True, started=True), 202

@app.route("/api/maintenance/progress", methods=["GET"])
def api_maint_progress():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    st = {
        "running": bool(SCAN_STATE.get("running")),
        "progress": int(SCAN_STATE.get("progress", 0)),
        "message": SCAN_STATE.get("message", ""),
        "kind": SCAN_STATE.get("kind", ""),
        "started": SCAN_STATE.get("started", 0),
        "finished": SCAN_STATE.get("finished", 0),
    }
    return jsonify(ok=True, **st)

@app.route("/api/maintenance/purge_thumbs", methods=["POST"])
def api_maintenance_purge_thumbs():
    if ratelimited("maint_purge_thumbs_"+(request.remote_addr or "x")):
        return jsonify(ok=False, error="rate_limited"), 429
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    try:
        cnt = 0
        if os.path.isdir(THUMB_DIR):
            for fn in os.listdir(THUMB_DIR):
                if fn.endswith(".jpg"):
                    try:
                        os.remove(os.path.join(THUMB_DIR, fn)); cnt += 1
                    except Exception:
                        pass
        _log_event("purge_thumbs", removed=cnt)
        return jsonify(ok=True, removed=cnt)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.after_request
def add_headers(resp):
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return resp

@app.route("/api/maintenance/journal", methods=["GET"])
def api_maint_journal():
    if not auth_required():
        return jsonify(ok=False, error="auth"), 401
    ev = _load_json(EVENTS_LOG, [])
    thumbs = 0
    try:
        if os.path.isdir(THUMB_DIR):
            thumbs = sum((os.path.getsize(os.path.join(THUMB_DIR,f)) for f in os.listdir(THUMB_DIR) if f.endswith(".jpg")), 0)
    except Exception:
        pass
    return jsonify(ok=True, events=ev[-50:], thumbs_bytes=thumbs)

# (Optionnel: helpers)
def short_file_hash(path, limit=1024*1024):
    try:
        h = hashlib.sha1()
        with open(path,'rb') as f:
            chunk = f.read(limit)
            if chunk: h.update(chunk)
        return h.hexdigest()[:12]
    except Exception:
        return ""

def ensure_thumbs_background():
    pass

# Initial scan + autoscan thread
scan_media()
try:
    if AUTOSCAN and SCAN_INTERVAL > 0:
        t_autoscan = threading.Thread(target=_autoscan_loop, daemon=True)
        t_autoscan.start()
        LOG.info("Auto-refresh actif (intervalle: %ss)", SCAN_INTERVAL)
except Exception as _e:
    LOG.warning("Impossible de démarrer l'auto-refresh: %s", _e)

def ensure_tags():
    try:
        iters = MEDIA
    except Exception:
        return
    for it in iters:
        if it.get('kind') == 'video' and not it.get('tags'):
            it['tags'] = tagify(it.get('name',''))

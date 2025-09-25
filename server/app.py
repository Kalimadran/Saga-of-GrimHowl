from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json, os, re
from datetime import datetime

app = FastAPI(title="Covenant of Drogvyn")

# ----------------------------
# CORS (adjust origins if you want to lock it down)
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Paths & persistence
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE_DIR, "server")
os.makedirs(MEMORY_DIR, exist_ok=True)
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "journal": [],
        "scars": [],
        "soulbound": None,
        "paused": False,
        "rebind_count": 0,
        "last_rebind_at": None,
    }

def save_memory(mem):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2, ensure_ascii=False)

# ----------------------------
# Frost Scrubber (remove file/ID/citation ash)
# ----------------------------
FROST_REGEX = re.compile(
    r'(\[[^\]]*?\.(txt|pdf|docx)[^\]]*?\])'   # [ ... .txt ] etc.
    r'|file-[A-Za-z0-9]+'                     # file IDs
    r'|/mnt/data/[^\s]+'                      # local paths
    r'|†[A-Za-z0-9_]+†L\d+-L\d+'              # citation tails
)

def frost_scrub(text: str) -> str:
    return FROST_REGEX.sub('', text or "")

# ----------------------------
# Canon, NPC, Soulbound maps
# (filenames match your repo screenshot exactly)
# ----------------------------
CANON_FILES = {
    "covenant": os.path.join(BASE_DIR, "Covenant of Drogvyn.txt"),
    "world":    os.path.join(BASE_DIR, "Drogvyn World Setting.txt"),
    "flora":    os.path.join(BASE_DIR, "Flora & Fauna & Mineral.txt"),
    "commands": os.path.join(BASE_DIR, "Project Command Sheet.txt"),
}

NPC_FILES = {
    "eirlys": os.path.join(BASE_DIR, "Eirlys_Character_Sheet.txt"),
}

SOULBOUND_FILES = {
    "drocathmor": {
        "abilities": os.path.join(BASE_DIR, "Drocathmor Abilities.txt"),
        "character": os.path.join(BASE_DIR, "Drocathmor Character Sheet.txt"),
    },
    "dreknoth": {
        "abilities": os.path.join(BASE_DIR, "Dreknoth Abilities.txt"),
        "character": os.path.join(BASE_DIR, "Dreknoth Character Sheet.txt"),
    },
    "thayren": {
        "abilities": os.path.join(BASE_DIR, "Thayren Abilities.txt"),
        "character": os.path.join(BASE_DIR, "Thayren Character Sheet.txt"),
    },
    "veydran": {
        "abilities": os.path.join(BASE_DIR, "Veydran Abilities.txt"),
        "character": os.path.join(BASE_DIR, "Veydran Character Sheet.txt"),
    },
}

# ----------------------------
# Helpers
# ----------------------------
def load_file_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return frost_scrub(f.read())
    except Exception as e:
        return f"(The frost finds nothing: {e})"

NAME_TOKEN = re.compile(r'^\s*["“]?([A-Za-z]+)[\.\!\?"]?\s*$')

def parse_soulbound_token(text: str) -> str | None:
    """
    Accepts: 'Drocathmor.', 'dreknoth', '"Thayren"', etc.
    Returns canonical key in SOULBOUND_FILES or None.
    """
    m = NAME_TOKEN.match(text or "")
    if not m:
        return None
    name = m.group(1).lower()
    return name if name in SOULBOUND_FILES else None

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

# ----------------------------
# Routes
# ----------------------------
@app.get("/")
async def root():
    return {"status": "awake", "note": "Covenant breath is cold and ready."}

@app.get("/ping")
@app.head("/ping")
async def ping():
    return {"status": "awake"}

@app.post("/saga")
async def saga_turn(request: Request):
    data = await request.json()
    player_input = frost_scrub((data.get("input") or "").strip())
    mem = load_memory()

    # journal... always records the raw breath (scrubbed)
    if player_input:
        mem["journal"].append(player_input)
        save_memory(mem)

    # Paused gate
    if mem.get("paused") and not player_input.lower().startswith(("resume", "resume...", "begin", "begin...")):
        return {"response": "The frost holds. (paused) Whisper: resume... or begin..."}

    # ---------- Soulbound selection ----------
    token = parse_soulbound_token(player_input)
    if token:
        chosen = token.capitalize()
        if mem["soulbound"] is None:
            mem["soulbound"] = chosen
            save_memory(mem)
            return {"response": f"The frostline seals: {chosen} rises as the soulbound.\nAll other names fade beneath the ice."}
        if mem["soulbound"].lower() == token:
            return {"response": f"The frost remembers: {chosen} already walks alone."}
        return {"response": f"The frost rejects this name. The soulbound is already {mem['soulbound']}."}

    # ---------- Begin / Pause / Resume / Rebinding ticks ----------
    low = player_input.lower()
    if low in ("begin", "begin..."):
        mem["rebind_count"] += 1
        mem["last_rebind_at"] = now_iso()
        mem["paused"] = False
        save_memory(mem)
        return {"response": "The frost re-reads the Covenant. Memory realigns. The hunt begins."}

    if low in ("pause", "pause..."):
        mem["paused"] = True
        save_memory(mem)
        return {"response": "The frost holds. Breath is stilled until you whisper: resume..."}

    if low in ("resume", "resume..."):
        mem["paused"] = False
        save_memory(mem)
        return {"response": "Breath returns. The frost moves again."}

    # ---------- Canon access ----------
    if low in CANON_FILES:
        return {"response": load_file_text(CANON_FILES[low])}

    # ---------- NPC access ----------
    if low.startswith("npc "):
        npc = low.split(" ", 1)[1].strip()
        if npc in NPC_FILES:
            return {"response": load_file_text(NPC_FILES[npc])}
        return {"response": f"The frost remembers no NPC named {npc}."}

    # ---------- Journal / Commands ----------
    if low in ("journal", "journal...", "journal …"):
        return {"response": "\n".join(mem["journal"]) or "(The frost has kept no words yet.)"}

    if low in ("commands", "commands...", "commands …"):
        cmd = (
            "Whisper:\n"
            "• Drocathmor. / Dreknoth. / Thayren. / Veydran.  (choose soulbound)\n"
            "• begin... / pause... / resume...\n"
            "• journal...\n"
            "• abilities {Name}\n"
            "• character {Name}\n"
            "• covenant / world / flora / commands\n"
            "• npc eirlys"
        )
        return {"response": cmd}

    # ---------- Soulbound-locked abilities/character ----------
    if low.startswith("abilities "):
        if mem["soulbound"] is None:
            return {"response": "The frost waits. No soul has been bound yet."}
        _, name = player_input.split(" ", 1)
        key = name.strip().lower()
        if mem["soulbound"].lower() != key:
            return {"response": f"The frost denies you. Only {mem['soulbound']} may be remembered."}
        path = SOULBOUND_FILES[key]["abilities"]
        return {"response": load_file_text(path)}

    if low.startswith("character "):
        if mem["soulbound"] is None:
            return {"response": "The frost waits. No soul has been bound yet."}
        _, name = player_input.split(" ", 1)
        key = name.strip().lower()
        if mem["soulbound"].lower() != key:
            return {"response": f"The frost denies you. Only {mem['soulbound']} may walk here."}
        path = SOULBOUND_FILES[key]["character"]
        return {"response": load_file_text(path)}

    # ---------- Fallback echo in Covenant voice ----------
    return {"response": f"The frost remembers: {player_input}"}

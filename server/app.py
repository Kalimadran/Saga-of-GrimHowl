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
# Frost Scrubber
# ----------------------------
FROST_REGEX = re.compile(
    r'(\[[^\]]*?\.(txt|pdf|docx)[^\]]*?\])'   # any bracketed file refs with extensions
    r'|(\[[^\]]*?\])'                         # any other bracketed tags
    r'|file-[A-Za-z0-9_-]+'                   # file-IDs
    r'|/mnt/data/[^\s]+'                      # path fragments
    r'|†[A-Za-z0-9_]+†L\d+-L\d+',             # citation tokens
    flags=re.IGNORECASE
)

def frost_scrub(text: str) -> str:
    cleaned = FROST_REGEX.sub('', text or "")
    return cleaned

# ----------------------------
# Canon, NPC, Soulbound maps
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
def load_file_text(path: str, label: str = "file") -> str:
    if not os.path.exists(path):
        return f"(The frost remembers no {label} here.)"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return frost_scrub(f.read())
    except Exception:
        return f"(The frost cannot read the {label}.)"

NAME_TOKEN = re.compile(r'^\s*["“]?([A-Za-z]+)[\.\!\?"]?\s*$')
def parse_soulbound_token(text: str) -> str | None:
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

    if player_input:
        mem["journal"].append(player_input)
        save_memory(mem)

    if mem.get("paused") and not player_input.lower().startswith(("resume", "resume...", "begin", "begin...")):
        return {"response": frost_scrub("The frost holds. (paused) Whisper: resume... or begin...")}

    # Soulbound selection
    token = parse_soulbound_token(player_input)
    if token:
        chosen = token.capitalize()
        if mem["soulbound"] is None:
            mem["soulbound"] = chosen
            save_memory(mem)
            return {"response": frost_scrub(f"The frostline seals: {chosen} rises as the soulbound.\nAll other names fade beneath the ice.")}
        if mem["soulbound"].lower() == token:
            return {"response": frost_scrub(f"The frost remembers: {chosen} already walks alone.")}
        return {"response": frost_scrub(f"The frost rejects this name. The soulbound is already {mem['soulbound']}.")}

    # Begin / Pause / Resume
    low = player_input.lower()
    if low in ("begin", "begin..."):
        mem["rebind_count"] += 1
        mem["last_rebind_at"] = now_iso()
        mem["paused"] = False
        save_memory(mem)
        return {"response": frost_scrub("The frost re-reads the Covenant. Memory realigns. The hunt begins.")}
    if low in ("pause", "pause..."):
        mem["paused"] = True
        save_memory(mem)
        return {"response": frost_scrub("The frost holds. Breath is stilled until you whisper: resume...")}
    if low in ("resume", "resume..."):
        mem["paused"] = False
        save_memory(mem)
        return {"response": frost_scrub("Breath returns. The frost moves again.")}

    # Canon access
    if low in CANON_FILES:
        return {"response": frost_scrub(load_file_text(CANON_FILES[low], low))}

    # NPC access
    if low.startswith("npc "):
        npc = low.split(" ", 1)[1].strip()
        if npc in NPC_FILES:
            return {"response": frost_scrub(load_file_text(NPC_FILES[npc], f"NPC {npc}"))}
        return {"response": frost_scrub(f"The frost remembers no NPC named {npc}.")}

    # Journal / Commands
    if low.startswith("journal"):
        return {"response": frost_scrub("\n".join(mem["journal"]) or "(The frost has kept no words yet.)")}
    if low.startswith("commands"):
        cmd = (
            "Whisper:\n"
            "• Drocathmor. / Dreknoth. / Thayren. / Veydran.\n"
            "• begin... / pause... / resume...\n"
            "• journal...\n"
            "• abilities {Name}\n"
            "• character {Name}\n"
            "• covenant / world / flora / commands\n"
            "• npc eirlys"
        )
        return {"response": frost_scrub(cmd)}

    # Abilities
    if low.startswith("abilities "):
        if mem["soulbound"] is None:
            return {"response": frost_scrub("The frost waits. No soul has been bound yet.")}
        _, name = player_input.split(" ", 1)
        token = parse_soulbound_token(name)
        if not token or mem["soulbound"].lower() != token:
            return {"response": frost_scrub(f"The frost denies you. Only {mem['soulbound']} may be remembered.")}
        return {"response": frost_scrub(load_file_text(SOULBOUND_FILES[token]["abilities"], "abilities"))}

    # Character
    if low.startswith("character "):
        if mem["soulbound"] is None:
            return {"response": frost_scrub("The frost waits. No soul has been bound yet.")}
        _, name = player_input.split(" ", 1)
        token = parse_soulbound_token(name)
        if not token or mem["soulbound"].lower() != token:
            return {"response": frost_scrub(f"The frost denies you. Only {mem['soulbound']} may walk here.")}
        return {"response": frost_scrub(load_file_text(SOULBOUND_FILES[token]["character"], "character sheet"))}

    # Default echo
    return {"response": frost_scrub(f"The frost remembers: {player_input}")}

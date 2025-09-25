from fastapi import FastAPI, Request
import json, os, re   # 🔹 add re for frost scrubber

app = FastAPI()

# --- Frost Scrubber ---
FROST_REGEX = re.compile(
    r'(\[[^\]]*?\.(txt|pdf|docx)[^\]]*?\])'   # citation blocks
    r'|file-[A-Za-z0-9]+'                     # file IDs
    r'|/mnt/data/[^ ]+'                       # paths
    r'|†[A-Za-z0-9_]+†L\d+-L\d+'              # citation tails
)

def frost_scrub(text: str) -> str:
    """Strip filename ash, leaving only marrow."""
    return FROST_REGEX.sub('', text)


# --- Memory file (state) ---
MEMORY_FILE = "server/memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {"journal": [], "scars": [], "soulbound": None}

def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)

# --- File loader ---
def load_file_text(name):
    try:
        with open(name, "r", encoding="utf-8") as f:
            raw_text = f.read()
            return frost_scrub(raw_text)   # 🔹 scrub file content before returning
    except Exception as e:
        return f"(The frost finds nothing: {e})"

# --- Route ---
@app.post("/saga")
async def saga_turn(request: Request):
    data = await request.json()
    player_input = frost_scrub(data.get("input", "").strip())   # 🔹 scrub input immediately

    memory = load_memory()
    memory["journal"].append(player_input)

    # --- Covenant hooks ---
    response = ""

    # Soulbound lock: only one may rise
    soulbound_names = ["drocathmor", "dreknoth", "thayren", "veydran"]

    if player_input.lower() in soulbound_names:
        chosen = player_input[:-1].capitalize()  # strip the dot, capitalize
        if memory["soulbound"] is None:
            memory["soulbound"] = chosen
            response = (
                f"The frostline seals: {chosen} rises as the soulbound.\n"
                f"All other names fade beneath the ice."
            )
        else:
            if memory["soulbound"] == chosen:
                response = f"The frost remembers: {chosen} already walks alone."
            else:
                response = (
                    f"The frost rejects this name. The soulbound is already {memory['soulbound']}."
                )

    elif player_input.lower().startswith("abilities "):
        if memory["soulbound"] is None:
            response = "The frost waits. No soul has been bound yet."
        else:
            parts = player_input.split(" ", 1)
            if len(parts) == 2:
                character = parts[1].strip()
                if character.lower() != memory["soulbound"].lower():
                    response = f"The frost denies you. Only {memory['soulbound']} may be remembered."
                else:
                    filename = f"{character} Abilities.txt"
                    if os.path.exists(filename):
                        response = load_file_text(filename)
                    else:
                        response = f"The frost remembers no abilities for {character}."

    elif player_input.lower().startswith("character "):
        if memory["soulbound"] is None:
            response = "The frost waits. No soul has been bound yet."
        else:
            parts = player_input.split(" ", 1)
            if len(parts) == 2:
                character = parts[1].strip()
                if character.lower() != memory["soulbound"].lower():
                    response = f"The frost denies you. Only {memory['soulbound']} may walk here."
                else:
                    filename = f"{character} Character Sheet.txt"
                    if os.path.exists(filename):
                        response = load_file_text(filename)
                    else:
                        response = f"The frost remembers no character named {character}."

    elif player_input.lower() == "world":
        response = load_file_text("Drogvyn World Setting.txt")

    elif player_input.lower() == "covenant":
        response = load_file_text("Covenant of Drogvyn.txt")

    elif player_input.lower() == "journal":
        response = "\n".join(memory["journal"])

    else:
        response = f"The frost remembers: {player_input}"

    # Scrub output before returning
    clean_output = frost_scrub(response)   # 🔹 cleanse any ash from the response

    save_memory(memory)
    return {"response": clean_output, "memory": memory}

# --- Ping route for uptime checks ---
@app.get("/ping")
@app.head("/ping")
async def ping():
    return {"status": "awake"}

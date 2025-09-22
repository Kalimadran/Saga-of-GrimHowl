from fastapi import FastAPI, Request
import json, os

app = FastAPI()


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
            return f.read()
    except Exception as e:
        return f"(The frost finds nothing: {e})"

# --- Route ---
@app.post("/saga")
async def saga_turn(request: Request):
    data = await request.json()
    player_input = data.get("input", "")

    memory = load_memory()
    memory["journal"].append(player_input)

    # --- Covenant hooks ---
    response = ""

    if player_input.lower().startswith("abilities "):
        parts = player_input.split(" ", 1)
        if len(parts) == 2:
            character = parts[1].strip()
            filename = f"{character} Abilities.txt"
            if os.path.exists(filename):
                response = load_file_text(filename)
            else:
                response = f"The frost remembers no abilities for {character}."

    elif player_input.lower().startswith("character "):
        parts = player_input.split(" ", 1)
        if len(parts) == 2:
            character = parts[1].strip()
            filename = f"{character} Character Sheet.txt"
            if os.path.exists(filename):
                response = load_file_text(filename)
            else:
                response = f"The frost remembers no character named {character}."

    elif player_input.lower() == "world":
        response = load_file_text("Drogvyn World Setting.txt")

    elif player_input.lower() == "journal":
        response = "\n".join(memory["journal"])

    else:
        response = f"The frost remembers: {player_input}"

    save_memory(memory)
    return {"response": response, "memory": memory}

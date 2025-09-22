from fastapi import FastAPI, Request
import json, os

app = FastAPI()

# Memory file (state)
MEMORY_FILE = "server/memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {"journal": [], "scars": [], "soulbound": None}

def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)

@app.post("/saga")
async def saga_turn(request: Request):
    data = await request.json()
    player_input = data.get("input", "")

    memory = load_memory()

    # Here you’d call the GPT API with Covenant + memory + input
    # For now, just simulate:
    response = f"The frost remembers: {player_input}"

    # Update memory (simple example: add to journal)
    memory["journal"].append(player_input)
    save_memory(memory)

    return {"response": response, "memory": memory}

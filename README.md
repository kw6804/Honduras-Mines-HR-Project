# Honduras Mines Map

Interactive visualization of mine locations in Honduras extracted from scanned documents.

---

## Overview

Two scripts:

1. **`extract_coordinates.py`** — reads the scanned document images, uses Claude AI (vision) to extract coordinates and metadata, and saves everything to `mines_data.json`.
2. **`generate_map.py`** — reads `mines_data.json` and produces a standalone `mines_map.html` that anyone can open in a browser.

Only the person running the extraction needs Python and an API key. The final `mines_map.html` file can be shared with and opened by anyone.

---

## Setup (one-time)

### 1. Install Python

Download and install Python 3.10 or newer from https://www.python.org/downloads/

During installation on Windows, check **"Add Python to PATH"**.

### 2. Install required packages

Open a terminal (Command Prompt or PowerShell on Windows, Terminal on Mac/Linux) and run:

```
pip install anthropic folium pyproj
```

### 3. Get an Anthropic API key

The extraction script uses Claude's vision AI, which requires a free API key.

1. Go to https://console.anthropic.com and sign up or log in.
2. Click **API Keys** in the left sidebar.
3. Click **Create Key**, give it a name (e.g. "Honduras Mines"), and copy the key.

### 4. Set the API key as an environment variable

**Windows (Command Prompt):**
```
set ANTHROPIC_API_KEY=your-key-here
```

**Windows (PowerShell):**
```
$env:ANTHROPIC_API_KEY="your-key-here"
```

**Mac / Linux:**
```
export ANTHROPIC_API_KEY="your-key-here"
```

> Note: this only lasts for the current terminal session. To make it permanent, add it to your system environment variables (Windows) or your shell profile file like `~/.zshrc` or `~/.bashrc` (Mac/Linux).

---

## Running the scripts

Open a terminal in the project folder (the folder containing this README), then:

### Step 1 — Extract coordinates

```
python extract_coordinates.py
```

This reads all images from `HONDURAS MINING COORDINATES/`, sends them to Claude, and saves the results to `mines_data.json`. It prints progress for each document.

### Step 2 — Generate the map

```
python generate_map.py
```

This reads `mines_data.json` and creates `mines_map.html`.

### Step 3 — View the map

Open `mines_map.html` in any web browser (double-click the file).

---

## Map features

- **Hover** over any point to see a tooltip with:
  - Document name
  - Vertex/point label (as written in the original document)
  - Original coordinates (as written: Este/Norte, Latitud/Longitud, etc.)
  - Converted decimal coordinates (WGS84)
  - All other extracted metadata (mine name, concession number, owner, date, area, etc.)
- **Layer control** (top-right corner) — toggle individual documents on/off
- **Legend** (bottom-left corner) — color key for each document

---

## Folder structure

```
Honduras-Mines-HR-Project/
├── HONDURAS MINING COORDINATES/
│   ├── #1 SA1 Dictamen RMC .../
│   │   └── Screenshot ....png
│   ├── #2 SA1 Escrito .../
│   │   └── Screenshot ....png
│   └── ...
├── extract_coordinates.py
├── generate_map.py
├── mines_data.json          ← created by extract_coordinates.py
├── mines_map.html           ← created by generate_map.py
└── README.md
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install anthropic folium pyproj` |
| `ANTHROPIC_API_KEY not set` | Follow step 4 above |
| `Folder not found` | Run the scripts from the project root directory |
| A document shows 0 points | Check the terminal output — the note field may explain why |
| Points appear in the ocean | Claude may have misread a digit; open `mines_data.json` and check the raw values |

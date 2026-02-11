# System Data Exporter v3.6

This **No Man's Sky** mod allows you to export detailed information about the current solar system and its planets into structured JSON files.

## Requirements

*   **Python+**
*   **pymhf** https://github.com/monkeyman192/pyMHF
*   **nmspy**: NMS binding library. [NMS.py](https://github.com/monkeyman192/NMS.py).

## Installation

1.  Ensure you have `pymhf` installed and correctly configured for No Man's Sky.
2.  Place the `systemexporter.py` file in your `pymhf` mods folder (usually `GAMEDATA/MODS/` or wherever you configured your scripts).

## Usage and Controls

The mod loads automatically with the game. You can interact with it using the following keys:

*   **`U`**: **Manual Export**. Saves current system data to a new JSON file.
*   **`I`**: **Consolidate Exports**. Merges all JSON files in the `SystemData` folder into an `all_systems.json` file.
*   **`O`**: **Toggle Auto-Export**. Enables or disables automatic export when arriving at a new system. (Status is shown in console/log).
*   **`Y`**: **Debug**. Shows the internal system data structure in the console (useful for development).

## Data Output

Files are generated in a folder named `SystemData` in the same directory as the script.

*   **Individual:** `system_SystemName_YYYYMMDD_HHMMSS.json`
*   **Latest System:** `latest_system.json` (always contains the last exported one).
*   **Consolidated:** `all_systems.json` (generated when pressing `I`).

## JSON Structure

The exported JSON contains:

```json
{
  "timestamp": "...",
  "version": "3.6",
  "sistema": {
    "nombre": "System Name",
    "raza": "Korvax",
    "clase": "Blue",
    "comercio": { ... },
    "conflicto": "Low",
    ...
  },
  "planetas": [
    {
      "nombre": "Planet Name",
      "recursos_basicos_es": ["Cobre", "Parafinio"],
      "generacion": {
        "bioma": "Lush",
        ...
      },
      ...
    }
  ]
}
```
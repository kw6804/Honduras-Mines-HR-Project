"""
extract_coordinates.py
----------------------
Reads scanned document images from "HONDURAS MINING COORDINATES" and uses
Claude Vision to extract mine coordinate data. Outputs mines_data.json.

Usage:
    python extract_coordinates.py
"""

import os
import json
import base64
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Error: 'anthropic' package not installed. Run: pip install anthropic")
    sys.exit(1)

try:
    from pyproj import Transformer
except ImportError:
    print("Error: 'pyproj' package not installed. Run: pip install pyproj")
    sys.exit(1)

# Honduras is almost entirely within UTM Zone 16N
UTM_TO_WGS84 = Transformer.from_crs("EPSG:32616", "EPSG:4326", always_xy=True)

DOCS_FOLDER = Path("HONDURAS MINING COORDINATES")
OUTPUT_FILE = Path("mines_data.json")

EXTRACTION_PROMPT = """Eres un asistente experto en extracción de datos de documentos mineros en Honduras.

Analiza TODAS las imágenes proporcionadas (pertenecen al mismo documento) y extrae TODA la información relevante.

Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta:

{
  "coordinate_system": "UTM" | "geographic" | "unknown",
  "utm_zone": "16N" (si aplica, de lo contrario null),
  "metadata": {
    // Todos los campos que encuentres: nombre de mina, número de licencia/concesión,
    // propietario/titular, fecha, área, municipio, departamento, etc.
    // Usa los nombres de campo tal como aparecen en el documento.
    // Si no hay metadatos claros, usa un objeto vacío {}.
  },
  "points": [
    {
      "label": "etiqueta del vértice/punto tal como aparece (ej: 'V1', 'Punto 1', 'A', etc.)",
      "easting_or_longitude": <número flotante>,
      "northing_or_latitude": <número flotante>,
      "raw_easting": "texto exacto del documento para el valor X/Este/Longitud",
      "raw_northing": "texto exacto del documento para el valor Y/Norte/Latitud"
    }
  ],
  "notes": "cualquier observación sobre calidad de imagen, ambigüedades, o datos faltantes"
}

REGLAS IMPORTANTES:
- Extrae TODOS los puntos de coordenadas sin excepción.
- Si los valores de coordenadas son números grandes (> 100,000) en metros, es UTM → usa "UTM".
- Si son grados decimales o grados/minutos/segundos (Latitud/Longitud), usa "geographic".
- Si están en DMS (ej: 14°30'25"N), conviértelos a decimales en los campos numéricos.
- Honduras normalmente usa UTM Zona 16N; si no se especifica zona, asume 16N.
- Haz tu mejor esfuerzo aunque la imagen no sea perfectamente nítida.
- NO incluyas texto explicativo fuera del JSON. Devuelve SOLO el JSON.
"""


def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def extract_from_folder(client: anthropic.Anthropic, folder_path: Path) -> dict | None:
    png_files = sorted(folder_path.glob("*.png"))
    if not png_files:
        print(f"  No PNG files found — skipping.")
        return None

    print(f"  Sending {len(png_files)} image(s) to Claude...")

    content = []
    for png_path in png_files:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": encode_image(png_path),
            },
        })
    content.append({"type": "text", "text": EXTRACTION_PROMPT})

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if Claude wraps the JSON
    if raw_text.startswith("```"):
        parts = raw_text.split("```")
        raw_text = parts[1]
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)


def convert_to_latlon(data: dict) -> dict:
    """Add decimal latitude/longitude to each point based on coordinate system."""
    coord_sys = data.get("coordinate_system", "unknown").upper()

    for point in data.get("points", []):
        x = point.get("easting_or_longitude")
        y = point.get("northing_or_latitude")

        if x is None or y is None:
            point["latitude"] = None
            point["longitude"] = None
            continue

        if coord_sys == "UTM":
            lon, lat = UTM_TO_WGS84.transform(x, y)
            point["latitude"] = round(lat, 6)
            point["longitude"] = round(lon, 6)
        else:
            # geographic: easting=longitude, northing=latitude
            point["latitude"] = round(y, 6)
            point["longitude"] = round(x, 6)

    return data


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("See README.md for instructions on how to set it up.")
        sys.exit(1)

    if not DOCS_FOLDER.exists():
        print(f"Error: Folder '{DOCS_FOLDER}' not found.")
        print("Make sure you run this script from the project root directory.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    doc_folders = sorted([f for f in DOCS_FOLDER.iterdir() if f.is_dir()])
    print(f"Honduras Mines Coordinate Extractor")
    print(f"{'=' * 40}")
    print(f"Found {len(doc_folders)} document folders.\n")

    all_data = []

    for folder in doc_folders:
        print(f"[{folder.name}]")
        try:
            data = extract_from_folder(client, folder)
            if data is None:
                continue
            data["document_name"] = folder.name
            data = convert_to_latlon(data)
            n_points = len(data.get("points", []))
            coord_sys = data.get("coordinate_system", "unknown")
            print(f"  Extracted {n_points} point(s). Coordinate system: {coord_sys}")
            if data.get("notes"):
                print(f"  Note: {data['notes']}")
            all_data.append(data)
        except json.JSONDecodeError as e:
            print(f"  ERROR parsing JSON response: {e}")
        except Exception as e:
            print(f"  ERROR: {e}")
        print()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    total_points = sum(len(d.get("points", [])) for d in all_data)
    print(f"{'=' * 40}")
    print(f"Complete! {total_points} total points from {len(all_data)} documents.")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"\nNext step: run  python generate_map.py")


if __name__ == "__main__":
    main()

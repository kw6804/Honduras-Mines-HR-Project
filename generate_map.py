"""
generate_map.py
---------------
Reads mines_data.json and generates an interactive mines_map.html
that can be opened in any web browser.

Usage:
    python generate_map.py
"""

import json
import sys
from pathlib import Path

try:
    import folium
    from folium.plugins import MarkerCluster
except ImportError:
    print("Error: 'folium' package not installed. Run: pip install folium")
    sys.exit(1)

DATA_FILE = Path("mines_data.json")
OUTPUT_FILE = Path("mines_map.html")

# One distinct color per document (up to 14)
COLORS = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
    "#a65628", "#f781bf", "#999999", "#1b9e77", "#d95f02",
    "#7570b3", "#e7298a", "#66a61e", "#e6ab02",
]


def format_value(val) -> str:
    if val is None:
        return "—"
    return str(val)


def build_tooltip_html(doc_name: str, point: dict, metadata: dict, coord_sys: str) -> str:
    """Build a styled HTML table for a map marker tooltip."""

    def row(label, value):
        return (
            f'<tr>'
            f'<td style="padding:3px 8px 3px 6px;color:#555;white-space:nowrap;">{label}</td>'
            f'<td style="padding:3px 6px;font-weight:600;">{format_value(value)}</td>'
            f'</tr>'
        )

    def section(title):
        return (
            f'<tr><td colspan="2" style="background:#e8f5e9;color:#2e7d32;'
            f'font-weight:700;padding:4px 6px;font-size:11px;letter-spacing:0.5px;">'
            f'{title}</td></tr>'
        )

    rows = [
        f'<tr><th colspan="2" style="background:#2e7d32;color:white;padding:7px 10px;'
        f'font-size:13px;font-weight:700;text-align:left;">{doc_name}</th></tr>'
    ]

    # Point label
    if point.get("label"):
        rows.append(row("Vértice / Punto", point["label"]))

    # Original coordinates
    rows.append(section("COORDENADAS ORIGINALES"))
    if coord_sys == "UTM":
        rows.append(row("Este (X)", point.get("raw_easting")))
        rows.append(row("Norte (Y)", point.get("raw_northing")))
        rows.append(row("Sistema", f"UTM {point.get('utm_zone', '16N')} (aprox.)"))
    else:
        rows.append(row("Longitud", point.get("raw_easting")))
        rows.append(row("Latitud", point.get("raw_northing")))
        rows.append(row("Sistema", "Geográfico (grados)"))

    # Converted decimal coordinates
    lat = point.get("latitude")
    lon = point.get("longitude")
    if lat is not None and lon is not None:
        rows.append(section("COORDENADAS DECIMALES (WGS84)"))
        rows.append(row("Latitud", f"{lat:.6f}°"))
        rows.append(row("Longitud", f"{lon:.6f}°"))

    # Document metadata
    if metadata:
        rows.append(section("INFORMACIÓN DEL DOCUMENTO"))
        for key, val in metadata.items():
            if val not in (None, "", {}):
                rows.append(row(key, val))

    html = (
        '<div style="font-family:Arial,sans-serif;font-size:12px;line-height:1.4;">'
        '<table style="border-collapse:collapse;min-width:270px;max-width:400px;">'
        + "".join(rows)
        + "</table></div>"
    )
    return html


def add_legend(m: folium.Map, doc_names: list[str], colors: list[str]) -> None:
    """Inject a floating legend into the Folium map."""
    items = "".join(
        f'<div style="margin:3px 0;">'
        f'<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
        f'background:{color};margin-right:7px;vertical-align:middle;border:1px solid #999;"></span>'
        f'<span style="vertical-align:middle;font-size:12px;">{name}</span></div>'
        for name, color in zip(doc_names, colors)
    )
    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
                padding:12px 16px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.3);
                font-family:Arial,sans-serif;max-height:80vh;overflow-y:auto;">
        <div style="font-weight:700;font-size:13px;margin-bottom:8px;
                    color:#2e7d32;border-bottom:1px solid #ccc;padding-bottom:4px;">
            Documentos
        </div>
        {items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))


def main():
    if not DATA_FILE.exists():
        print(f"Error: {DATA_FILE} not found. Run extract_coordinates.py first.")
        sys.exit(1)

    with open(DATA_FILE, encoding="utf-8") as f:
        all_data = json.load(f)

    if not all_data:
        print("No data found in mines_data.json.")
        sys.exit(1)

    # Honduras center
    m = folium.Map(location=[14.8, -86.8], zoom_start=8, tiles="OpenStreetMap")

    doc_names = []
    used_colors = []
    plotted = 0
    skipped = 0
    warnings = []

    for i, doc in enumerate(all_data):
        doc_name = doc.get("document_name", f"Documento {i + 1}")
        coord_sys = doc.get("coordinate_system", "unknown").upper()
        metadata = doc.get("metadata", {})
        color = COLORS[i % len(COLORS)]

        # Add UTM zone to each point for tooltip use
        for point in doc.get("points", []):
            point["utm_zone"] = doc.get("utm_zone")

        feature_group = folium.FeatureGroup(name=doc_name, show=True)
        has_points = False

        for point in doc.get("points", []):
            lat = point.get("latitude")
            lon = point.get("longitude")

            if lat is None or lon is None:
                skipped += 1
                continue

            # Sanity check: rough bounding box for Honduras
            if not (-90.5 < lon < -83.0 and 12.5 < lat < 16.5):
                msg = (
                    f"  WARNING: '{doc_name}' — point '{point.get('label', '?')}' "
                    f"has coordinates ({lat}, {lon}) outside Honduras. Skipping."
                )
                warnings.append(msg)
                skipped += 1
                continue

            tooltip_html = build_tooltip_html(doc_name, point, metadata, coord_sys)

            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                tooltip=folium.Tooltip(tooltip_html, sticky=True),
            ).add_to(feature_group)

            plotted += 1
            has_points = True

        feature_group.add_to(m)

        if has_points:
            doc_names.append(doc_name)
            used_colors.append(color)

    # Layer control so users can toggle documents on/off
    folium.LayerControl(collapsed=False).add_to(m)

    add_legend(m, doc_names, used_colors)

    m.save(str(OUTPUT_FILE))

    print(f"Map generated: {OUTPUT_FILE}")
    print(f"  Points plotted : {plotted}")
    if skipped:
        print(f"  Points skipped : {skipped}")
    for w in warnings:
        print(w)
    print(f"\nOpen {OUTPUT_FILE} in any web browser to view the interactive map.")


if __name__ == "__main__":
    main()

"""Ortsbezug & Entfernung (Luftlinie) — offline, reine stdlib.

- Erkennt in einem Deal-Text (Titel/Beschreibung) einen bekannten Ort aus einer
  eingebauten Städte-Tabelle (DE/AT/CH inkl. Bergbahn-/Genuss-Orten).
- Geocodiert den Startort des Nutzers ("50667 Köln", "München" oder "lat,lon").
- Rechnet Luftlinie (Haversine) in km und baut einen Maps-Routen-Link.

Keine Netz-/API-Abhängigkeit: Koordinaten sind grob (Stadtzentrum), was für einen
Radius-Filter völlig genügt. Für Orte ohne Tabellen-Treffer greift bei deutschen
PLZ ein grober Regions-Fallback (erste PLZ-Ziffer).
"""
from __future__ import annotations

import math
import re

from analyze import keyword_matches, normalize

# --------------------------------------------------------------------------- #
# Städte-Tabelle: normalisierter Name -> (Anzeigename, lat, lon).
# Deckt die Orte ab, die in den Quellen real vorkommen (mydays-Event-Städte,
# Schweizer Bergbahnen, Tourismus-Ziele). Erweiterbar.
# --------------------------------------------------------------------------- #
_RAW_PLACES = [
    # Deutschland – Großstädte
    ("Berlin", 52.520, 13.405), ("Hamburg", 53.551, 9.994),
    ("München", 48.137, 11.575), ("Köln", 50.938, 6.960),
    ("Frankfurt", 50.110, 8.682), ("Stuttgart", 48.775, 9.183),
    ("Düsseldorf", 51.228, 6.773), ("Dortmund", 51.514, 7.466),
    ("Essen", 51.458, 7.014), ("Bremen", 53.079, 8.801),
    ("Dresden", 51.050, 13.738), ("Leipzig", 51.340, 12.375),
    ("Hannover", 52.375, 9.732), ("Nürnberg", 49.452, 11.077),
    ("Duisburg", 51.435, 6.762), ("Bochum", 51.481, 7.216),
    ("Wuppertal", 51.256, 7.150), ("Bonn", 50.735, 7.100),
    ("Münster", 51.960, 7.626), ("Karlsruhe", 49.007, 8.404),
    ("Mannheim", 49.487, 8.466), ("Augsburg", 48.370, 10.898),
    ("Wiesbaden", 50.082, 8.240), ("Gelsenkirchen", 51.517, 7.086),
    ("Braunschweig", 52.268, 10.526), ("Kiel", 54.323, 10.135),
    ("Aachen", 50.776, 6.084), ("Halle", 51.482, 11.970),
    ("Magdeburg", 52.120, 11.627), ("Freiburg", 47.999, 7.842),
    ("Krefeld", 51.334, 6.564), ("Lübeck", 53.866, 10.687),
    ("Mainz", 49.992, 8.247), ("Erfurt", 50.984, 11.029),
    ("Rostock", 54.092, 12.099), ("Kassel", 51.312, 9.480),
    ("Potsdam", 52.400, 13.060), ("Saarbrücken", 49.240, 6.997),
    ("Heidelberg", 49.398, 8.672), ("Würzburg", 49.790, 9.953),
    ("Regensburg", 49.013, 12.101), ("Ulm", 48.400, 9.987),
    ("Trier", 49.750, 6.637), ("Koblenz", 50.360, 7.589),
    ("Konstanz", 47.660, 9.175), ("Osnabrück", 52.279, 8.047),
    ("Bielefeld", 52.030, 8.530), ("Wolfsburg", 52.420, 10.790),
    ("Göttingen", 51.540, 9.930), ("Oldenburg", 53.144, 8.214),
    ("Baden-Baden", 48.760, 8.240), ("Garmisch-Partenkirchen", 47.492, 11.096),
    ("Tegernsee", 47.710, 11.760), ("Sylt", 54.900, 8.330),
    ("Rügen", 54.400, 13.400), ("Usedom", 53.960, 14.050),
    ("Waren", 53.520, 12.680), ("Nürburgring", 50.335, 6.947),
    # Österreich
    ("Wien", 48.208, 16.373), ("Salzburg", 47.810, 13.055),
    ("Innsbruck", 47.269, 11.404), ("Graz", 47.070, 15.440),
    ("Linz", 48.306, 14.286), ("Klagenfurt", 46.620, 14.310),
    ("Bregenz", 47.503, 9.747), ("Kitzbühel", 47.446, 12.392),
    # Schweiz – Städte
    ("Zürich", 47.377, 8.540), ("Bern", 46.948, 7.447),
    ("Basel", 47.560, 7.588), ("Genf", 46.204, 6.143),
    ("Lausanne", 46.520, 6.630), ("Luzern", 47.050, 8.310),
    ("St. Gallen", 47.420, 9.380), ("Lugano", 46.000, 8.950),
    ("Montreux", 46.430, 6.910), ("Chur", 46.850, 9.530),
    # Schweiz – Bergbahnen / Alpen-Genussorte
    ("Zermatt", 46.020, 7.749), ("Grindelwald", 46.624, 8.041),
    ("Interlaken", 46.686, 7.863), ("Jungfraujoch", 46.547, 7.980),
    ("St. Moritz", 46.490, 9.838), ("Davos", 46.800, 9.830),
    ("Engelberg", 46.820, 8.400), ("Andermatt", 46.630, 8.594),
    ("Titlis", 46.770, 8.440), ("Gornergrat", 45.983, 7.786),
    ("Pilatus", 46.980, 8.250), ("Rigi", 47.050, 8.485),
    ("Säntis", 47.249, 9.343), ("Schilthorn", 46.556, 7.835),
    ("Stanserhorn", 46.920, 8.340),
    # Südbaden / Schwarzwald / Bodensee (Umland Freiburg)
    ("Offenburg", 48.474, 7.945), ("Lörrach", 47.615, 7.661),
    ("Müllheim", 47.808, 7.630), ("Emmendingen", 48.121, 7.848),
    ("Waldkirch", 48.093, 7.964), ("Bad Krozingen", 47.918, 7.699),
    ("Breisach", 48.028, 7.583), ("Titisee", 47.903, 8.152),
    ("Todtnau", 47.829, 7.945), ("Feldberg", 47.867, 8.004),
    ("Schluchsee", 47.817, 8.166), ("Villingen-Schwenningen", 48.061, 8.459),
    ("Friedrichshafen", 47.657, 9.480), ("Ravensburg", 47.782, 9.612),
    # Baden-Württemberg / weitere Süd-Städte
    ("Tübingen", 48.520, 9.058), ("Reutlingen", 48.492, 9.211),
    ("Esslingen", 48.740, 9.310), ("Heilbronn", 49.142, 9.211),
    ("Pforzheim", 48.891, 8.698), ("Göppingen", 48.703, 9.652),
    # Bayern
    ("Fürth", 49.478, 10.990), ("Erlangen", 49.590, 11.004),
    ("Bamberg", 49.891, 10.887), ("Bayreuth", 49.948, 11.578),
    ("Ingolstadt", 48.766, 11.425), ("Rosenheim", 47.856, 12.123),
    ("Landshut", 48.537, 12.152), ("Passau", 48.567, 13.431),
    ("Kempten", 47.727, 10.314), ("Oberstdorf", 47.409, 10.279),
    ("Füssen", 47.571, 10.702), ("Berchtesgaden", 47.630, 13.004),
    ("Bad Tölz", 47.760, 11.556), ("Mittenwald", 47.444, 11.261),
    # Hessen / Mitte
    ("Darmstadt", 49.872, 8.651), ("Offenbach", 50.096, 8.766),
    ("Fulda", 50.555, 9.681), ("Gießen", 50.587, 8.678),
    ("Marburg", 50.802, 8.767), ("Wetzlar", 50.560, 8.505),
    # Rheinland-Pfalz / Saarland
    ("Kaiserslautern", 49.440, 7.749), ("Ludwigshafen", 49.481, 8.446),
    ("Speyer", 49.317, 8.441), ("Worms", 49.634, 8.360),
    # NRW (weitere)
    ("Leverkusen", 51.030, 6.983), ("Neuss", 51.198, 6.687),
    ("Oberhausen", 51.470, 6.851), ("Solingen", 51.171, 7.085),
    ("Remscheid", 51.178, 7.190), ("Recklinghausen", 51.614, 7.198),
    ("Bottrop", 51.523, 6.923), ("Mönchengladbach", 51.180, 6.442),
    ("Hagen", 51.361, 7.463), ("Hamm", 51.679, 7.816),
    ("Siegen", 50.875, 8.024), ("Paderborn", 51.719, 8.754),
    ("Gütersloh", 51.906, 8.379), ("Minden", 52.289, 8.915),
    # Ost / Nord (weitere)
    ("Jena", 50.927, 11.589), ("Chemnitz", 50.833, 12.921),
    ("Zwickau", 50.718, 12.496), ("Cottbus", 51.760, 14.334),
    ("Schwerin", 53.636, 11.401), ("Flensburg", 54.782, 9.437),
    ("Lüneburg", 53.247, 10.414), ("Celle", 52.625, 10.081),
    ("Hildesheim", 52.155, 9.958), ("Bremerhaven", 53.540, 8.580),
    ("Wilhelmshaven", 53.529, 8.113),
    # Küsten- / Ferien-Orte
    ("Norderney", 53.707, 7.156), ("Borkum", 53.578, 6.663),
    ("Timmendorfer Strand", 54.006, 10.774), ("Willingen", 51.293, 8.610),
    ("Winterberg", 51.194, 8.531),
    # Österreich (weitere / Alpen)
    ("Villach", 46.611, 13.856), ("St. Pölten", 48.204, 15.625),
    ("Dornbirn", 47.412, 9.744), ("Zell am See", 47.323, 12.797),
    ("Sölden", 46.966, 11.007), ("Ischgl", 47.011, 10.291),
    ("Mayrhofen", 47.166, 11.868), ("Saalbach", 47.390, 12.636),
    ("Bad Gastein", 47.115, 13.134), ("Seefeld", 47.329, 11.188),
    # Schweiz (weitere Städte / Alpen-Resorts)
    ("Winterthur", 47.500, 8.724), ("Fribourg", 46.806, 7.161),
    ("Neuchâtel", 46.992, 6.931), ("Sion", 46.233, 7.360),
    ("Locarno", 46.171, 8.799), ("Thun", 46.758, 7.628),
    ("Biel", 47.137, 7.247), ("Schaffhausen", 47.697, 8.635),
    ("Aarau", 47.391, 8.045), ("Saas-Fee", 46.108, 7.929),
    ("Verbier", 46.096, 7.228), ("Gstaad", 46.472, 7.286),
    ("Wengen", 46.605, 7.922), ("Mürren", 46.559, 7.892),
    ("Arosa", 46.783, 9.680), ("Flims", 46.837, 9.284),
    ("Laax", 46.809, 9.258), ("Crans-Montana", 46.308, 7.481),
    ("Adelboden", 46.494, 7.559), ("Lenzerheide", 46.729, 9.558),
    ("Klosters", 46.869, 9.879), ("Leukerbad", 46.379, 7.627),
]
PLACES = {normalize(name): (name, lat, lon) for name, lat, lon in _RAW_PLACES}

# Grober Regions-Fallback für deutsche PLZ (erste Ziffer -> Regionszentrum).
_PLZ_REGION = {
    "0": (51.10, 13.40), "1": (52.50, 13.40), "2": (53.55, 10.00),
    "3": (52.00, 9.70), "4": (51.40, 7.00), "5": (50.90, 7.00),
    "6": (50.11, 8.68), "7": (48.78, 9.18), "8": (48.14, 11.58),
    "9": (49.45, 11.08),
}


# --------------------------------------------------------------------------- #
# Distanz
# --------------------------------------------------------------------------- #
def haversine(lat1, lon1, lat2, lon2):
    """Luftlinie zwischen zwei Punkten in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


# --------------------------------------------------------------------------- #
# Geocoding
# --------------------------------------------------------------------------- #
def geocode_home(home):
    """Startort -> (lat, lon, label) oder None.

    Akzeptiert 'lat,lon', 'PLZ Ort', 'Ort' oder 'PLZ'. Ort schlägt PLZ-Fallback.
    """
    if not home:
        return None
    s = str(home).strip()

    # 1) Direkte Koordinaten 'lat,lon'
    m = re.fullmatch(r"\s*(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*", s)
    if m:
        return (float(m.group(1)), float(m.group(2)), s)

    # 2) Ortsname aus der Tabelle (PLZ davor wird ignoriert)
    hit = _match_place(s)
    if hit:
        name, lat, lon = hit
        return (lat, lon, name)

    # 3) Grober PLZ-Regions-Fallback (Deutschland)
    mp = re.search(r"\b(\d{5})\b", s)
    if mp:
        lat, lon = _PLZ_REGION[mp.group(1)[0]]
        return (lat, lon, s)
    return None


def _match_place(text):
    """Besten Tabellen-Ort in einem Text finden (längster Namens-Treffer gewinnt)."""
    best = None
    for key, (name, lat, lon) in PLACES.items():
        if keyword_matches(name, text):
            if best is None or len(key) > best[0]:
                best = (len(key), name, lat, lon)
    return (best[1], best[2], best[3]) if best else None


def locate(text):
    """Ort in einem Deal-Text erkennen -> (Anzeigename, lat, lon) oder None."""
    return _match_place(text or "")


def maps_route_url(home_coords, dest_coords):
    """Google-Maps-Navigations-Link von Start zu Ziel (beide (lat, lon))."""
    return ("https://www.google.com/maps/dir/?api=1"
            f"&origin={home_coords[0]},{home_coords[1]}"
            f"&destination={dest_coords[0]},{dest_coords[1]}")

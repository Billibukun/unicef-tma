import csv
import os
from decimal import Decimal
from pathlib import Path

# City → State mapping
CITY_TO_STATE = {
    "Abakaliki": "Ebonyi",
    "Abeokuta": "Ogun",
    "Abuja": "FCT",
    "Ado-Ekiti": "Ekiti",
    "Akure": "Ondo",
    "Asaba": "Delta",
    "Awka": "Anambra",
    "Bauchi": "Bauchi",
    "Benin-City": "Edo",
    "Birnin-Kebbi": "Kebbi",
    "Calabar": "Cross River",
    "Damaturu": "Yobe",
    "Dutse": "Jigawa",
    "Enugu": "Enugu",
    "Gombe": "Gombe",
    "Gusau": "Zamfara",
    "Ibadan": "Oyo",
    "Ikeja": "Lagos",
    "Ilorin": "Kwara",
    "Jalingo": "Taraba",
    "Jos": "Plateau",
    "Kaduna": "Kaduna",
    "Kano": "Kano",
    "Katsina": "Katsina",
    "Lafia": "Nasarawa",
    "Lokoja": "Kogi",
    "Maiduguri": "Borno",
    "Makurdi": "Benue",
    "Minna": "Niger",
    "Osogbo": "Osun",
    "Owerri": "Imo",
    "Port-Harcourt": "Rivers",
    "Sokoto": "Sokoto",
    "Umuahia": "Abia",
    "Uyo": "Akwa Ibom",
    "Yenagoa": "Bayelsa",
    "Yola": "Adamawa",
}

# Reverse: State → City
STATE_TO_CITY = {v: k for k, v in CITY_TO_STATE.items()}

# Cache the mileage matrix
_mileage_matrix: dict[str, dict[str, int]] | None = None


def _load_matrix() -> dict[str, dict[str, int]]:
    global _mileage_matrix
    if _mileage_matrix is not None:
        return _mileage_matrix

    csv_path = Path(__file__).resolve().parent.parent / "data" / "nbs_mileage_matrix.csv"
    if not csv_path.exists():
        _mileage_matrix = {}
        return _mileage_matrix

    matrix = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        cities = header[1:]

        for row in reader:
            origin = row[0].strip()
            if not origin:
                continue
            matrix[origin] = {}
            for i, city in enumerate(cities):
                try:
                    matrix[origin][city] = int(row[i + 1])
                except (ValueError, IndexError):
                    matrix[origin][city] = 0

    _mileage_matrix = matrix
    return _mileage_matrix


def get_distance_km(from_state: str, to_state: str) -> int:
    """Get distance in km between two states (by capital city)."""
    from_city = STATE_TO_CITY.get(from_state)
    to_city = STATE_TO_CITY.get(to_state)

    if not from_city or not to_city:
        return 0

    matrix = _load_matrix()
    row = matrix.get(from_city, {})
    return row.get(to_city, 0)


def calculate_road_mileage(from_state: str, to_state: str, rate_per_km: Decimal = Decimal("50")) -> Decimal:
    """Calculate round-trip road mileage cost.

    Default rate: NGN 50/km (adjust as needed).
    Returns round-trip cost (distance × 2 × rate).
    """
    distance = get_distance_km(from_state, to_state)
    return Decimal(distance) * 2 * rate_per_km

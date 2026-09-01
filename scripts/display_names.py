"""Helpers for turning PDF-extracted labels into readable display labels."""
from __future__ import annotations
import re

COUNTRY_DISPLAY = {
    "BosniaandHerzegovina": "Bosnia and Herzegovina",
    "CongoDemocraticRepublicof": "Democratic Republic of the Congo",
    "CongoRepublicof": "Republic of the Congo",
    "CaboVerde": "Cabo Verde",
    "CentralAfricanRepublic": "Central African Republic",
    "CostaRica": "Costa Rica",
    "Coted'Ivoire": "Côte d'Ivoire",
    "DominicanRepublic": "Dominican Republic",
    "EgyptArabRepublicof": "Egypt",
    "ElSalvador": "El Salvador",
    "EquatorialGuinea": "Equatorial Guinea",
    "KyrgyzRepublic": "Kyrgyz Republic",
    "LaoPeople'sDemocraticRepublic": "Lao People's Democratic Republic",
    "NorthMacedonia": "North Macedonia",
    "SouthAfrica": "South Africa",
    "SouthSudan": "South Sudan",
    "St.VincentandtheGrenadines": "St. Vincent and the Grenadines",
    "Timor-Leste": "Timor-Leste",
    "Turkey": "Türkiye",
    "Turkiye": "Türkiye",
    "UnitedStates": "United States",
    "Vietnam": "Vietnam",
    "YemenRepublicof": "Yemen",
    "EasternandSouthernAfrica": "Eastern and Southern Africa",
    "WesternandCentralAfrica": "Western and Central Africa",
    "WesternBalkans": "Western Balkans",
    "CentralAfrica": "Central Africa",
    "SouthAsia": "South Asia",
}


def clean_pdf_label(value: str) -> str:
    """Add spaces to common PDF text-layer concatenations without changing meaning."""
    if not value:
        return value
    value = value.strip()
    value = COUNTRY_DISPLAY.get(value, value)
    value = re.sub(r"(?<=[a-z])and(?=[A-Z])", " and ", value)
    value = value.replace("andthe", "and the").replace("andof", "and of")
    value = re.sub(r"(?<=[a-z])and(?=\s)", " and", value)
    value = re.sub(r"\)(?=[A-Za-z])", ") ", value)
    value = re.sub(r"(?<=,)(?=[A-Za-z])", " ", value)
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", value)
    value = value.replace("P P P", "PPP").replace("I B R D", "IBRD").replace("I D A", "IDA")
    value = re.sub(r"\s+", " ", value)
    return value

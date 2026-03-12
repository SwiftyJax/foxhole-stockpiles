"""Stockpile type text constants.

This module contains the valid texts for each stockpile type, including
translations for all supported languages. These are the canonical texts
that appear in the game UI.

Generated/verified by: tools/sync_stockpile_translations.py
"""

from foxhole_stockpiles.enums.stockpile_type import StockpileType

STOCKPILE_TYPE_TEXTS: dict[StockpileType, list[str]] = {
    StockpileType.ENCAMPMENT: [
        "Encampment",
        "Feldlager",
        "Campement",
        "Acampamento",
        "Лагерь",
        "营地",
    ],
    StockpileType.KEEP: [
        "Keep",
        "Wehrturm",
        "Place Forte",
        "Torreão",
        "Крепость",
        "要塞",
    ],
    StockpileType.SAFE_HOUSE: [
        "Safe House",
        "Unterschlupf",
        "Planque",
        "Casa Fortificada",
        "Убежище",
        "安全屋",
    ],
    StockpileType.RELIC_BASE: [
        "Relic Base",
        "Reliktbasis",
        "Base Relique",
        "Base Relíquia",
        "Реликтовая База",
        "遗迹基地",
    ],
    StockpileType.BUNKER_BASE: [
        "Bunker Base",
        "Bunkerbasis",
        "Base Bunker",
        "Centro do Bunker",
        "Base de Bunker",
        "Centro do bunker",
        "Бункерная база",
        "Бункерная База",
        "地堡基地",
    ],
    StockpileType.BORDER_BASE: [
        "Border Base",
        "Grenzbasis",
        "Base Frontalière",
        "Base Fronteiriça",
        "Пограничная База",
        "边境基地",
    ],
    StockpileType.TOWN_BASE: [
        "Town Base",
        "Stadtkernbasis",
        "Quartier Général",
        "Base da Cidade",
        "Ратуша",
        "城镇基地",
    ],
    StockpileType.UNDERGROUND_FORTRESS: [
        "Underground Fortress",
        "Untergrundfestung",
        "Forteresse Souterraine",
        "Bunker Subterrâneo",
        "Подземная Крепость",
        "地下要塞",
    ],
    StockpileType.BMS_LONGHOOK: [
        "BMS - Longhook",
    ],
    StockpileType.STORAGE_DEPOT: [
        "Storage Depot",
        "Lagerdepot",
        "Dépôt",
        "Depósito",
        "Складское помещение",
        "仓库",
    ],
    StockpileType.SEAPORT: [
        "Seaport",
        "Seehafen",
        "Port",
        "Porto",
        "Морской порт",
        "海港",
    ],
    StockpileType.AIRCRAFT_DEPOT: [
        "Aircraft Depot",
    ],
    StockpileType.UNDEFINED: [
        "Undefined",
    ],
}

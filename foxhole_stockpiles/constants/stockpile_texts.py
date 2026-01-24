"""Stockpile type text constants.

This module contains the valid texts for each stockpile type, including
translations for all supported languages. These are the canonical texts
that appear in the game UI.
"""

from foxhole_stockpiles.enums.stockpile_type import StockpileType

STOCKPILE_TYPE_TEXTS: dict[StockpileType, list[str]] = {
    StockpileType.ENCAMPMENT: [
        "Encampment",
        "Campement",
        "Feldlager",
        "Acampamento",
        "Лагерь",
        "营地",
    ],
    StockpileType.KEEP: [
        "Keep",
        "Place Forte",
        "Wehrturm",
        "Torreão",
        "Крепость",
        "要塞",
    ],
    StockpileType.SAFE_HOUSE: [
        "Safe House",
        "Planque",
        "Unterschlupf",
        "Casa Fortificada",
        "Убежище",
        "安全屋",
    ],
    StockpileType.RELIC_BASE: [
        "Relic Base",
        "Base Relique",
        "Reliktbasis",
        "Base Relíquia",
        "Реликтовая База",
        "遗迹基地",
    ],
    StockpileType.BUNKER_BASE: [
        "Bunker Base",
        "Base Bunker",
        "Bunkerbasis",
        "Centro do Bunker",
        "Centro do bunker",
        "Base de Bunker",
        "Бункерная база",
        "Бункерная База",
        "地堡基地",
    ],
    StockpileType.BORDER_BASE: [
        "Border Base",
        "Base Frontalière",
        "Grenzbasis",
        "Base Fronteiriça",
        "Пограничная База",
        "边境基地",
    ],
    StockpileType.TOWN_BASE: [
        "Town Base",
        "Quartier Général",
        "Stadtkernbasis",
        "Base da Cidade",
        "Ратуша",
        "城镇基地",
    ],
    StockpileType.BMS_LONGHOOK: [
        "BMS - Longhook",
    ],
    StockpileType.STORAGE_DEPOT: [
        "Storage Depot",
        "Dépôt",
        "Lagerdepot",
        "Depósito",
        "Складское помещение",
        "仓库",
    ],
    StockpileType.SEAPORT: [
        "Seaport",
        "Port",
        "Seehafen",
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

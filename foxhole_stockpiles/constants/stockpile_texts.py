"""Stockpile type text constants.

This module contains the valid texts for each stockpile type, including
translations for all supported languages. These are the canonical texts
that appear in the game UI.

Generated/verified by: tools/sync_stockpile_translations.py
"""

from foxhole_stockpiles.enums.stockpile_type import StockpileType

# Display texts for each stockpile type (used for OCR text matching)
# Each tier may have unique translations in some languages (e.g., Portuguese Bunker Base)
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
    # Bunker Base tiers - Portuguese uses different translations per tier
    StockpileType.BUNKER_BASE_1: [
        "Bunker Base",
        "Bunkerbasis",
        "Base Bunker",
        "Centro do Bunker",  # Portuguese T1-specific
        "Бункерная база",
        "地堡基地",
    ],
    StockpileType.BUNKER_BASE_2: [
        "Bunker Base",
        "Bunkerbasis",
        "Base Bunker",
        "Base de Bunker",  # Portuguese T2/T3
        "Бункерная база",
        "地堡基地",
    ],
    StockpileType.BUNKER_BASE_3: [
        "Bunker Base",
        "Bunkerbasis",
        "Base Bunker",
        "Base de Bunker",  # Portuguese T2/T3
        "Бункерная База",  # Russian T3 uses uppercase
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
    # Town Base tiers - Chinese TownBase2 has unique translation
    StockpileType.TOWN_BASE_1: [
        "Town Base",
        "Stadthalle",
        "Quartier Général",
        "Base da Cidade",
        "Ратуша",
        "城镇基地",
    ],
    StockpileType.TOWN_BASE_2: [
        "Town Base",
        "Stadthalle",
        "Quartier Général",
        "Base da Cidade",
        "Ратуша",
        "市政厅",  # Chinese TownBase2-specific
        "城镇基地",
    ],
    StockpileType.TOWN_BASE_3: [
        "Town Base",
        "Stadthalle",
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
    StockpileType.BMS_BLUEFIN: [
        "BMS - Bluefin",
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
    # Facilities
    StockpileType.HOSPITAL: [
        "Hospital",
    ],
    StockpileType.REFINERY: [
        "Refinery",
    ],
    StockpileType.MAINTENANCE_TUNNEL: [
        "Maintenance Tunnel",
    ],
    StockpileType.SMALL_ARMS_FACTORY: [
        "Small Arms Factory",
    ],
    StockpileType.MODIFICATION_CENTER: [
        "Modification Center",
    ],
    StockpileType.TRANSFER_LIQUID: [
        "Transfer Station",
    ],
    StockpileType.TRANSFER_MATERIAL: [
        "Transfer Station",
    ],
    StockpileType.TRANSFER_RESOURCE: [
        "Transfer Station",
    ],
    StockpileType.VEHICLE_FACTORY_1: [
        "Vehicle Factory",
    ],
    StockpileType.VEHICLE_FACTORY_2: [
        "Vehicle Factory",
    ],
    StockpileType.VEHICLE_FACTORY_3: [
        "Vehicle Factory",
    ],
    StockpileType.UNDEFINED: [
        "Undefined",
    ],
}

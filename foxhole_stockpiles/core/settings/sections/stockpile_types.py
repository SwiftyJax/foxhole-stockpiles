"""Stockpile types settings."""

from pydantic import BaseModel, ConfigDict, Field


class StockpileTypesSettings(BaseModel):
    """Settings for the stockpile types."""

    encampment: list[str] = Field(
        description="Encampment values",
        default=[
            "Encampment",
            "Campement",
            "Feldlager",
            "Acampamento",
            "Лагерь",
            "营地",
        ],
    )
    keep: list[str] = Field(
        description="Keep values",
        default=[
            "Keep",
            "Place Forte",
            "Wehrturm",
            "Torreão",
            "Крепость",
            "要塞",
        ],
    )
    safe_house: list[str] = Field(
        description="Safe House values",
        default=[
            "Safe House",
            "Planque",
            "Unterschlupf",
            "Casa Fortificada",
            "Yбeжищe",
            "安全屋",
        ],
    )
    relic_base: list[str] = Field(
        description="Relic Base values",
        default=[
            "Relic Base",
            "Base Relique",
            "Reliktbasis",
            "Base Relíquia",
            "Peликтoвая база",
            "遗迹基地",
        ],
    )
    bunker_base: list[str] = Field(
        description="Bunker Base values",
        default=[
            "Bunker Base",
            "Base Bunker",
            "Bunkerbasis",
            "Centro do Bunker",
            "Base de Bunker",
            "Base de Casamata",
            "Бункерная база",
            "Бункерная База",
            "地堡基地",
        ],
    )
    border_base: list[str] = Field(
        description="Border Base values",
        default=[
            "Border Base",
            "Base Frontalière",
            "Grenzbasis",
            "Base Fronteiriça",
            "Пограничная База",
            "边境基地",
        ],
    )
    town_base: list[str] = Field(
        description="Town Base values",
        default=[
            "Town Base",
            "Quartier Général",
            "Stadtkernbasis",
            "Base de Cidade",
            "Ратуша",
            "城镇基地",
        ],
    )
    bms_longhook: list[str] = Field(
        description="BMS - Longhook values",
        default=["BMS - Longhook"],
    )
    storage_depot: list[str] = Field(
        description="Storage Depot values",
        default=[
            "Storage Depot",
            "Dépôt",
            "Lagerdepot",
            "Depósito",
            "Складское Помещение",
            "仓库",
        ],
    )
    seaport: list[str] = Field(
        description="Seaport values",
        default=[
            "Seaport",
            "Port",
            "Seehafen",
            "Porto",
            "Морской порт",
            "海港",
        ],
    )
    undefined: list[str] = Field(
        description="Undefined values",
        default=["Undefined"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "encampment": [
                    "Encampment",
                    "Campement",
                    "Feldlager",
                    "Acampamento",
                    "Лагерь",
                    "营地",
                ],
                "keep": [
                    "Keep",
                    "Place Forte",
                    "Wehrturm",
                    "Torreão",
                    "Крепость",
                    "要塞",
                ],
                "safe_house": [
                    "Safe House",
                    "Planque",
                    "Unterschlupf",
                    "Casa Fortificada",
                    "Yбeжищe",
                    "安全屋",
                ],
                "relic_base": [
                    "Relic Base",
                    "Base Relique",
                    "Reliktbasis",
                    "Base Relíquia",
                    "Peликтoвая база",
                    "遗迹基地",
                ],
                "bunker_base": [
                    "Bunker Base",
                    "Base Bunker",
                    "Bunkerbasis",
                    "Centro do Bunker",
                    "Base de Bunker",
                    "Base de Casamata",
                    "Бункерная база",
                    "Бункерная База",
                    "地堡基地",
                ],
                "border_base": [
                    "Border Base",
                    "Base Frontalière",
                    "Grenzbasis",
                    "Base Fronteiriça",
                    "Пограничная База",
                    "边境基地",
                ],
                "town_base": [
                    "Town Base",
                    "Quartier Général",
                    "Stadtkernbasis",
                    "Base de Cidade",
                    "Ратуша",
                    "城镇基地",
                ],
                "bms_longhook": ["BMS - Longhook"],
                "storage_depot": [
                    "Storage Depot",
                    "Dépôt",
                    "Lagerdepot",
                    "Depósito",
                    "Складское Помещение",
                    "仓库",
                ],
                "seaport": [
                    "Seaport",
                    "Port",
                    "Seehafen",
                    "Porto",
                    "Морской порт",
                    "海港",
                ],
                "undefined": ["Undefined"],
            }
        },
    )

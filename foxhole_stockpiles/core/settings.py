"""Configuration module for the app."""

from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OCRSettings(BaseModel):
    """Settings for the OCR."""

    height: int = Field(description="Base Height for the scaling", gt=0, default=2160)
    box_width: int = Field(description="Width of the quantity square", gt=0, default=84)
    box_height: int = Field(description="Height of the quantity square", gt=0, default=64)
    column_offset: int = Field(description="Horizontal separation between icons", gt=0, default=112)
    row_offset: int = Field(description="Vertical separation between icons", gt=0, default=78)
    group_offset: int = Field(description="Vertical separation for a new group", gt=0, default=98)
    title_margin: int = Field(
        description="Gap from top-left icon to title top-left point", gt=0, default=24
    )
    title_min_width: int = Field(description="Mimimum width for title", gt=0, default=600)
    title_height: int = Field(description="Title height", gt=0, default=64)
    icon_to_quantity_offset: int = Field(
        description="Gap between icon and quantity", gt=0, default=88
    )
    gray_lower: int = Field(
        description="Value for quantity boxes with darkest gamma", gt=0, default=15
    )
    gray_upper: int = Field(
        description="Value for quantity boxes with brighest gamma", gt=0, default=98
    )
    pixel_diff_tolerance: int = Field(description="pixel error tolerance", gt=0, default=2)

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "height": 2160,
                "box_width": 84,
                "box_height": 64,
                "column_offset": 112,
                "row_offset": 78,
                "group_offset": 98,
                "title_margin": 24,
                "title_min_width": 600,
                "title_height": 64,
                "icon_to_quantity_offset": 88,
                "gray_lower": 15,
                "gray_upper": 98,
                "pixel_diff_tolerance": 2,
            }
        },
    )


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
        extra="ignore",
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


# Sections. End


class AppSettings(BaseSettings):
    """Application Settings."""

    ocr: OCRSettings = Field(description="OCR settings", default_factory=OCRSettings)
    stockpile_types: StockpileTypesSettings = Field(
        description="Stockpile types settings", default_factory=StockpileTypesSettings
    )
    model_config = SettingsConfigDict(env_nested_delimiter="__", env_prefix="FS_")


@lru_cache
def get_settings() -> AppSettings:
    """Get the settings.

    Returns:
        AppSettings: The settings
    """
    return AppSettings()

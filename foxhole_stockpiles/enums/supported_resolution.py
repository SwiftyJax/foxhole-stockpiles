"""Supported resolutions for template matching."""

from enum import StrEnum


class SupportedResolution(StrEnum):
    """Supported vertical resolutions for template matching."""

    R_664 = "664"  # 20
    R_720 = "720"  # 21
    R_768 = "768"  # 23
    R_800 = "800"  # 24
    R_864 = "864"  # 26
    R_900 = "900"  # 27
    R_960 = "960"  # 28
    R_992 = "992"  # 29
    R_1024 = "1024"  # 30
    R_1050 = "1050"  # 31
    R_1080 = "1080"  # 32
    R_1200 = "1200"  # 36
    R_1440 = "1440"  # 43
    R_1536 = "1536"  # 46
    R_1600 = "1600"  # 47
    R_2160 = "2160"  # 64

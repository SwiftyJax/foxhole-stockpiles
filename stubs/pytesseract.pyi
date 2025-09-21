from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL.Image import Image

def image_to_string(
    image: str | bytes | Image | NDArray[np.uint8],
    lang: str | None = None,
    config: str = "",
    nice: int = 0,
    output_type: int = 0,
    timeout: int = 0,
) -> str: ...
def image_to_data(
    image: str | bytes | Image | NDArray[np.uint8],
    output_type: int = 1,
    lang: str | None = None,
    config: str = "",
    nice: int = 0,
    timeout: int = 0,
) -> dict[str, Any]: ...
def image_to_boxes(
    image: str | bytes | Image | NDArray[np.uint8],
    lang: str | None = None,
    config: str = "",
    nice: int = 0,
    output_type: int = 0,
    timeout: int = 0,
) -> str: ...

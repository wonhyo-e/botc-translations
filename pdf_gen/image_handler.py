import logging
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO
from typing import Dict, Optional

class ImageHandler:
    """Handles image processing and retrieval"""
    def __init__(self, assets_path: str = "assets"):
        self.assets_path = Path(assets_path)

    def get_image(self, item: Dict[str, str]) -> Optional[Image.Image]:
        """Get image from local storage or download from URL"""
        icon_id = item["id"]
        
        path_patterns = [
            f"icons/Icon_{icon_id}.png",
            f"icons/Icon_{'_'.join(icon_id.split('_')[2:])}.png",
            f"icons/Icon_{icon_id.split('_')[-1]}.png"
        ]

        for pattern in path_patterns:
            full_path = self.assets_path / pattern
            if full_path.exists():
                logging.info(f"Found image at: {full_path}")
                return Image.open(full_path)

        return self._download_image(item.get("image"))

    def _download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL"""
        if not url:
            return None
            
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except requests.RequestException as e:
            logging.error(f"Error downloading image from {url}: {e}")
            return None
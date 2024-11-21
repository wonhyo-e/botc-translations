import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .config import FontConfig

class FontManager:
    """Manages font registration and configuration"""
    def __init__(self, config: FontConfig):
        self.config = config

    def register_fonts(self) -> None:
        """Register all required fonts"""
        font_mappings = {
            "NanumGothic": self.config.regular,
            "NanumGothic-Bold": self.config.bold,
            "Dumbledor": self.config.dumbledor,
            "ChungjuKimSaeng": self.config.title
        }

        for font_name, font_path in font_mappings.items():
            if not os.path.exists(font_path):
                raise FileNotFoundError(f"Font file '{font_path}' not found.")
            pdfmetrics.registerFont(TTFont(font_name, font_path))
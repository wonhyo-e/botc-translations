from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from abc import ABC, abstractmethod
import logging
import json
import re
import os
from PIL import Image
from io import BytesIO
import requests

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image as ReportLabImage, Table, TableStyle

# Configuration
@dataclass
class AppConfig:
    """Application-wide configuration"""
    LOGGING_FORMAT: str = "%(asctime)s - %(levelname)s - %(message)s"
    LOGGING_LEVEL: int = logging.INFO

@dataclass
class FontConfig:
    """Font configuration"""
    FONT_DIR: Path = Path("assets/fonts")
    FONTS: Dict[str, str] = field(default_factory=lambda: {
        "regular": "NanumGothic.ttf",
        "bold": "NanumGothic-Bold.ttf",
        "title": "dum1.ttf",
        "header": "ChungjuKimSaeng.ttf"
    })

    def get_font_path(self, font_type: str) -> Path:
        return self.FONT_DIR / self.FONTS[font_type]

@dataclass
class PDFConfig:
    """PDF generation configuration"""
    VALID_TEAMS: Tuple[str, ...] = ("townsfolk", "outsider", "minion", "demon")
    PAGE_MARGINS: Tuple[float, float, float, float] = (1*mm, 1*mm, 0*mm, 0*mm)
    TEAM_IMAGE_DIR: Path = Path("assets/icons")
    DEFAULT_IMAGE_WIDTH: float = 0.5 * inch
    DEFAULT_IMAGE_HEIGHT: float = 0.5 * inch

# Base classes and interfaces
class StyleProvider(ABC):
    """Abstract base class for style providers"""
    @abstractmethod
    def get_styles(self) -> Dict[str, ParagraphStyle]:
        pass

class DocumentBuilder(ABC):
    """Abstract base class for document builders"""
    @abstractmethod
    def build(self, data: List[Dict]) -> List[Any]:
        """Build document elements from data."""
        pass

# Core functionality classes
class DefaultStyleProvider(StyleProvider):
    """Provides default styles for PDF generation"""
    def get_styles(self) -> Dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()
        style_configs = [
            {
                "name": "Korean",
                "fontName": "NanumGothic",
                "fontSize": 8,
                "leading": 11
            },
            {
                "name": "KoreanName",
                "fontName": "NanumGothic-Bold",
                "fontSize": 9,
                "leading": 12
            },
            {
                "name": "MetaTitle",
                "fontName": "Dumbledor",
                "fontSize": 14,
                "leading": 16,
                "alignment": TA_LEFT,
                "textColor": HexColor("#5c1f22")
            },
            {
                "name": "MetaAuthor",
                "fontName": "Dumbledor",
                "fontSize": 12,
                "leading": 14,
                "alignment": TA_RIGHT,
                "textColor": HexColor("#5c1f22")
            }
        ]

        for config in style_configs:
            styles.add(ParagraphStyle(**config))
        
        return styles

class FontRegistry:
    """Handles font registration"""
    def __init__(self, font_config: FontConfig):
        self.font_config = font_config

    def register_fonts(self) -> None:
        font_mappings = {
            "NanumGothic": self.font_config.get_font_path("regular"),
            "NanumGothic-Bold": self.font_config.get_font_path("bold"),
            "Dumbledor": self.font_config.get_font_path("title"),
            "ChungjuKimSaeng": self.font_config.get_font_path("header")
        }

        for font_name, font_path in font_mappings.items():
            if not font_path.exists():
                raise FileNotFoundError(f"Font file '{font_path}' not found.")
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))

class TextProcessor:
    """Handles text processing and formatting"""
    @staticmethod
    def split_text(text: str) -> List[str]:
        pattern = '([가-힣]+|[^가-힣]+)'
        return re.findall(pattern, text)

    @staticmethod
    def create_formatted_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
        parts = TextProcessor.split_text(text)
        formatted_parts = [
            f'<font face="ChungjuKimSaeng" size="{style.fontSize - 2}">{part}</font>'
            if re.match('[가-힣]+', part)
            else f'<font face="Dumbledor">{part}</font>'
            for part in parts
        ]
        return Paragraph(''.join(formatted_parts), style)

class ImageHandler:
    """Handles image processing and loading"""
    def __init__(self, config: PDFConfig):
        self.config = config

    def load_image(self, item: Dict[str, str]) -> Optional[Image.Image]:
        icon_id = item["id"]
        local_paths = [
            self.config.TEAM_IMAGE_DIR / f"Icon_{icon_id}.png",
            self.config.TEAM_IMAGE_DIR / f"Icon_{'_'.join(icon_id.split('_')[2:])}.png",
            self.config.TEAM_IMAGE_DIR / f"Icon_{icon_id.split('_')[-1]}.png"
        ]

        for path in local_paths:
            if path.exists():
                logging.info(f"Found image: {path}")
                return Image.open(path)

        return self._download_image(item.get("image"))

    def _download_image(self, url: Optional[str]) -> Optional[Image.Image]:
        if not url:
            return None
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except requests.RequestException as e:
            logging.error(f"Error downloading image from {url}: {e}")
            return None

class PDFDocumentBuilder(DocumentBuilder):
    """Builds PDF document structure"""
    def __init__(self, config: PDFConfig, styles: Dict[str, ParagraphStyle], image_handler: ImageHandler):
        self.config = config
        self.styles = styles
        self.image_handler = image_handler

    def build(self, data: List[Dict]) -> List[Any]:
        """Build PDF elements from data."""
        elements = []
        
        # Add meta information
        elements.extend(self._process_meta_info(data))
        
        # Process team data
        filtered_data = self._filter_and_sort_data(data)
        grouped_data = self._group_data_by_team(filtered_data)
        
        # Add team sections
        for team in self.config.VALID_TEAMS:
            if team in grouped_data:
                elements.extend(self._create_team_section(team, grouped_data[team]))
        
        return elements

    def _create_meta_table(self, title_para: Paragraph, author_para: Optional[Paragraph]) -> Table:
        """Create meta information table."""
        left_col_width = A4[0] - 20*mm
        right_col_width = A4[0] * 0.3

        if author_para:
            table_data = [[title_para, author_para]]
            col_widths = [left_col_width - right_col_width, right_col_width]
            style = [
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        else:
            table_data = [[title_para]]
            col_widths = [left_col_width]
            style = [
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
            ]

        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle(style))
        return table

    def _process_meta_info(self, data: List[Dict]) -> List[Any]:
        """Process meta information from data."""
        meta = next((item for item in data if item.get("id") == "_meta"), None)
        if not meta:
            return []

        title = TextProcessor.create_formatted_paragraph(
            meta.get("name", "").upper(),
            self.styles["MetaTitle"]
        )
        
        if author := meta.get("author"):
            author_para = Paragraph(f"by {author}", self.styles["MetaAuthor"])
            return [self._create_meta_table(title, author_para)]
        
        return [self._create_meta_table(title, None)]

    def _create_team_section(self, team: str, team_data: List[Dict]) -> List[Any]:
        """Create section for a specific team."""
        elements = []
        
        # Add team header
        team_image_path = Path(f"assets/images/{team}.png")
        if team_image_path.exists():
            team_image = Image.open(team_image_path)
            team_image.thumbnail((A4[0], 72))
            elements.append(
                ReportLabImage(str(team_image_path),
                             width=team_image.size[0],
                             height=team_image.size[1])
            )
        else:
            elements.append(Paragraph(team.capitalize(), self.styles["KoreanName"]))

        # Add team table
        elements.append(self._create_team_table(team_data))
        return elements

    def _create_team_table(self, team_data: List[Dict]) -> Table:
        """Create a table for a specific team."""
        table_data = []
        for item in team_data:
            img = self.image_handler.load_image(item)
            image = self._process_image(img) if img else Paragraph("No image", self.styles["Korean"])
            
            name = Paragraph(item.get("name", "N/A"), self.styles["KoreanName"])
            ability = Paragraph(item.get("ability", "N/A"), self.styles["Korean"])
            table_data.append([image, name, ability])

        table = Table(
            table_data,
            colWidths=[0.4 * inch, 1.0 * inch, A4[0] - 2.0 * inch],
            rowHeights=0.39 * inch,
        )
        
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, -1), -10),
            ("RIGHTPADDING", (-1, 0), (-1, -1), 10),
        ]))
        
        return table

    def _process_image(self, img: Optional[Image.Image]) -> ReportLabImage:
        """Process PIL Image to ReportLab Image."""
        if img is None:
            return Paragraph("No image", self.styles["Korean"])
            
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format="PNG")
        return ReportLabImage(
            BytesIO(img_byte_arr.getvalue()),
            width=self.config.DEFAULT_IMAGE_WIDTH,
            height=self.config.DEFAULT_IMAGE_HEIGHT
        )

    def _filter_and_sort_data(self, data: List[Dict]) -> List[Dict]:
        """Filter and sort data by team."""
        filtered = [item for item in data if item and item.get("team") in self.config.VALID_TEAMS]
        return sorted(filtered, key=lambda x: self.config.VALID_TEAMS.index(x["team"]))

    def _group_data_by_team(self, data: List[Dict]) -> Dict[str, List[Dict]]:
        """Group data by team."""
        return {
            team: [item for item in data if item["team"] == team]
            for team in self.config.VALID_TEAMS
        }

class PDFGenerator:
    """Main PDF generation class"""
    def __init__(self, config: PDFConfig, font_config: FontConfig):
        self.config = config
        self.font_registry = FontRegistry(font_config)
        self.style_provider = DefaultStyleProvider()
        self.image_handler = ImageHandler(config)
        
    def generate(self, input_path: Path, output_path: Optional[Path] = None) -> None:
        # Setup
        self.font_registry.register_fonts()
        styles = self.style_provider.get_styles()
        
        # Read data
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
        
        # Initialize builder
        builder = PDFDocumentBuilder(self.config, styles, self.image_handler)
        
        # Generate output path
        output_path = output_path or input_path.with_suffix('.pdf')
        
        # Create document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=self.config.PAGE_MARGINS[1],
            leftMargin=self.config.PAGE_MARGINS[0],
            topMargin=self.config.PAGE_MARGINS[2],
            bottomMargin=self.config.PAGE_MARGINS[3],
        )
        
        # Build and save
        elements = builder.build(data)
        doc.build(elements)
        logging.info(f"PDF has been created successfully: {output_path}")

def main():
    import argparse
    
    # Configure logging
    logging.basicConfig(
        level=AppConfig.LOGGING_LEVEL,
        format=AppConfig.LOGGING_FORMAT
    )
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Convert JSON to PDF with team filtering and sorting.")
    parser.add_argument("input_json", help="Path to the input JSON file")
    parser.add_argument("-o", "--output", help="Path to the output PDF file (optional)")
    args = parser.parse_args()
    
    try:
        # Initialize configurations
        pdf_config = PDFConfig()
        font_config = FontConfig()
        
        # Generate PDF
        generator = PDFGenerator(pdf_config, font_config)
        generator.generate(
            Path(args.input_json),
            Path(args.output) if args.output else None
        )
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
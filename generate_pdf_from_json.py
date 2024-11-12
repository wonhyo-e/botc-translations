import re
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
from PIL import Image
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image as ReportLabImage, Table, TableStyle

@dataclass
class FontConfig:
    REGULAR_FONT_PATH: Path = Path("assets/fonts/NanumGothic.ttf")
    BOLD_FONT_PATH: Path = Path("assets/fonts/NanumGothic-Bold.ttf")
    DUMBLEDOR_FONT_PATH: Path = Path("assets/fonts/dum1.ttf")
    TITLE_FONT_PATH: Path = Path("assets/fonts/ChungjuKimSaeng.ttf")

@dataclass
class PDFConfig:
    VALID_TEAMS: List[str] = ("townsfolk", "outsider", "minion", "demon")
    PAGE_MARGINS: Tuple[float, float, float, float] = (1*mm, 1*mm, 0*mm, 0*mm)  # left, right, top, bottom

class FontManager:
    def __init__(self, font_config: FontConfig):
        self.font_config = font_config

    def setup_fonts(self) -> None:
        """Register fonts for PDF generation."""
        font_mappings = {
            "NanumGothic": self.font_config.REGULAR_FONT_PATH,
            "NanumGothic-Bold": self.font_config.BOLD_FONT_PATH,
            "Dumbledor": self.font_config.DUMBLEDOR_FONT_PATH,
            "ChungjuKimSaeng": self.font_config.TITLE_FONT_PATH
        }

        for font_name, font_path in font_mappings.items():
            if not font_path.exists():
                raise FileNotFoundError(f"Font file '{font_path}' not found.")
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))

class StyleManager:
    @staticmethod
    def create_styles() -> Dict[str, ParagraphStyle]:
        """Create and return custom styles for PDF generation."""
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

class TextProcessor:
    @staticmethod
    def split_korean_english(text: str) -> list:
        """Split text into Korean and non-Korean parts."""
        pattern = '([가-힣]+|[^가-힣]+)'
        return re.findall(pattern, text)

    @staticmethod
    def create_mixed_font_paragraph(text: str, base_style: ParagraphStyle) -> Paragraph:
        """Create a paragraph with mixed Korean and English fonts."""
        parts = TextProcessor.split_korean_english(text)
        formatted_text = []
        
        for part in parts:
            if re.match('[가-힣]+', part):
                formatted_text.append(
                    f'<font face="ChungjuKimSaeng" size="{base_style.fontSize - 2}">{part}</font>'
                )
            else:
                formatted_text.append(
                    f'<font face="Dumbledor">{part}</font>'
                )

        return Paragraph(''.join(formatted_text), base_style)

class ImageManager:
    @staticmethod
    def get_image(item: Dict[str, str]) -> Optional[Image.Image]:
        """Get image from local storage or download from URL."""
        icon_id = item["id"]
        
        # Try different path patterns
        path_patterns = [
            f"assets/icons/Icon_{icon_id}.png",
            f"assets/icons/Icon_{'_'.join(icon_id.split('_')[2:])}.png",
            f"assets/icons/Icon_{icon_id.split('_')[-1]}.png"
        ]
        
        for path in path_patterns:
            if os.path.exists(path):
                logging.info(f"Found image: {path}")
                return Image.open(path)

        # Try downloading if local files not found
        try:
            logging.info(f"Downloading image from: {item['image']}")
            response = requests.get(item["image"], timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except requests.RequestException as e:
            logging.error(f"Error downloading image from {item['image']}: {e}")
            return None

class PDFGenerator:
    def __init__(self, config: PDFConfig, styles: Dict[str, ParagraphStyle]):
        self.config = config
        self.styles = styles

    def process_meta_info(self, data: List[Dict]) -> List:
        """Process meta information and return PDF elements."""
        elements = []
        meta_info = next((item for item in data if item.get("id") == "_meta"), None)
        
        if not meta_info:
            logging.warning("Meta information (_meta object) not found in the JSON data.")
            return elements

        title = meta_info.get("name", "").upper()
        author = meta_info.get("author", "")
        title_para = TextProcessor.create_mixed_font_paragraph(title, self.styles["MetaTitle"])
        
        left_col_width = A4[0] - 20*mm
        right_col_width = A4[0] * 0.3
        
        if author:
            author_para = Paragraph(f"by {author}", self.styles["MetaAuthor"])
            meta_table = self._create_meta_table(title_para, author_para, left_col_width, right_col_width)
        else:
            meta_table = self._create_meta_table(title_para, None, left_col_width, None)
        
        elements.append(meta_table)
        return elements

    def _create_meta_table(self, title_para: Paragraph, author_para: Optional[Paragraph],
                          left_width: float, right_width: Optional[float]) -> Table:
        """Create meta information table."""
        if author_para:
            table_data = [[title_para, author_para]]
            col_widths = [left_width - right_width, right_width]
            style = [
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        else:
            table_data = [[title_para]]
            col_widths = [left_width]
            style = [
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
            ]

        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle(style))
        return table

    def create_team_table(self, team_data: List[Dict]) -> Table:
        """Create a table for a specific team."""
        table_data = []
        for item in team_data:
            img = ImageManager.get_image(item)
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

    def _process_image(self, img: Image.Image) -> ReportLabImage:
        """Process PIL Image to ReportLab Image."""
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format="PNG")
        return ReportLabImage(
            BytesIO(img_byte_arr.getvalue()),
            width=0.5 * inch,
            height=0.5 * inch
        )

    @staticmethod
    def create_footer(canvas, doc):
        """Create footer for PDF pages."""
        canvas.saveState()
        page_width = A4[0]

        # Left text
        canvas.setFont("NanumGothic", 7)
        canvas.setFillColor(HexColor('#999999'))
        canvas.drawString(20, 5, "© StevenMedway, bloodontheclocktower.com | Korean PDF by botc-kr.github.io")

        # Right text
        canvas.setFont("NanumGothic", 9)
        canvas.setFillColor(HexColor('#5c1f22'))
        canvas.drawRightString(page_width - 20, 5, "*첫날 밤 제외")

        canvas.restoreState()

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    import argparse
    parser = argparse.ArgumentParser(description="Convert JSON to PDF with team filtering and sorting.")
    parser.add_argument("input_json", help="Path to the input JSON file")
    parser.add_argument("-o", "--output", help="Path to the output PDF file (optional)")
    args = parser.parse_args()

    try:
        # Initialize configurations
        font_config = FontConfig()
        pdf_config = PDFConfig()

        # Setup fonts
        font_manager = FontManager(font_config)
        font_manager.setup_fonts()

        # Create styles
        styles = StyleManager.create_styles()

        # Read and process JSON data
        with open(args.input_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = [data]

        # Generate output filename
        input_basename = Path(args.input_json).stem
        output_filename = f"{input_basename}.pdf"

        # Initialize PDF document
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=A4,
            rightMargin=pdf_config.PAGE_MARGINS[1],
            leftMargin=pdf_config.PAGE_MARGINS[0],
            topMargin=pdf_config.PAGE_MARGINS[2],
            bottomMargin=pdf_config.PAGE_MARGINS[3],
        )

        # Generate PDF
        pdf_generator = PDFGenerator(pdf_config, styles)
        elements = pdf_generator.process_meta_info(data)

        # Process team data
        filtered_data = [item for item in data if item and item.get("team") in pdf_config.VALID_TEAMS]
        sorted_data = sorted(filtered_data, key=lambda x: pdf_config.VALID_TEAMS.index(x["team"]))
        grouped_data = {team: [item for item in sorted_data if item["team"] == team] for team in pdf_config.VALID_TEAMS}

        # Add team sections
        for team in pdf_config.VALID_TEAMS:
            if team in grouped_data:
                team_image_path = Path(f"assets/images/{team}.png")
                if team_image_path.exists():
                    team_image = Image.open(team_image_path)
                    team_image.thumbnail((A4[0], 72))
                    team_image_width, team_image_height = team_image.size
                    elements.append(
                        ReportLabImage(str(team_image_path), width=team_image_width, height=team_image_height)
                    )
                else:
                    logging.warning(f"Team image '{team_image_path}' not found. Using text instead.")
                    elements.append(Paragraph(team.capitalize(), styles["KoreanName"]))

                elements.append(pdf_generator.create_team_table(grouped_data[team]))

        # Build PDF
        doc.build(elements, onFirstPage=PDFGenerator.create_footer, onLaterPages=PDFGenerator.create_footer)
        logging.info(f"PDF has been created successfully: {output_filename}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
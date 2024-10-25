import json
import requests
from PIL import Image
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Image as ReportLabImage,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
import argparse
import sys
import os
import logging
from typing import List, Dict, Optional

# Constants
REGULAR_FONT_PATH = "assets/fonts/NanumGothic.ttf"
BOLD_FONT_PATH = "assets/fonts/NanumGothic-Bold.ttf"
DUMBLEDOR_FONT_PATH = "assets/fonts/dum1.ttf"

VALID_TEAMS = ["townsfolk", "outsider", "minion", "demon"]

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

def setup_fonts() -> None:
    """Register the font for PDF generation."""
    if not os.path.exists(REGULAR_FONT_PATH):
        raise FileNotFoundError(f"Font file '{REGULAR_FONT_PATH}' not found.")
    pdfmetrics.registerFont(TTFont("NanumGothic", REGULAR_FONT_PATH))

    if not os.path.exists(BOLD_FONT_PATH):
        raise FileNotFoundError(f"Font file '{BOLD_FONT_PATH}' not found.")
    pdfmetrics.registerFont(TTFont("NanumGothic-Bold", BOLD_FONT_PATH))

    if not os.path.exists(DUMBLEDOR_FONT_PATH):
        raise FileNotFoundError(f"Font file '{DUMBLEDOR_FONT_PATH}' not found.")
    pdfmetrics.registerFont(TTFont("Dumbledor", DUMBLEDOR_FONT_PATH))

def get_image(item: Dict[str, str]) -> Optional[Image.Image]:
    icon_id = item["id"]  # 예: ko_KR_pregnantmidge_barbieontheclocktower123dgeewes
    
    # 1. 전체 ID로 시도
    local_path = f"assets/icons/Icon_{icon_id}.png"
    logging.info(f"1. Attempting with full ID: {local_path}")
    if os.path.exists(local_path):
        logging.info(f"Found image with full ID: {local_path}")
        return Image.open(local_path)
    
    # 2. 언어 코드 제외하고 시도 (ko_KR_ 제거)
    icon_id_no_lang = '_'.join(icon_id.split('_')[2:])  # pregnantmidge_barbieontheclocktower123dgeewes
    local_path = f"assets/icons/Icon_{icon_id_no_lang}.png"
    logging.info(f"2. Attempting without language code: {local_path}")
    if os.path.exists(local_path):
        logging.info(f"Found image without language code: {local_path}")
        return Image.open(local_path)
    
    # 3. 마지막 부분만 사용 (기존 로직)
    icon_id_last = icon_id.split('_')[-1]  # barbieontheclocktower123dgeewes
    local_path = f"assets/icons/Icon_{icon_id_last}.png"
    logging.info(f"3. Attempting with last part: {local_path}")
    if os.path.exists(local_path):
        logging.info(f"Found image with last part: {local_path}")
        return Image.open(local_path)

    try:
        logging.info(f"Downloading image from: {item['image']}")
        response = requests.get(item["image"], timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except requests.RequestException as e:
        logging.error(f"Error downloading image from {item['image']}: {e}")
        return None

def create_styles() -> Dict[str, ParagraphStyle]:
    """Create and return custom styles for PDF generation."""
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(name="Korean", fontName="NanumGothic", fontSize=8, leading=11)
    )
    styles.add(
        ParagraphStyle(
            name="KoreanName", fontName="NanumGothic-Bold", fontSize=9, leading=12
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaTitle",
            fontName="Dumbledor",
            fontSize=14,
            leading=16,
            alignment=TA_LEFT,
            textColor=HexColor("#5c1f22"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaAuthor",
            fontName="Dumbledor",
            fontSize=12,
            leading=14,
            alignment=TA_RIGHT,
            textColor=HexColor("#5c1f22"),
        )
    )
    return styles

def process_meta_info(data: List[Dict], styles: Dict[str, ParagraphStyle]) -> List:
    """Process meta information and return PDF elements."""
    elements = []
    meta_info = next((item for item in data if item.get("id") == "_meta"), None)
    if meta_info:
        title = meta_info.get("name", "").upper()
        author = meta_info.get("author", "")
        title_para = Paragraph(title, styles["MetaTitle"])
        
        left_col_width = A4[0] - 20*mm  # Full page width minus margins
        right_col_width = A4[0] * 0.3  # 30% of page width for author
        
        if author:
            author_para = Paragraph(f"by {author}", styles["MetaAuthor"])
            # Create a table with one row and two columns
            meta_table = Table(
                [[title_para, author_para]], colWidths=[left_col_width - right_col_width, right_col_width]
            )
            meta_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),  # Reduced left padding
                        ("RIGHTPADDING", (1, 0), (1, 0), 0),  # Reduced right padding
                    ]
                )
            )
        else:
            # If there's no author, create a table with just the title
            meta_table = Table([[title_para]], colWidths=[left_col_width])
            meta_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ]
                )
            )
        
        elements.append(meta_table)
    else:
        logging.warning("Meta information (_meta object) not found in the JSON data.")
    return elements

def create_team_table(team_data: List[Dict], styles: Dict[str, ParagraphStyle]) -> Table:
    """Create a table for a specific team."""
    table_data = []
    for item in team_data:
        img = get_image(item)
        if img:
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format="PNG")
            image = ReportLabImage(
                BytesIO(img_byte_arr.getvalue()), width=0.4 * inch, height=0.4 * inch
            )
        else:
            image = Paragraph("No image", styles["Korean"])

        name = Paragraph(item.get("name", "N/A"), styles["KoreanName"])
        ability = Paragraph(item.get("ability", "N/A"), styles["Korean"])
        table_data.append([image, name, ability])

    table = Table(
        table_data,
        colWidths=[0.4 * inch, 1.0 * inch, A4[0] - 2.0 * inch],  # Adjusted last column width
        rowHeights=0.375 * inch,
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, -1), -10),
                ("RIGHTPADDING", (-1, 0), (-1, -1), 10),  # Add right padding to the last column
            ]
        )
    )
    return table

def create_pdf(data: List[Dict], output_filename: str) -> None:
    """Create PDF from the provided data."""
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        rightMargin=1*mm,
        leftMargin=1*mm,
        topMargin=0*mm,
        bottomMargin=0*mm,
    )
    styles = create_styles()
    elements = process_meta_info(data, styles)

    filtered_data = [
        item for item in data if item is not None and item.get("team") in VALID_TEAMS
    ]
    sorted_data = sorted(filtered_data, key=lambda x: VALID_TEAMS.index(x["team"]))
    grouped_data = {
        team: [item for item in sorted_data if item["team"] == team]
        for team in VALID_TEAMS
    }

    for team in VALID_TEAMS:
        if team in grouped_data:
            team_image_path = f"assets/images/{team}.png"
            if os.path.exists(team_image_path):
                team_image = Image.open(team_image_path)
                team_image.thumbnail((A4[0], 72))
                team_image_width, team_image_height = team_image.size
                elements.append(
                    ReportLabImage(
                        team_image_path,
                        width=team_image_width,
                        height=team_image_height,
                    )
                )
            else:
                logging.warning(
                    f"Team image '{team_image_path}' not found. Using text instead."
                )
                elements.append(Paragraph(team.capitalize(), styles["KoreanName"]))

            elements.append(create_team_table(grouped_data[team], styles))

    def footer(canvas, doc):
        canvas.saveState()
        
        # 페이지 너비
        page_width = A4[0]

        # 좌측 문구 (작은 폰트, 연한 회색)
        left_text = "© StevenMedway, bloodontheclocktower.com. PDF generated by Skull"
        canvas.setFont("NanumGothic", 7)  # 폰트 크기를 7로 줄임
        canvas.setFillColor(HexColor('#999999'))  # 연한 회색
        canvas.drawString(20, 5, left_text)

        # 우측 문구 (기존 스타일 유지)
        right_text = "*첫날 밤 제외"
        canvas.setFont("NanumGothic", 9)  # 기존 폰트 크기
        canvas.setFillColor(HexColor('#5c1f22'))  # 기존 색상
        canvas.drawRightString(page_width - 20, 5, right_text)

        canvas.restoreState()

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)

def main():
    parser = argparse.ArgumentParser(
        description="Convert JSON to PDF with team filtering and sorting."
    )
    parser.add_argument("input_json", help="Path to the input JSON file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output PDF file (optional)",
    )
    args = parser.parse_args()

    try:
        setup_fonts()
        with open(args.input_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        # Get meta information for filename
        meta_info = next((item for item in data if item.get("id") == "_meta"), None)
        
        # Determine output filename
        if args.output:
            output_filename = args.output
        elif meta_info and meta_info.get("name"):
            # Replace invalid filename characters and add .pdf extension
            safe_name = "".join(c for c in meta_info["name"] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_filename = f"{safe_name}.pdf"
        else:
            # Use input filename but change extension to .pdf
            input_basename = os.path.splitext(os.path.basename(args.input_json))[0]
            output_filename = f"{input_basename}.pdf"

        create_pdf(data, output_filename)
        logging.info(f"PDF has been created successfully: {output_filename}")
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON file: {args.input_json}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
import os
import logging
from typing import List, Dict
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image as ReportLabImage, Table, TableStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor
from io import BytesIO
from PIL import Image
from .fonts import FontManager
from .styles import StyleManager
from .image_handler import ImageHandler

class PDFGenerator:
    """Main PDF generation class"""
    VALID_TEAMS = ["townsfolk", "outsider", "minion", "demon"]

    def __init__(self, font_manager: FontManager, style_manager: StyleManager, image_handler: ImageHandler):
        self.font_manager = font_manager
        self.style_manager = style_manager
        self.image_handler = image_handler
        self.styles = style_manager.create_styles()

    def create_pdf(self, data: List[Dict], output_filename: str) -> None:
        """Create PDF document from provided data"""
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=A4,
            rightMargin=1*mm,
            leftMargin=1*mm,
            topMargin=0*mm,
            bottomMargin=0*mm,
            compress=2,
        )

        elements = self._process_meta_info(data)
        elements.extend(self._process_team_data(data))
        
        doc.build(elements, onFirstPage=self._add_footer, onLaterPages=self._add_footer)

    def _process_meta_info(self, data: List[Dict]) -> List:
        """Process meta information section"""
        elements = []
        meta_info = next((item for item in data if item.get("id") == "_meta"), None)
        
        if not meta_info:
            logging.warning("Meta information not found in the JSON data.")
            return elements

        title = meta_info.get("name", "").upper()
        author = meta_info.get("author", "")
        
        return self._create_meta_table(title, author)

    def _create_meta_table(self, title: str, author: str) -> List:
        """Create meta information table"""
        title_para = self.style_manager.create_mixed_font_paragraph(title, self.styles["MetaTitle"])
        left_col_width = A4[0] - 20*mm
        right_col_width = A4[0] * 0.3

        if not author:
            return [Table(
                [[title_para]], 
                colWidths=[left_col_width],
                style=TableStyle([
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                ])
            )]

        author_para = Paragraph(f"by {author}", self.styles["MetaAuthor"])
        return [Table(
            [[title_para, author_para]], 
            colWidths=[left_col_width - right_col_width, right_col_width],
            style=TableStyle([
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ])
        )]

    def _process_team_data(self, data: List[Dict]) -> List:
        """Process team data section"""
        elements = []
        filtered_data = [
            item for item in data 
            if item is not None and item.get("team") in self.VALID_TEAMS
        ]
        
        sorted_data = sorted(
            filtered_data, 
            key=lambda x: self.VALID_TEAMS.index(x["team"])
        )
        
        grouped_data = {
            team: [item for item in sorted_data if item["team"] == team]
            for team in self.VALID_TEAMS
        }

        for team in self.VALID_TEAMS:
            if team in grouped_data:
                elements.extend(self._create_team_section(team, grouped_data[team]))

        return elements

    def _create_team_section(self, team: str, team_data: List[Dict]) -> List:
        """Create section for specific team"""
        elements = []
        team_image_path = f"assets/images/{team}.png"

        if os.path.exists(team_image_path):
            team_image = Image.open(team_image_path)
            team_image.thumbnail((A4[0], 72))
            width, height = team_image.size
            elements.append(
                ReportLabImage(team_image_path, width=width, height=height)
            )
        else:
            logging.warning(f"Team image not found: {team_image_path}")
            elements.append(Paragraph(team.capitalize(), self.styles["KoreanName"]))

        elements.append(self._create_team_table(team_data))
        return elements

    def _create_team_table(self, team_data: List[Dict]) -> Table:
        """Create table for team members"""
        table_data = []
        for item in team_data:
            image = self._process_team_member_image(item)
            name = Paragraph(item.get("name", "N/A"), self.styles["KoreanName"])
            ability = Paragraph(item.get("ability", "N/A"), self.styles["Korean"])
            table_data.append([image, name, ability])

        return Table(
            table_data,
            colWidths=[0.4 * inch, 1.0 * inch, A4[0] - 2.0 * inch],
            rowHeights=0.39 * inch,
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, -1), -10),
                ("RIGHTPADDING", (-1, 0), (-1, -1), 10),
            ])
        )

    def _process_team_member_image(self, item: Dict) -> Paragraph | ReportLabImage:
        """Process team member image with optimization"""
        img = self.image_handler.get_image(item)
        if not img:
            return Paragraph("No image", self.styles["Korean"])

        # 이미지 크기가 실제 표시 크기보다 크다면 리사이즈
        target_size = (int(2 * inch), int(2 * inch))
        if img.size[0] > target_size[0] or img.size[1] > target_size[1]:
            img = img.resize(target_size, Image.LANCZOS)

        # JPEG로 변환하여 압축 (투명도가 필요없는 경우)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            # 투명 배경이 있는 경우 처리
            background = Image.new('RGB', img.size, 'white')
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1])
            img = background

        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='JPEG', 
                 quality=85,  # 품질 조정 (85는 보통 시각적으로 차이가 거의 없음)
                 optimize=True)  # 추가 최적화 활성화

        return ReportLabImage(
            BytesIO(img_byte_arr.getvalue()),
            width=0.5 * inch,
            height=0.5 * inch
        )

    def _add_footer(self, canvas, doc) -> None:
        """Add footer to PDF page"""
        canvas.saveState()
        page_width = A4[0]

        canvas.setFont("NanumGothic", 7)
        canvas.setFillColor(HexColor('#999999'))
        canvas.drawString(
            20, 5, 
            "© StevenMedway, bloodontheclocktower.com | Korean PDF by botc-kr.github.io"
        )

        canvas.setFont("NanumGothic", 9)
        canvas.setFillColor(HexColor('#5c1f22'))
        canvas.drawRightString(page_width - 20, 5, "*첫날 밤 제외")

        canvas.restoreState()
import io
import qrcode
import os
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(BASE_DIR, 'recipes', 'static', 'fonts', 'DejaVuSans.ttf')

def generate_recipe_pdf(recipe):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 40
    max_width = width - 2 * margin

    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', FONT_PATH))
        font_name = 'DejaVuSans'
    except:
        font_name = 'Helvetica'

    # ===== ФУНКЦИЯ ДЛЯ ПЕРЕНОСА ТЕКСТА =====
    def wrap_text(text, font_name, font_size, max_width):
        """Разбивает текст на строки по ширине страницы"""
        c.setFont(font_name, font_size)
        lines = []
        words = text.split(' ')
        current_line = ''
        for word in words:
            test_line = current_line + ' ' + word if current_line else word
            if c.stringWidth(test_line, font_name, font_size) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    # ===== РИСУЕМ ШАПКУ =====
    def draw_header(y):
        c.setFont("Helvetica-Bold", 28)
        c.setFillColor(colors.orange)
        c.drawString(margin, y, "Wajos")
        c.setFont(font_name, 14)
        c.setFillColor(colors.black)
        c.drawString(margin, y - 20, "готовьте без страха")

        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data('https://django-project-jvee.onrender.com/recipe/' + str(recipe.id))
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            qr_img.save(tmp, format='PNG')
            tmp_path = tmp.name
        c.drawImage(ImageReader(tmp_path), width - 100, y - 70, width=70, height=70)
        os.unlink(tmp_path)
        c.setFont(font_name, 7)
        c.setFillColor(colors.grey)
        c.drawRightString(width - margin, y - 80, "QR-код на рецепт")
        return y - 95

    # ===== СТРАНИЦА 1 =====
    y = height - 40
    y = draw_header(y)

    # НАЗВАНИЕ РЕЦЕПТА
    c.setFont(font_name, 20)
    c.setFillColor(colors.black)
    c.drawString(margin, y, recipe.title[:80])
    y -= 32

    # ИНГРЕДИЕНТЫ
    c.setFont(font_name, 14)
    c.drawString(margin, y, "Ингредиенты:")
    y -= 24
    c.setFont(font_name, 11)
    if hasattr(recipe, 'ingredients') and recipe.ingredients:
        for ing in recipe.ingredients:
            if y < 60:
                c.showPage()
                y = draw_header(height - 40)
                c.setFont(font_name, 11)
            c.drawString(margin + 10, y, f"• {ing}")
            y -= 20
    else:
        c.drawString(margin + 10, y, "Ингредиенты не указаны")
        y -= 20

    # ШАГИ
    y -= 12
    c.setFont(font_name, 14)
    c.drawString(margin, y, "Приготовление:")
    y -= 24
    c.setFont(font_name, 10)

    for idx, step in enumerate(recipe.steps, 1):
        text = f"{idx}. {step.get('text', '')}"
        if step.get('duration'):
            text += f" — {step['duration']} мин"
        if step.get('desc'):
            text += f" {step['desc']}"

        # Переносим текст по ширине
        lines = wrap_text(text, font_name, 10, max_width - 20)
        for line in lines:
            if y < 60:
                c.showPage()
                y = draw_header(height - 40)
                c.setFont(font_name, 10)
            c.drawString(margin + 10, y, line)
            y -= 16

    # КОЛОНТИТУЛ
    if y < 40:
        c.showPage()
        y = draw_header(height - 40)
    c.setFont(font_name, 8)
    c.setFillColor(colors.grey)
    c.drawString(margin, 20, "Скачано с Wajos — готовьте без страха")
    c.drawRightString(width - margin, 20, "wajos.app")

    c.save()
    buffer.seek(0)
    return buffer
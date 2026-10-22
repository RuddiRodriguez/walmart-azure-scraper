from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).parent
report = json.loads((root / 'evidence/validation-500.json').read_text())
image = Image.new('RGB', (1600, 1250), '#101c2e')
draw = ImageDraw.Draw(image)
fontpath = '/System/Library/Fonts/Supplemental/Arial.ttf'
boldpath = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(x, y, value, size=28, color='#dce5f1', bold=False):
    draw.text((x, y), value, font=ImageFont.truetype(boldpath if bold else fontpath, size), fill=color)
text(70, 50, 'WALMART SCRAPER', 54, '#ffffff', True)
text(70, 120, 'Live local collection evidence • Python • No paid scraping services', 28)
for x, number, label in [(70, '500', 'validated products'), (580, '11', 'required categories'), (1090, '0', 'duplicate IDs / URLs')]:
    draw.rounded_rectangle((x, 190, x+440, 350), radius=18, fill='#1c3049')
    text(x+25, 205, number, 65, '#64d6c0', True)
    text(x+25, 295, label, 25)
text(70, 385, 'Store 100 • Bentonville S Walton Blvd • ZIP 72712 • Pickup', 29, '#ffffff', True)
text(70, 435, 'Per-product checks: local pickup, Walmart seller, product ID and matching price.', 25)
text(70, 480, '468 UPCs preserved  |  381 displayed PPM values  |  22 fields in required order', 25)
text(70, 545, 'CATEGORY COUNTS', 28, '#64d6c0', True)
for index, (name, count) in enumerate(report['category_counts'].items()):
    col = index // 6
    y = 595 + (index % 6) * 46
    x = 70 + col * 760
    text(x, y, name, 27)
    text(x+590, y, str(count), 27, '#ffffff', True)
text(70, 910, 'PACKAGE', 25, '#64d6c0', True)
text(70, 950, 'Private source repository • JSON dataset • Evidence • Checkpoints • Azure install files', 25)
text(70, 1005, 'VERIFICATION LIMITS', 25, '#ffcf86', True)
text(70, 1045, '500-record evidence comes from feasibility run; packaged runner validation ongoing.', 24)
text(70, 1085, 'Full catalog, live volume/digital offers and Azure acceptance still require demonstration.', 24)
text(70, 1170, 'Ruddi Rodriguez Garcia  |  23 October 2026  |  Data and logo belong to Walmart', 23)
image.save(root / 'evidence/contest-entry.png')

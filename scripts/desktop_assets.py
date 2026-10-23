"""CI-only staging and supersampled rendering of the porcelain folded-F icon."""
import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFilter, ImageFont

if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
    raise SystemExit('Desktop asset staging and rendering require a disposable GitHub-hosted runner')


def app_icon():
    scale = 4
    canvas = 256 * scale
    image = Image.new('RGBA', (canvas, canvas))

    def bounds(*values):
        return tuple(round(value * scale) for value in values)

    def polygon(mask, points, fill=255):
        ImageDraw.Draw(mask).polygon([bounds(*point) for point in points], fill=fill)

    def gradient(top, bottom):
        top, bottom = ImageColor.getrgb(top), ImageColor.getrgb(bottom)
        layer = Image.new('RGBA', (canvas, canvas))
        draw = ImageDraw.Draw(layer)
        for y in range(canvas):
            progress = y / (canvas - 1)
            color = tuple(round(a + (b - a) * progress) for a, b in zip(top, bottom))
            draw.line((0, y, canvas, y), fill=(*color, 255))
        return layer

    def paint(mask, top, bottom, opacity=255):
        layer = gradient(top, bottom)
        layer.putalpha(ImageChops.multiply(mask, Image.new('L', mask.size, opacity)))
        image.alpha_composite(layer)

    tile = Image.new('L', image.size)
    ImageDraw.Draw(tile).rounded_rectangle(bounds(16, 14, 240, 238), radius=54 * scale, fill=255)
    shadow = ImageChops.offset(tile, 0, 5 * scale).filter(ImageFilter.GaussianBlur(7 * scale))
    paint(shadow, '#274269', '#274269', 65)
    paint(tile, '#FEFFFF', '#DEE9F8')
    light = Image.new('L', image.size)
    ImageDraw.Draw(light).ellipse(bounds(-40, -60, 228, 146), fill=255)
    light = ImageChops.multiply(light.filter(ImageFilter.GaussianBlur(24 * scale)), tile)
    paint(light, '#FFFFFF', '#E4F4FF', 135)
    inset = Image.new('L', image.size)
    ImageDraw.Draw(inset).rounded_rectangle(bounds(17, 15, 239, 237), radius=53 * scale, fill=255)
    paint(ImageChops.subtract(tile, inset), '#FFFFFF', '#8FAED4', 195)

    mark = Image.new('L', image.size)
    draw = ImageDraw.Draw(mark)
    draw.rounded_rectangle(bounds(70, 58, 112, 206), radius=10 * scale, fill=255)
    draw.rounded_rectangle(bounds(74, 58, 191, 98), radius=10 * scale, fill=255)
    draw.rounded_rectangle(bounds(98, 115, 172, 151), radius=8 * scale, fill=255)
    # The slanted foot and two folded arm ends make the silhouette authored,
    # while the stem and open counter remain readable at 16px.
    polygon(mark, [(70, 199), (113, 185), (113, 220), (70, 220)], 0)
    mark_shadow = ImageChops.offset(mark, 0, 10 * scale).filter(ImageFilter.GaussianBlur(6 * scale))
    paint(mark_shadow, '#275DA4', '#275DA4', 64)
    paint(ImageChops.offset(mark, 6 * scale, 7 * scale), '#2474D2', '#173E96')
    paint(mark, '#419AFF', '#2253C7')
    for points, colors in [
        ([(81, 59), (182, 59), (189, 65), (176, 74), (80, 74)], ('#B5EDFF', '#6AAEFF')),
        ([(70, 73), (81, 76), (81, 191), (70, 198)], ('#73C8FF', '#2C73D9')),
        ([(154, 115), (172, 123), (172, 148), (154, 139)], ('#9BDCFF', '#4A90E7')),
    ]:
        facet = Image.new('L', image.size)
        polygon(facet, points)
        paint(ImageChops.multiply(facet, mark), *colors)
    edge = Image.new('L', image.size)
    ImageDraw.Draw(edge).line([bounds(84, 64), bounds(180, 64)], fill=180, width=scale)
    ImageDraw.Draw(edge).line([bounds(75, 79), bounds(75, 188)], fill=135, width=scale)
    paint(ImageChops.multiply(edge, mark), '#FFFFFF', '#BAE2FF')
    return image.resize((256, 256), Image.Resampling.LANCZOS)


def icon_evidence(icon, directory):
    directory.mkdir(parents=True, exist_ok=True)
    icon.save(directory / 'app-icon.png')
    preview = Image.new('RGB', (760, 410), '#EDF2F8')
    draw = ImageDraw.Draw(preview)
    font = ImageFont.load_default(size=18)
    draw.text((34, 24), 'Facetmark / porcelain folded F', font=font, fill='#18334F')
    preview.paste(icon, (35, 90), icon)
    draw.rounded_rectangle((326, 80, 732, 217), radius=22, fill='#FFFFFF')
    draw.rounded_rectangle((326, 230, 732, 367), radius=22, fill='#172636')
    for surface, y, ink in [('light', 102, '#294669'), ('dark', 253, '#D8E8FA')]:
        draw.text((342, y - 8), surface, font=font, fill=ink)
        for index, size in enumerate([16, 20, 24, 32, 48, 64]):
            x = 347 + index * 61
            scaled = icon.resize((size, size), Image.Resampling.LANCZOS)
            preview.paste(scaled, (x + (52 - size) // 2, y + 35 + (64 - size) // 2), scaled)
            draw.text((x + 8, y + 99), str(size), font=font, fill=ink)
    preview.save(directory / 'desktop-icon-preview.png')

root = Path(__file__).resolve().parents[1]
source = root / 'dist/facetmark-service'
dest = root / 'desktop/src-tauri/binaries'
dest.mkdir(parents=True, exist_ok=True)
shutil.copy2(source / 'facetmark-service.exe', dest / 'facetmark-service-x86_64-pc-windows-msvc.exe')
shutil.copytree(source / '_internal', dest / '_internal', dirs_exist_ok=True)
icons = root / 'desktop/src-tauri/icons'
icons.mkdir(parents=True, exist_ok=True)
im = app_icon()
im.save(icons / 'icon.png')
sizes = [(size, size) for size in [16, 20, 24, 32, 48, 64, 128, 256]]
im.save(icons / 'icon.ico', sizes=sizes)
with Image.open(icons / 'icon.ico') as encoded:
    assert encoded.ico.sizes() == set(sizes)
    for size in sizes:
        assert encoded.ico.getimage(size).size == size
evidence = root / '.desktop-build/evidence'
icon_evidence(im, evidence)
shutil.copy2(icons / 'icon.ico', evidence / 'app-icon.ico')
(evidence / 'desktop-icon.json').write_text(json.dumps({
    'revision': os.environ.get('GITHUB_SHA'), 'direction': 'porcelain tile and blue folded-F geometry',
    'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'png_sha256': hashlib.sha256((icons / 'icon.png').read_bytes()).hexdigest(),
    'ico_sha256': hashlib.sha256((icons / 'icon.ico').read_bytes()).hexdigest(),
    'encoded_sizes': sizes, 'user_review': 'pending',
}, indent=2), encoding='utf-8')

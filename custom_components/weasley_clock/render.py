"""Discover local clock graphics and render a deterministic PNG snapshot."""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from urllib.parse import unquote

from PIL import Image, ImageOps

EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
FACE_NAMES = ('reloj_weasley', 'clock_face', 'clock', 'reloj', 'weasley_clock')
SNAPSHOT_FILENAME = 'weasley_clock_snapshot.png'


def find_image(root, names):
    files = {p.name.casefold(): p.name for p in Path(root).iterdir()
             if p.is_file() and p.suffix.lower() in EXTENSIONS}
    for name in names:
        for extension in EXTENSIONS:
            if (candidate := files.get((name + extension).casefold())):
                return candidate
    return None


def discover_face(root):
    """Prefer conventional names; only fall back when one source image exists."""
    found = find_image(root, FACE_NAMES)
    if found:
        return found
    candidates = [p.name for p in Path(root).iterdir()
                  if p.is_file() and p.suffix.lower() in EXTENSIONS
                  and not p.name.startswith('weasley_clock_snapshot')
                  and not p.stem.lower().startswith(('manecilla_', 'hand_'))]
    return candidates[0] if len(candidates) == 1 else None


def resolve_image(value, media_root, www_root):
    """Accept local media names and supported HA URLs; reject paths escaping roots."""
    value = unquote(value.split('?', 1)[0])
    if value.startswith('media-source://weasley_clock/'):
        value = value[len('media-source://weasley_clock/'):]
    if value.startswith('/weasley_clock/images/'):
        value = value[len('/weasley_clock/images/'):]
    if value.startswith('/local/'):
        root = Path(www_root).resolve()
        relative = value[len('/local/'):]
    else:
        root = Path(media_root).resolve()
        relative = value
    if '://' in relative or Path(relative).is_absolute():
        raise ValueError('Snapshots require images from local Multimedia or /local/')
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in EXTENSIONS or not path.is_file():
        raise ValueError(f'Local clock image not found: {value}')
    return path


def css_length(value, reference):
    match = re.fullmatch(r'(-?\d+(?:\.\d+)?)(%|px)?', str(value).strip())
    if not match:
        raise ValueError('Hand layout must use percentages or pixels')
    number = float(match[1])
    return number * reference / 100 if match[2] == '%' else number


def load_image(path):
    try:
        with Image.open(path) as image:
            if image.width * image.height > 32_000_000:
                raise ValueError('Clock graphics must be smaller than 32 megapixels')
            return ImageOps.exif_transpose(image).convert('RGBA')
    except Image.DecompressionBombError as error:
        raise ValueError('Clock graphic is too large to render safely') from error


def scaled_length(value, reference, scale):
    length = css_length(value, reference)
    return length if '%' in str(value) else length * scale


def render_snapshot(face_path, hands, destination, width=None):
    """Match browser image sizes, offsets, clockwise angles and centre pivots."""
    face = load_image(face_path)
    scale = min((width or face.width) / face.width, 4096 / face.width, 4096 / face.height)
    size = (max(1, round(face.width * scale)), max(1, round(face.height * scale)))
    face = face.resize(size, Image.Resampling.LANCZOS)
    for hand in hands:
        image = load_image(hand['path'])
        # CSS px offsets refer to the original face, percentages to its dimensions.
        w = round(scaled_length(hand.get('width', '100%'), size[0], scale))
        if w <= 0:
            raise ValueError('Hand width must be positive')
        h = max(1, round(w * image.height / image.width))
        if w * h > 32_000_000 or max(w, h) > 12288:
            raise ValueError('Hand layout produces an oversized image')
        image = image.resize((w, h), Image.Resampling.LANCZOS)
        left = scaled_length(hand.get('left', '0%'), size[0], scale)
        top = scaled_length(hand.get('top', '0%'), size[1], scale)
        angle = float(hand['angle'])
        if not math.isfinite(angle): raise ValueError('Hand angle must be finite')
        rotated = image.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=True)
        x = round(left + w / 2 - rotated.width / 2)
        y = round(top + h / 2 - rotated.height / 2)
        face.alpha_composite(rotated, (x, y))
    destination = Path(destination)
    # Atomic replacement avoids half-written images when a screen fetches latest.png.
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, suffix='.png', delete=False) as output:
            temporary = output.name
            face.save(output, format='PNG')
        os.replace(temporary, destination)
    finally:
        if temporary and Path(temporary).exists(): Path(temporary).unlink()
    return size

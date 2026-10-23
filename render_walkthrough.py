"""Render recorded terminal output to MP4. Optional: Pillow and local ffmpeg required."""
import argparse
import json
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def render(source, destination, font_path):
    lines = source.read_text().splitlines()
    events = [json.loads(line) for line in lines[1:]]
    duration = int(events[-1][0]) + 6
    font = ImageFont.truetype(str(font_path), 18)
    process = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', '1440x900', '-framerate', '1', '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination)], stdin=subprocess.PIPE)
    for second in range(duration):
        output = ''.join(e[2] for e in events if e[0] <= second).replace('\r', '')
        wrapped = [part for line in output.splitlines() for part in (textwrap.wrap(line, width=120, replace_whitespace=False) or [''])]
        frame = Image.new('RGB', (1440, 900), '#111827')
        draw = ImageDraw.Draw(frame)
        draw.text((28, 18), 'Walmart scraper | recorded local review | ' + str(second) + 's', font=font, fill='#93c5fd')
        draw.text((28, 48), 'Offline checks and saved live evidence. No Azure execution shown.', font=font, fill='#fbbf24')
        draw.multiline_text((28, 90), '\n'.join(wrapped[-32:]), font=font, fill='#e5e7eb', spacing=4)
        process.stdin.write(frame.tobytes())
    process.stdin.close()
    if process.wait():
        raise RuntimeError('Video rendering failed')
    print('Rendered', duration, 'seconds')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--font', type=Path, default=Path('/System/Library/Fonts/Menlo.ttc'))
    args = parser.parse_args()
    render(args.source, args.destination, args.font)

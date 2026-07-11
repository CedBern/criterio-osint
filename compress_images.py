import sys, io, os
from pathlib import Path
from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

IMG_DIR = Path("website/images")
MAX_WIDTH = 1600
QUALITY = 80
SKIP = {"og-cover.jpg", "og-cover.png"}

def compress_all():
    total_before = 0
    total_after = 0
    converted = []

    for src in sorted(IMG_DIR.iterdir()):
        if src.name in SKIP:
            continue
        if src.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue

        dest = src.with_suffix(".webp")
        if dest.exists():
            print(f"  SKIP  {src.name} -> deja .webp, ignore")
            continue

        size_before = src.stat().st_size
        total_before += size_before

        try:
            mode = "RGBA" if src.suffix.lower() == ".png" else "RGB"
            img = Image.open(src).convert(mode)
            if img.width > MAX_WIDTH:
                ratio = MAX_WIDTH / img.width
                img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)
            img.save(dest, "WEBP", quality=QUALITY, method=6)
            size_after = dest.stat().st_size
            total_after += size_after
            ratio_pct = (1 - size_after / size_before) * 100
            converted.append((src.name, dest.name, size_before, size_after, ratio_pct))
            print(f"  OK  {src.name:35s} -> {dest.name:35s}  {size_before//1024:6d} Ko -> {size_after//1024:5d} Ko  (-{ratio_pct:.0f}%)")
        except Exception as e:
            print(f"  ERR {src.name}: {e}")

    print()
    print("=" * 70)
    print(f"  Total avant : {total_before / 1024 / 1024:.1f} Mo")
    print(f"  Total apres : {total_after / 1024 / 1024:.1f} Mo")
    if total_before > 0:
        print(f"  Reduction   : -{(1 - total_after / total_before) * 100:.0f}%")
    print(f"  Convertis   : {len(converted)} fichiers")
    print("=" * 70)
    return converted

if __name__ == "__main__":
    print("[*] Compression images -> WebP")
    print(f"    Dossier : {IMG_DIR.resolve()}")
    print()
    compress_all()

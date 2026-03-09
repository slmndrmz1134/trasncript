"""
Video Transkript Aracı
MP4 dosyasını Whisper ile transkript eder ve PDF olarak kaydeder.

Kullanım:
    python transcribe.py video.mp4
    python transcribe.py                  # dizindeki ilk MP4'ü kullanır
    python transcribe.py video.mp4 --model medium --language tr
"""

import sys
import os
import glob
import argparse
import torch

# FFmpeg'i PATH'e ekle (Whisper için gerekli)
FFMPEG_DIR = r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin"
if os.path.isdir(FFMPEG_DIR) and FFMPEG_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
    print(f"✔ FFmpeg PATH'e eklendi: {FFMPEG_DIR}")

import whisper
from fpdf import FPDF
import textwrap


def find_mp4_file():
    """Mevcut dizindeki ilk MP4 dosyasını bulur."""
    mp4_files = glob.glob("*.mp4")
    if not mp4_files:
        print("❌ Dizinde MP4 dosyası bulunamadı!")
        print("   Lütfen bir MP4 dosyasını bu dizine kopyalayın veya dosya adını argüman olarak verin.")
        sys.exit(1)
    print(f"📁 Bulunan MP4 dosyası: {mp4_files[0]}")
    return mp4_files[0]


def transcribe_video(video_path, model_name="small", language=None):
    """Whisper ile videoyu transkript eder."""
    if not os.path.exists(video_path):
        print(f"❌ Dosya bulunamadı: {video_path}")
        sys.exit(1)

    # GPU/CPU seçimi
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n🖥️  Kullanılan cihaz: {device.upper()}")
    if device == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("   ⚠️  CUDA bulunamadı, CPU kullanılıyor.")

    print(f"\n🔄 Whisper modeli yükleniyor: '{model_name}'...")
    model = whisper.load_model(model_name, device=device)

    print(f"🎙️  Transkript ediliyor: {video_path}")
    print("   (Bu işlem birkaç dakika sürebilir...)\n")

    transcribe_options = {"verbose": True}
    if language:
        transcribe_options["language"] = language

    result = model.transcribe(video_path, **transcribe_options)

    print("\n✅ Transkript tamamlandı!")
    return result


def format_timestamp(seconds):
    """Saniyeyi HH:MM:SS formatına çevirir."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_segments(segments):
    """Whisper segment'lerini zaman damgalı metin listesine çevirir."""
    lines = []
    for seg in segments:
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        text = seg["text"].strip()
        if text:
            lines.append(f"[{start} --> {end}]  {text}")
    return lines


def sanitize_text(text):
    """PDF'de sorun çıkarabilecek karakterleri temizler."""
    import re
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    def break_long_word(match):
        word = match.group(0)
        return ' '.join([word[i:i+40] for i in range(0, len(word), 40)])
    text = re.sub(r'\S{50,}', break_long_word, text)
    return text


def save_as_pdf(text, output_path, video_name):
    """Transkript metnini PDF olarak kaydeder."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Unicode desteği için Windows font kullan
    font_path = None
    possible_fonts = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
    ]
    for fp in possible_fonts:
        if os.path.exists(fp):
            font_path = fp
            break

    if font_path:
        pdf.add_font("CustomFont", "", font_path)
        pdf.set_font("CustomFont", size=11)
        title_font = ("CustomFont", "", 16)
        body_font = ("CustomFont", "", 11)
    else:
        pdf.set_font("Helvetica", size=11)
        title_font = ("Helvetica", "B", 16)
        body_font = ("Helvetica", "", 11)

    # Başlık
    pdf.set_font(*title_font)
    pdf.cell(0, 10, f"Transkript: {video_name}",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Ayırıcı çizgi
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    # Metin içeriği
    pdf.set_font(*body_font)

    # Her satırı zaman damgasıyla yaz
    for line in text:
        clean_line = sanitize_text(line)
        pdf.multi_cell(0, 7, clean_line)
        pdf.ln(2)

    pdf.output(output_path)
    print(f"📄 PDF kaydedildi: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="MP4 videoyu transkript edip PDF olarak kaydet")
    parser.add_argument("video", nargs="?", default=None, help="MP4 dosya yolu (belirtilmezse dizindeki ilk MP4 kullanılır)")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model boyutu (varsayılan: small)")
    parser.add_argument("--language", default=None, help="Dil kodu, ör: 'tr', 'en' (belirtilmezse otomatik algılar)")
    parser.add_argument("--output", default=None, help="Çıktı PDF dosya adı (varsayılan: video_adı_transcript.pdf)")
    args = parser.parse_args()

    # Video dosyasını belirle
    video_path = args.video if args.video else find_mp4_file()

    # Çıktı dosya adını belirle
    if args.output:
        output_pdf = args.output
    else:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_pdf = f"{base_name}_transcript.pdf"

    # Transkript et
    result = transcribe_video(video_path, model_name=args.model, language=args.language)

    # Algılanan dili göster
    if "language" in result:
        print(f"🌐 Algılanan dil: {result['language']}")

    # Segment'leri zaman damgalı formata çevir
    segments = result.get("segments", [])
    timestamped_lines = format_segments(segments)

    # TXT olarak kaydet (zaman damgalı)
    txt_path = output_pdf.replace(".pdf", ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(timestamped_lines))
    print(f"📝 TXT kaydedildi: {txt_path}")

    # PDF olarak kaydet (zaman damgalı)
    save_as_pdf(timestamped_lines, output_pdf, os.path.basename(video_path))

    print(f"\n🎉 İşlem tamamlandı!")
    print(f"   PDF: {output_pdf}")
    print(f"   TXT: {txt_path}")


if __name__ == "__main__":
    main()
# backend/reports/report_service.py
from __future__ import annotations

import base64
import mimetypes
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, date

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------- Jinja2 ----------------
TEMPLATES_DIR = Path(__file__).parent / "templates"
ASSETS_DIR = TEMPLATES_DIR / "assets"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

def render_html_string(template_name: str, ctx: dict) -> str:
    tpl = env.get_template(template_name)
    return tpl.render(**ctx)

# --------- helpers ----------

def _file_to_data_uri(p: Path) -> str:
    """Return a data: URL for a given file path (empty string if missing)."""
    if not p.exists():
        return ""
    mime, _ = mimetypes.guess_type(p.name)
    mime = mime or "application/octet-stream"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def _materialize_assets(tmpdir: Path) -> dict:
    """
    Copy (or write) binary assets to the temp dir and return useful paths + data URIs.
    wkhtmltopdf is much happier loading fonts via file:// URLs.
    """
    out = {"logos": {}, "fonts": {}, "print_meta": {}}

    # Logos (data URIs are OK for images; wkhtml handles them fine)
    cuj = ASSETS_DIR / "cuj_logo.png"
    inv = ASSETS_DIR / "invigilink_logo.png"
    out["logos"]["cuj_data"] = _file_to_data_uri(cuj)
    out["logos"]["invigilink_data"] = _file_to_data_uri(inv)

    # Devanagari font: write to a temp location and use file:/// URL in @font-face
    devan_src = ASSETS_DIR / "NotoSansDevanagari-Regular.ttf"
    devan_dst = tmpdir / "NotoSansDevanagari-Regular.ttf"
    if devan_src.exists():
        devan_dst.write_bytes(devan_src.read_bytes())
        out["fonts"]["devanagari_path"] = f"file:///{str(devan_dst).replace(os.sep, '/')}"
    else:
        out["fonts"]["devanagari_path"] = ""  # header will gracefully fallback

    # Footer meta
    out["print_meta"] = {
        "generated_at": datetime.now(),
        "app": "Invigilink-AI – Prototype phase • Made by Mrigank J.",
    }
    return out

def _wkhtml_margins_for(ctx: dict) -> dict:
    """
    Choose margins/spacing. Compact can be enabled by:
      - ctx["pdf_layout"] == "compact"
      - ctx["pdf_compact"] == True
      - env PDF_LAYOUT=COMPACT
    """
    compact_flag = (
        (str(os.getenv("PDF_LAYOUT", "")).upper() == "COMPACT")
        or (str(ctx.get("pdf_layout", "")).lower() == "compact")
        or bool(ctx.get("pdf_compact"))
    )
    if compact_flag:
        return {
            "top": "34mm",
            "right": "12mm",
            "bottom": "16mm",
            "left": "12mm",
            "header_spacing": "4",
            "footer_spacing": "2",
        }
    return {
        "top": "40mm",
        "right": "14mm",
        "bottom": "18mm",
        "left": "14mm",
        "header_spacing": "6",
        "footer_spacing": "3",
    }

# -------------- PDF engines --------------
WEASY_AVAILABLE = False
WEASY_IMPORT_ERROR = None
try:
    from weasyprint import HTML  # type: ignore
    WEASY_AVAILABLE = True
except Exception as e:
    WEASY_AVAILABLE = False
    WEASY_IMPORT_ERROR = str(e)

USE_WKHTML = True  # we prefer wkhtmltopdf for proper running header/footer
WKHTML_PATH = os.getenv("WKHTMLTOPDF_PATH", "wkhtmltopdf")

def _render_weasy(html_str: str) -> bytes:
    return HTML(string=html_str).write_pdf()

def _render_wkhtml(html_str: str, body_ctx: dict) -> bytes:
    """
    Render HTML -> PDF using wkhtmltopdf with repeating header and footer.
    """
    margins = _wkhtml_margins_for(body_ctx)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        in_html = td_path / "in.html"
        out_pdf = td_path / "out.pdf"
        in_html.write_text(html_str, encoding="utf-8")

        # Materialize assets and render header/footer with those paths/URIs
        asset_ctx = _materialize_assets(td_path)
        header_ctx = dict(body_ctx or {}, **asset_ctx)
        footer_ctx = dict(body_ctx or {}, **asset_ctx)

        header_html = render_html_string("_pdf_header.html", header_ctx)
        header_path = td_path / "header.html"
        header_path.write_text(header_html, encoding="utf-8")

        footer_path = None
        footer_tpl = (TEMPLATES_DIR / "_pdf_footer.html")
        if footer_tpl.exists():
            footer_html = render_html_string("_pdf_footer.html", footer_ctx)
            footer_path = td_path / "footer.html"
            footer_path.write_text(footer_html, encoding="utf-8")

        cmd = [
            WKHTML_PATH,
            "--enable-local-file-access",         # allow file:/// font loading
            "--encoding", "UTF-8",
            "--page-size", "A4",
            "--margin-top", margins["top"],
            "--margin-right", margins["right"],
            "--margin-bottom", margins["bottom"],
            "--margin-left", margins["left"],
            "--header-html", str(header_path),
            "--header-spacing", margins["header_spacing"],
        ]
        if footer_path:
            cmd += ["--footer-html", str(footer_path), "--footer-spacing", margins["footer_spacing"]]

        cmd += [str(in_html), str(out_pdf)]
        subprocess.run(cmd, check=True)
        return out_pdf.read_bytes()

# ------------- Helpers / validation -------------
def _normalize_pdf_prefix(b: bytes) -> bytes:
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return b.lstrip()

def _looks_like_pdf(data: bytes) -> bool:
    if not data or len(data) < 100:
        return False
    head = _normalize_pdf_prefix(data[:16])
    if not head.startswith(b"%PDF"):
        return False
    tail = data[-2048:] if len(data) > 2048 else data
    return b"%%EOF" in tail

def _swap_ext(template_name: str, new_ext: str) -> str:
    p = Path(template_name)
    if p.suffix:
        return str(p.with_suffix(new_ext))
    return f"{template_name}{new_ext}"

# ------------- Public API -------------
def render_pdf_or_html_download(template_name: str, ctx: dict) -> tuple[bytes, str, str]:
    """
    Main entry used by routes. Prefer PDF; fall back to HTML (so downloads never corrupt).
    """
    html = render_html_string(template_name, ctx)

    if os.getenv("PDF_DISABLED") == "1":
        return html.encode("utf-8"), _swap_ext(template_name, ".html"), "text/html"

    # Try WeasyPrint first (optional)
    if WEASY_AVAILABLE:
        try:
            pdf = _render_weasy(html)
            if _looks_like_pdf(pdf):
                return pdf, _swap_ext(template_name, ".pdf"), "application/pdf"
        except Exception:
            pass

    # Use wkhtmltopdf for header/footer
    try:
        pdf = _render_wkhtml(html, ctx)
        if _looks_like_pdf(pdf):
            return pdf, _swap_ext(template_name, ".pdf"), "application/pdf"
    except Exception:
        pass

    # Fallback: HTML
    return html.encode("utf-8"), _swap_ext(template_name, ".html"), "text/html"

def render_pdf_bytes(template_name: str, ctx: dict) -> tuple[bytes, str, str]:
    html = render_html_string(template_name, ctx)

    if WEASY_AVAILABLE:
        try:
            pdf = _render_weasy(html)
            if _looks_like_pdf(pdf):
                return pdf, _swap_ext(template_name, ".pdf"), "application/pdf"
        except Exception:
            pass

    try:
        pdf = _render_wkhtml(html, ctx)
        if _looks_like_pdf(pdf):
            return pdf, _swap_ext(template_name, ".pdf"), "application/pdf"
    except Exception:
        pass

    return html.encode("utf-8"), _swap_ext(template_name, ".html"), "text/html"

# ------------- Jinja filters -------------
def _strftime(fmt: str = "%Y-%m-%d", value: date | datetime | None = None) -> str:
    dt = value or datetime.now()
    try:
        if isinstance(dt, (datetime, date)):
            return dt.strftime(fmt)
        return str(dt)
    except Exception:
        return ""

env.filters["strftime"] = _strftime

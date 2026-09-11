"""Bounded offline OCR for scanned FORGE service-manual pages.

OCR output is evidence-bearing *untrusted reference text*.  It never executes
manufacturer content, never grants repair authority and never silently upgrades
an unqualified development runtime into a production-qualified dependency.

The default renderer is pypdfium2/PDFium and the default OCR engine is the local
Tesseract CLI. The renderer choice is intentionally permissive-license oriented
for proprietary deployment; dependency licensing still remains an admission gate.  Both are version-gated for production.  Tests can inject fake
renderers/engines so core custody logic remains testable without those optional
native dependencies.

Qualification extraction note: this file is source-extracted from the authoritative
V8 cumulative patch. The only V9 runtime change is forwarding an existing
LD_LIBRARY_PATH into Tesseract subprocess environments so the qualified bundled
native closure can resolve. stable_hash is supplied by the harness only for the
serialization method and is not involved in renderer/engine qualification.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Protocol, Sequence, Tuple

try:
    from .provenance import stable_hash
except ImportError:
    import json
    def stable_hash(value: Any) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()

SCHEMA = "mft.forge1.manual_ocr.v1"
REQUIRED_TESSERACT_VERSION = "5.5.3"
REQUIRED_PYPDFIUM2_VERSION = "5.13.0"
DEFAULT_DPI = 250
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_IMAGE_BYTES = 48 * 1024 * 1024
DEFAULT_MAX_PIXELS = 30_000_000
DEFAULT_MAX_TSV_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_TEXT_CHARS = 250_000
DEFAULT_MIN_TEXT_CHARS = 8
DEFAULT_MIN_MEAN_CONFIDENCE = 50.0
DEFAULT_MAX_OCR_PAGES = 64
_VERSION_RE = re.compile(r"(?P<version>\d+\.\d+(?:\.\d+)?)")

class ManualOcrError(ValueError):
    """Raised when OCR cannot produce a bounded, custody-preserving result."""

@dataclass(frozen=True)
class RenderedOcrPage:
    page: int
    image_bytes: bytes
    width_px: int
    height_px: int
    image_format: str = "PNG"
    dpi: int = DEFAULT_DPI

    def validated(self) -> "RenderedOcrPage":
        if self.page < 1:
            raise ManualOcrError("OCR page numbers are 1-based positive integers")
        if self.width_px < 1 or self.height_px < 1:
            raise ManualOcrError("rendered OCR page dimensions must be positive")
        if not 72 <= int(self.dpi) <= 600:
            raise ManualOcrError("rendered OCR page dpi must be within 72..600")
        if not isinstance(self.image_bytes, (bytes, bytearray)) or not self.image_bytes:
            raise ManualOcrError("rendered OCR page contains no image bytes")
        if len(self.image_bytes) > DEFAULT_MAX_IMAGE_BYTES:
            raise ManualOcrError("rendered OCR page exceeds configured image-byte limit")
        if self.width_px * self.height_px > DEFAULT_MAX_PIXELS:
            raise ManualOcrError("rendered OCR page exceeds configured pixel limit")
        return self

    @property
    def image_sha256(self) -> str:
        return hashlib.sha256(bytes(self.image_bytes)).hexdigest()

@dataclass(frozen=True)
class OcrEngineText:
    text: str
    mean_confidence: float | None
    word_count: int

@dataclass(frozen=True)
class ManualOcrPageEvidence:
    page: int
    status: str
    text: str
    text_sha256: str
    text_chars: int
    word_count: int
    mean_confidence: float | None
    image_sha256: str
    image_bytes: int
    width_px: int
    height_px: int

    def as_dict(self, *, include_text: bool = False) -> Dict[str, Any]:
        value = asdict(self)
        if not include_text:
            value.pop("text", None)
        return value

@dataclass(frozen=True)
class OcrRuntimeIdentity:
    renderer: str
    renderer_version: str
    ocr_engine: str
    ocr_engine_version: str
    renderer_qualified: bool
    ocr_engine_qualified: bool
    ocr_binary_path: str
    ocr_binary_sha256: str

    @property
    def qualified(self) -> bool:
        return self.renderer_qualified and self.ocr_engine_qualified

    def as_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "qualified": self.qualified,
            "required_renderer_version": REQUIRED_PYPDFIUM2_VERSION,
            "required_ocr_engine_version": REQUIRED_TESSERACT_VERSION,
        }

@dataclass(frozen=True)
class ManualOcrExtraction:
    source_sha256: str
    pages: Tuple[ManualOcrPageEvidence, ...]
    runtime: OcrRuntimeIdentity
    dpi: int
    language: str

    @property
    def extracted_pages(self) -> Dict[int, str]:
        return {
            row.page: row.text
            for row in self.pages
            if row.status == "OCR_EXTRACTED" and row.text
        }

    def as_dict(self, *, include_text: bool = False) -> Dict[str, Any]:
        material: Dict[str, Any] = {
            "schema": SCHEMA + ".extraction.v1",
            "source_sha256": self.source_sha256,
            "dpi": self.dpi,
            "language": self.language,
            "runtime": self.runtime.as_dict(),
            "pages": [row.as_dict(include_text=include_text) for row in self.pages],
            "truth_boundary": {
                "ocr_text_is_untrusted_reference_content": True,
                "ocr_text_is_not_diagram_semantics": True,
                "source_pdf_or_ocr_text_executed": False,
                "network_required": False,
                "hardware_actions_still_require_safety_authority": True,
                "runtime_qualification_is_dependency_qualification_not_capability_superiority": True,
            },
        }
        material["ocr_extraction_sha256"] = stable_hash(material)
        return material

class PageRenderer(Protocol):
    name: str
    version: str
    def page_count(self, pdf_path: Path) -> int: ...
    def render(self, pdf_path: Path, page: int, *, dpi: int) -> RenderedOcrPage: ...

class OcrEngine(Protocol):
    name: str
    version: str
    binary_path: str
    binary_sha256: str
    def recognize(self, image: RenderedOcrPage, *, language: str, timeout_seconds: float) -> OcrEngineText: ...

def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _normalize_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)

class PdfiumRenderer:
    """Render PDF pages through pypdfium2 / PDFium."""
    name = "pypdfium2"

    def __init__(self) -> None:
        try:
            import pypdfium2 as pdfium
            from pypdfium2.version import PYPDFIUM_INFO, PDFIUM_INFO
        except Exception as exc:
            raise ManualOcrError("pypdfium2 renderer dependency is unavailable") from exc
        self._pdfium = pdfium
        self.version = str(PYPDFIUM_INFO)
        self.pdfium_version = str(PDFIUM_INFO)

    def _open(self, pdf_path: Path):
        try:
            return self._pdfium.PdfDocument(str(pdf_path))
        except Exception as exc:
            raise ManualOcrError("OCR renderer could not open manual PDF; encrypted PDFs are not eligible") from exc

    def page_count(self, pdf_path: Path) -> int:
        doc = self._open(pdf_path)
        try:
            return int(len(doc))
        finally:
            doc.close()

    def render(self, pdf_path: Path, page: int, *, dpi: int) -> RenderedOcrPage:
        doc = self._open(pdf_path)
        try:
            count = int(len(doc))
            if page < 1 or page > count:
                raise ManualOcrError(f"OCR page {page} is outside the PDF page range")
            p = doc[page - 1]
            try:
                width_pt, height_pt = p.get_size()
                scale = float(dpi) / 72.0
                width = max(1, int(round(float(width_pt) * scale)))
                height = max(1, int(round(float(height_pt) * scale)))
                if width * height > DEFAULT_MAX_PIXELS:
                    raise ManualOcrError("rendered OCR page would exceed configured pixel limit")
                bitmap = p.render(scale=scale, rotation=0)
                try:
                    image = bitmap.to_pil()
                    output = io.BytesIO()
                    image.save(output, format="PNG")
                    image_bytes = output.getvalue()
                    rendered = RenderedOcrPage(
                        page=page,
                        image_bytes=image_bytes,
                        width_px=int(image.width),
                        height_px=int(image.height),
                        image_format="PNG",
                        dpi=int(dpi),
                    ).validated()
                finally:
                    bitmap.close()
                return rendered
            except ManualOcrError:
                raise
            except Exception as exc:
                raise ManualOcrError(f"failed to render OCR page {page}") from exc
            finally:
                p.close()
        finally:
            doc.close()

class TesseractCliEngine:
    name = "tesseract"

    def __init__(self, binary: str = "tesseract") -> None:
        resolved = shutil.which(binary)
        if not resolved:
            raise ManualOcrError("Tesseract OCR binary is unavailable")
        path = Path(resolved).resolve()
        if not path.is_file():
            raise ManualOcrError("Tesseract OCR binary path is not a regular file")
        self.binary_path = str(path)
        self.binary_sha256 = _sha256_path(path)
        env = {"PATH": os.environ.get("PATH", "")}
        if os.environ.get("LD_LIBRARY_PATH"):
            env["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]
        try:
            probe = subprocess.run(
                [self.binary_path, "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=5.0,
                env=env,
            )
        except Exception as exc:
            raise ManualOcrError("unable to identify Tesseract OCR runtime") from exc
        first = probe.stdout.decode("utf-8", "replace").splitlines()[0] if probe.stdout else ""
        match = _VERSION_RE.search(first)
        self.version = match.group("version") if match else "unknown"

    def recognize(self, image: RenderedOcrPage, *, language: str, timeout_seconds: float) -> OcrEngineText:
        image = image.validated()
        if not re.fullmatch(r"[A-Za-z0-9_+-]{2,64}", str(language or "")):
            raise ManualOcrError("OCR language token is invalid")
        argv = [
            self.binary_path,
            "stdin",
            "stdout",
            "--dpi",
            str(int(image.dpi)),
            "-l",
            language,
            "--psm",
            "6",
            "tsv",
        ]
        env = {
            "PATH": os.environ.get("PATH", ""),
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            **({"TESSDATA_PREFIX": os.environ["TESSDATA_PREFIX"]} if os.environ.get("TESSDATA_PREFIX") else {}),
        }
        if os.environ.get("LD_LIBRARY_PATH"):
            env["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]
        try:
            run = subprocess.run(
                argv,
                input=bytes(image.image_bytes),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=float(timeout_seconds),
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise ManualOcrError(f"OCR timed out on page {image.page}") from exc
        if run.returncode != 0:
            stderr = run.stderr.decode("utf-8", "replace")[:1000]
            raise ManualOcrError(f"Tesseract OCR failed on page {image.page}: {stderr}")
        if len(run.stdout) > DEFAULT_MAX_TSV_BYTES:
            raise ManualOcrError("OCR engine output exceeds configured byte limit")
        decoded = run.stdout.decode("utf-8", "replace")
        reader = csv.DictReader(io.StringIO(decoded), delimiter="\t")
        words: list[str] = []
        confidences: list[float] = []
        line_key: tuple[str, ...] | None = None
        lines: list[list[str]] = []
        for row in reader:
            text = str(row.get("text") or "").strip()
            if not text:
                continue
            current = tuple(str(row.get(name) or "") for name in ("page_num", "block_num", "par_num", "line_num"))
            if current != line_key:
                lines.append([])
                line_key = current
            lines[-1].append(text)
            words.append(text)
            try:
                confidence = float(row.get("conf") or -1)
            except ValueError:
                confidence = -1
            if 0.0 <= confidence <= 100.0:
                confidences.append(confidence)
        text = _normalize_text("\n".join(" ".join(parts) for parts in lines if parts))
        if len(text) > DEFAULT_MAX_TEXT_CHARS:
            raise ManualOcrError("OCR text exceeds configured character limit")
        mean_confidence = round(sum(confidences) / len(confidences), 4) if confidences else None
        return OcrEngineText(text=text, mean_confidence=mean_confidence, word_count=len(words))

def identify_runtime(renderer: PageRenderer, engine: OcrEngine) -> OcrRuntimeIdentity:
    return OcrRuntimeIdentity(
        renderer=str(renderer.name),
        renderer_version=str(renderer.version),
        ocr_engine=str(engine.name),
        ocr_engine_version=str(engine.version),
        renderer_qualified=str(renderer.version) == REQUIRED_PYPDFIUM2_VERSION,
        ocr_engine_qualified=str(engine.version) == REQUIRED_TESSERACT_VERSION,
        ocr_binary_path=str(engine.binary_path),
        ocr_binary_sha256=str(engine.binary_sha256),
    )

def ocr_manual_pdf_pages(
    pdf_path: str | Path,
    source_sha256: str,
    page_numbers: Sequence[int],
    *,
    language: str = "eng",
    dpi: int = DEFAULT_DPI,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    renderer: PageRenderer | None = None,
    engine: OcrEngine | None = None,
    require_qualified_runtime: bool = True,
    min_text_chars: int = DEFAULT_MIN_TEXT_CHARS,
    min_mean_confidence: float = DEFAULT_MIN_MEAN_CONFIDENCE,
    max_ocr_pages: int = DEFAULT_MAX_OCR_PAGES,
) -> ManualOcrExtraction:
    """OCR an explicit bounded set of PDF pages and return custody evidence."""
    path = Path(pdf_path)
    if not path.is_file() or path.is_symlink():
        raise ManualOcrError("OCR source PDF must be a regular non-symlink file")
    declared_sha = str(source_sha256 or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", declared_sha):
        raise ManualOcrError("OCR source_sha256 must be a 64-character hexadecimal digest")
    observed_sha = _sha256_path(path)
    if observed_sha != declared_sha:
        raise ManualOcrError("OCR source PDF SHA-256 does not match declared source_sha256")
    if not 72 <= int(dpi) <= 600:
        raise ManualOcrError("OCR dpi must be within 72..600")
    if not 0.1 <= float(timeout_seconds) <= 300.0:
        raise ManualOcrError("OCR timeout_seconds must be within 0.1..300")
    pages = tuple(sorted({int(page) for page in page_numbers}))
    if not pages:
        raise ManualOcrError("OCR requires at least one explicit page")
    if any(page < 1 for page in pages):
        raise ManualOcrError("OCR page numbers are 1-based positive integers")
    if len(pages) > int(max_ocr_pages):
        raise ManualOcrError("OCR page request exceeds configured page-count limit")
    if not 0.0 <= float(min_mean_confidence) <= 100.0:
        raise ManualOcrError("OCR min_mean_confidence must be within 0..100")
    renderer = renderer or PdfiumRenderer()
    engine = engine or TesseractCliEngine()
    runtime = identify_runtime(renderer, engine)
    if require_qualified_runtime and not runtime.qualified:
        raise ManualOcrError(
            "OCR runtime is not qualified: "
            f"renderer {runtime.renderer_version} (required {REQUIRED_PYPDFIUM2_VERSION}), "
            f"tesseract {runtime.ocr_engine_version} (required {REQUIRED_TESSERACT_VERSION})"
        )
    page_count = int(renderer.page_count(path))
    if page_count < 1:
        raise ManualOcrError("OCR source PDF contains no pages")
    if pages[-1] > page_count:
        raise ManualOcrError("OCR page request exceeds source PDF page count")
    evidence: list[ManualOcrPageEvidence] = []
    for page in pages:
        rendered = renderer.render(path, page, dpi=int(dpi)).validated()
        recognized = engine.recognize(rendered, language=language, timeout_seconds=float(timeout_seconds))
        text = _normalize_text(recognized.text)
        if len(text) > DEFAULT_MAX_TEXT_CHARS:
            raise ManualOcrError("OCR text exceeds configured character limit")
        if len(text.strip()) < int(min_text_chars):
            status = "OCR_EMPTY"
        elif recognized.mean_confidence is None or float(recognized.mean_confidence) < float(min_mean_confidence):
            status = "OCR_LOW_CONFIDENCE"
        else:
            status = "OCR_EXTRACTED"
        stored_text = text if status != "OCR_EMPTY" else ""
        evidence.append(
            ManualOcrPageEvidence(
                page=page,
                status=status,
                text=stored_text,
                text_sha256=hashlib.sha256(stored_text.encode("utf-8")).hexdigest(),
                text_chars=len(stored_text),
                word_count=int(recognized.word_count) if stored_text else 0,
                mean_confidence=recognized.mean_confidence if stored_text else None,
                image_sha256=rendered.image_sha256,
                image_bytes=len(rendered.image_bytes),
                width_px=rendered.width_px,
                height_px=rendered.height_px,
            )
        )
    return ManualOcrExtraction(
        source_sha256=observed_sha,
        pages=tuple(evidence),
        runtime=runtime,
        dpi=int(dpi),
        language=language,
    )

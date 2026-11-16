"""OCR + bill field detection. Everything here is best-effort: results are
suggestions only and must be verified by the user before they are saved."""
import io
import re
import shutil

from helpers import STATES

LANGS = {"English": "eng", "Hindi": "hin", "Marathi": "mar"}

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

DISCOMS = [
    (r"msedcl|mahavitaran|mahadiscom|महावितरण|maharashtra state electricity", "MSEDCL / Mahavitaran", "Maharashtra"),
    (r"tata\s*power\s*(?:co|company)?\s*(?:ltd)?\s*(?:-|–)?\s*(?:mumbai|distribution)", "Tata Power (Mumbai)", "Maharashtra"),
    (r"adani\s*electricity", "Adani Electricity Mumbai", "Maharashtra"),
    (r"brihanmumbai electric|\bbest\s+undertaking", "BEST", "Maharashtra"),
    (r"bses\s*rajdhani", "BSES Rajdhani", "Delhi"),
    (r"bses\s*yamuna", "BSES Yamuna", "Delhi"),
    (r"tpddl|tata power delhi", "TPDDL", "Delhi"),
    (r"bescom|bangalore electricity", "BESCOM", "Karnataka"),
    (r"tangedco|tnpdcl|\btneb\b", "TNPDCL (TANGEDCO)", "Tamil Nadu"),
    (r"pgvcl|dgvcl|mgvcl|ugvcl", "Gujarat DISCOM (GUVNL)", "Gujarat"),
    (r"torrent\s*power", "Torrent Power", "Gujarat"),
    (r"tgspdcl|tsspdcl|tgnpdcl", "TGSPDCL / TGNPDCL", "Telangana"),
    (r"apspdcl|apepdcl|apcpdcl", "AP DISCOM", "Andhra Pradesh"),
    (r"\bkseb", "KSEB", "Kerala"),
    (r"wbsedcl", "WBSEDCL", "West Bengal"),
    (r"\bcesc\b", "CESC", "West Bengal"),
    (r"uppcl|pvvnl|mvvnl|dvvnl|puvvnl|kesco", "UPPCL", "Uttar Pradesh"),
    (r"jvvnl|ajmer vidyut|jodhpur vidyut", "Rajasthan DISCOM", "Rajasthan"),
    (r"uhbvn|dhbvn", "Haryana DISCOM", "Haryana"),
    (r"pspcl", "PSPCL", "Punjab"),
]

_NUM = r"(\d[\d,]*(?:\.\d+)?)(?![\d/])"

AMOUNT_PATTERNS = [
    r"net\s*(?:bill\s*)?amount\s*(?:payable)?[^\d\n]{0,30}" + _NUM,
    r"(?:total\s*)?(?:amount\s*)?payable\s*(?:amount|by\s*due\s*date)?[^\d\n]{0,30}" + _NUM,
    r"net\s*payable[^\d\n]{0,30}" + _NUM,
    r"(?:current\s*)?(?:total\s*)?bill\s*amount[^\d\n]{0,30}" + _NUM,
    r"(?:एकूण\s*देय|देय\s*रक्कम|कुल\s*देय)[^\d\n]{0,30}" + _NUM,
]
UNIT_PATTERNS = [
    r"(?:units?\s*consumed|total\s*units?|net\s*units?|billed\s*units?|energy\s*consumed|consumption)[^\d\n]{0,30}" + _NUM,
    r"(?:वीज\s*वापर|एकूण\s*युनिट|युनिट)[^\d\n]{0,30}" + _NUM,
    _NUM + r"\s*(?:kwh|units)\b",
]


# ----------------------------------------------------------------- status
def ocr_status():
    """Return (tesseract_available, list_of_installed_language_names)."""
    if not shutil.which("tesseract"):
        return False, []
    try:
        import pytesseract
        installed = set(pytesseract.get_languages(config=""))
    except Exception:
        return False, []
    return True, [name for name, code in LANGS.items() if code in installed]


# ------------------------------------------------------------- extraction
SEP = "\n=== OCR TEXT (image reading) ===\n"


def looks_garbled(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 40 or t.count("(cid:") > 3:
        return True
    ok = sum(1 for ch in t if ch.isspace() or ch.isascii() and (ch.isalnum() or ch in ".,:;/-()%&|₹")
             or "ऀ" <= ch <= "ॿ" or ch == "₹")
    return ok / len(t) < 0.85 or not re.search(r"\d", t)


def _pdf_text(data: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages[:6])
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:6])
    except Exception:
        return ""


def _pdf_images(data: bytes, dpi: int):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return [p.to_image(resolution=dpi).original for p in pdf.pages[:2]]
    except Exception:
        pass
    try:
        from pdf2image import convert_from_bytes
        return convert_from_bytes(data, dpi=dpi, first_page=1, last_page=2)
    except Exception:
        return []


def _open_image(data: bytes):
    try:
        from PIL import Image
        return [Image.open(io.BytesIO(data))]
    except Exception:
        return []


def _ocr(images, language: str, notes: list) -> str:
    ready, installed = ocr_status()
    if not ready:
        notes.append("OCR engine (Tesseract) is not available on this server. Please enter the values manually.")
        return ""
    import pytesseract
    from PIL import ImageOps

    codes = ["eng"]
    if language != "English":
        if language in installed:
            codes.append(LANGS[language])
        elif "Hindi" in installed:
            codes.append("hin")  # Devanagari fallback: reads Marathi script reasonably well
            notes.append(f"{language} OCR data is not installed, so Hindi (Devanagari) OCR was used instead.")
        else:
            notes.append(f"{language} OCR data is not installed, so English OCR was used.")
    out = []
    for img in images:
        try:
            g = ImageOps.autocontrast(ImageOps.grayscale(img))
            out.append(pytesseract.image_to_string(g, lang="+".join(codes), config="--psm 6"))
        except Exception:
            notes.append("One page could not be read by OCR.")
    return "\n".join(out)


def extract_text(data: bytes, filename: str, language: str, force_ocr: bool = False, dpi: int = 250):
    """Return (text, method, notes). Never raises.

    Many PDFs (e.g. MSEDCL) have a text layer whose NUMBERS are reliable even though
    regional-language labels are garbled. So the text layer is parsed first, and OCR is
    only added when key values are missing (or when the user forces OCR).
    """
    notes = []
    try:
        if filename.lower().endswith(".pdf"):
            layer = _pdf_text(data)
            if not force_ocr and layer.strip():
                p = parse_bill(layer)
                if p["units"] is not None and p["amount"] is not None and p["month"]:
                    return layer, "PDF text layer", notes
            images = _pdf_images(data, dpi)
            if not images:
                if layer.strip():
                    return layer, "PDF text layer", notes
                notes.append("We could not open this PDF for OCR. Please enter the values manually.")
                return "", "none", notes
            ocr = _ocr(images, language, notes)
            if layer.strip() and ocr.strip():
                return layer + SEP + ocr, "PDF text layer + OCR", notes
            if ocr.strip():
                return ocr, "OCR", notes
            return layer, ("PDF text layer" if layer.strip() else "none"), notes
        images = _open_image(data)
        if not images:
            notes.append("We could not open this image. Please enter the values manually.")
            return "", "none", notes
        return _ocr(images, language, notes), "OCR", notes
    except Exception:
        notes.append("Something went wrong while reading this file. Please enter the values manually.")
        return "", "none", notes


# ---------------------------------------------------------------- parsing
MONTH_DEV = {
    "जानेवारी": 1, "जानेवरी": 1, "फेब्रुवारी": 2, "फेब्रुअरी": 2, "फरवरी": 2, "मार्च": 3,
    "एप्रिल": 4, "अप्रैल": 4, "मे": 5, "मई": 5, "जून": 6, "जुलै": 7, "जुलाई": 7,
    "ऑगस्ट": 8, "अगस्त": 8, "सप्टेंबर": 9, "सितंबर": 9, "सितम्बर": 9, "ऑक्टोबर": 10,
    "अक्टूबर": 10, "अक्तूबर": 10, "नोव्हेंबर": 11, "नवंबर": 11, "नवम्बर": 11,
    "डिसेंबर": 12, "दिसंबर": 12, "दिसम्बर": 12,
}
_DEV_RE = re.compile("(" + "|".join(sorted(MONTH_DEV, key=len, reverse=True)) + r")\s*[-–/,]?\s*(20\d{2})")
_MSEDCL_RE = re.compile(r"msedcl|mahavitaran|mahadiscom|महावितरण|maharashtra state electricity", re.I)
# MSEDCL reading row: [current] previous  multiplier  units  adjusted-units  total-units
_READING_ROW = re.compile(
    r"(?<![\d.])(?:(\d{3,7})\s+)?(\d{3,7})\s+(\d+\.\d{2})\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)(?![\d.])")
_RS = re.compile(r"Rs\.?\s*(\d[\d,]*\.\d{2})", re.I)
_TOP_AMOUNT = re.compile(r"^[^\n\d]{0,60}:\s*(\d[\d,]*\.\d{2})\s*$", re.M)


def _to_float(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _find_month(s: str):
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?[\s\-/,']*((?:20)?\d{2})\b", s, re.I)
    if m:
        y = int(m.group(2))
        return MONTH_MAP[m.group(1).lower()[:3]], (y + 2000 if y < 100 else y)
    m = re.search(r"\b\d{1,2}[/\-.](\d{1,2})[/\-.](20\d{2})\b", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(0?[1-9]|1[0-2])[/\-.](20\d{2})\b", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _empty():
    return {"month": None, "year": None, "units": None, "amount": None, "amount_candidates": [],
            "discom": "", "state": "", "notes": [], "info": [], "month_notes": []}


def _parse_one(text: str) -> dict:
    res = _empty()
    try:
        t = (text or "").translate(_DEVANAGARI_DIGITS)
        if not t.strip():
            return res
        low = t.lower()
        lines = t.splitlines()

        # DISCOM / State
        for pat, name, state in DISCOMS:
            if re.search(pat, low, re.I):
                res["discom"], res["state"] = name, state
                break
        if not res["state"]:
            for s in STATES:
                if s.lower() in low:
                    res["state"] = s
                    break
        is_msedcl = bool(_MSEDCL_RE.search(t)) or res["discom"].startswith("MSEDCL")

        # ---- Billing month
        found = None
        if not is_msedcl:  # MSEDCL's "Bill Period" line is followed by the NEXT reading date -> skip it
            for i, line in enumerate(lines):
                if re.search(r"bill(?:ing)?\s*(?:month|period|date|for)|billing\s*cycle|महिना|बिल\s*माह", line, re.I):
                    found = _find_month(line + " " + (lines[i + 1] if i + 1 < len(lines) else ""))
                    if found:
                        break
        if not found:
            m = _DEV_RE.search("\n".join(lines[:25]))
            if m:
                found = (MONTH_DEV[m.group(1)], int(m.group(2)))
        if not found and is_msedcl:
            for line in lines[:15]:
                m = re.search(r"\b(\d{2})-(\d{2})-(20\d{2})\b", line)
                if m and 1 <= int(m.group(2)) <= 12:
                    found = (int(m.group(2)), int(m.group(3)))
                    res["month_notes"].append(("info", "Billing month was taken from the bill date. Please confirm it matches the bill heading."))
                    break
        if not found:
            found = _find_month(t)
            if found:
                res["month_notes"].append(("warn", "Billing month was guessed from a date in the bill. Please verify it."))
        if found:
            res["month"], res["year"] = found

        # ---- Units
        m = _READING_ROW.search(t)
        if m:
            cur, prev, mult, total = _to_float(m.group(1)), _to_float(m.group(2)), _to_float(m.group(3)), _to_float(m.group(6))
            ok = cur is None or abs((cur - prev) * (mult or 1) - _to_float(m.group(4))) < 1.0
            if total is not None and total > 0 and ok:
                res["units"] = total
        if res["units"] is None:
            for pat in UNIT_PATTERNS:
                m = re.search(pat, t, re.I)
                if m:
                    v = _to_float(m.group(1))
                    if v is not None:
                        res["units"] = v
                        break

        # ---- Amount
        cands, labelled = [], []
        if is_msedcl:
            rs_vals = sorted({_to_float(x) for x in _RS.findall(t) if _to_float(x)})
            tops = [_to_float(x) for x in _TOP_AMOUNT.findall(t)]
            top = tops[0] if tops else None
            if top is not None and 1 <= top <= 10_000_000:
                labelled.append(top)  # amount payable by the due date (top box of the bill)
            elif len(rs_vals) == 3:
                labelled.append(rs_vals[1])  # pay-early < payable on due date < pay-late
            cands += rs_vals
        for pat in AMOUNT_PATTERNS:
            for m in re.finditer(pat, t, re.I):
                v = _to_float(m.group(1))
                if v is not None and 1 <= v <= 10_000_000:
                    if not is_msedcl:
                        labelled.append(v)
                    cands.append(v)
        for m in re.finditer(r"(?:₹|rs\.?|inr)\s*" + _NUM, t, re.I):
            v = _to_float(m.group(1))
            if v is not None and 1 <= v <= 10_000_000:
                cands.append(v)
        seen, uniq = set(), []
        for v in labelled + cands:
            if v not in seen:
                seen.add(v)
                uniq.append(v)
        res["amount_candidates"] = uniq[:8]
        if labelled:
            res["amount"] = labelled[0]
    except Exception:
        res["notes"].append("Some details could not be read automatically.")
    return res


def parse_bill(text: str) -> dict:
    """Detect fields. Parses the PDF text layer and the OCR text separately and merges,
    preferring the first source that found each value. Values may be None."""
    out = _empty()
    try:
        results = [_parse_one(p) for p in (text or "").split(SEP)]
    except Exception:
        out["notes"].append("Some details could not be read automatically.")
        return out
    for r in results:
        for k in ("units", "amount"):
            if out[k] is None and r[k] is not None:
                out[k] = r[k]
        if out["month"] is None and r["month"]:
            out["month"], out["year"] = r["month"], r["year"]
            for lvl, msg in r["month_notes"]:
                (out["info"] if lvl == "info" else out["notes"]).append(msg)
        if not out["discom"] and r["discom"]:
            out["discom"], out["state"] = r["discom"], r["state"]
        elif not out["state"] and r["state"]:
            out["state"] = r["state"]
        for v in r["amount_candidates"]:
            if v not in out["amount_candidates"]:
                out["amount_candidates"].append(v)
        for n in r["notes"]:
            if n not in out["notes"]:
                out["notes"].append(n)
    out["amount_candidates"] = out["amount_candidates"][:8]
    return out

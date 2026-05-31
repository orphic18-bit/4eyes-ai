"""
4eyes.ai — Phase 4: Streamlit Frontend
Contract Intelligence Platform
"""

import streamlit as st
import tempfile
import os
import sys
import io
from pathlib import Path

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="4eyes.ai — Contract Intelligence",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0A0A0F;
    color: #E8E4DC;
}

/* Kill default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1100px; }

/* ── Brand header ── */
.brand-header {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
}
.brand-name {
    font-family: 'DM Serif Display', serif;
    font-size: 2.6rem;
    color: #E8E4DC;
    letter-spacing: -0.02em;
    line-height: 1;
}
.brand-dot {
    font-family: 'DM Serif Display', serif;
    font-size: 2.6rem;
    color: #C8F55A;
    line-height: 1;
}
.brand-tagline {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #6B6860;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 2.5rem;
}

/* ── Divider ── */
.hairline {
    border: none;
    border-top: 1px solid #1E1E26;
    margin: 2rem 0;
}

/* ── Section labels ── */
.section-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #6B6860;
    margin-bottom: 0.75rem;
}

/* ── Input mode pills ── */
.stRadio > div {
    display: flex;
    gap: 0.5rem;
    flex-direction: row !important;
}
.stRadio > div > label {
    background: #13131A;
    border: 1px solid #2A2A35;
    border-radius: 4px;
    padding: 0.4rem 1rem;
    font-size: 0.82rem;
    cursor: pointer;
    transition: all 0.15s;
    color: #9A9690 !important;
}
.stRadio > div > label:has(input:checked) {
    background: #1A1A24;
    border-color: #C8F55A;
    color: #C8F55A !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0E0E16;
    border: 1px dashed #2A2A35;
    border-radius: 8px;
    padding: 1.5rem;
    transition: border-color 0.2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: #C8F55A40;
}

/* ── Text area ── */
.stTextArea > div > div > textarea {
    background: #0E0E16 !important;
    border: 1px solid #2A2A35 !important;
    border-radius: 8px;
    color: #E8E4DC !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem;
    line-height: 1.6;
    padding: 1rem;
    min-height: 220px;
}
.stTextArea > div > div > textarea:focus {
    border-color: #C8F55A60 !important;
    box-shadow: 0 0 0 1px #C8F55A30 !important;
}

/* ── Analyse button ── */
.stButton > button {
    background: #C8F55A;
    color: #0A0A0F;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border: none;
    border-radius: 4px;
    padding: 0.65rem 2.2rem;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
    width: auto;
}
.stButton > button:hover {
    background: #D8FF6A;
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: translateY(0);
}
.stButton > button:disabled {
    background: #2A2A35;
    color: #4A4A55;
    cursor: not-allowed;
    transform: none;
}

/* ── Spinner ── */
.stSpinner > div {
    border-color: #C8F55A transparent transparent transparent;
}

/* ── Report output ── */
.report-wrapper {
    background: #0E0E16;
    border: 1px solid #1E1E26;
    border-radius: 8px;
    padding: 2rem 2.5rem;
    margin-top: 1.5rem;
}

/* Section headers inside report */
.report-wrapper h2 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.3rem;
    color: #E8E4DC;
    margin: 1.8rem 0 0.6rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #1E1E26;
}
.report-wrapper h3 {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    font-weight: 500;
    color: #C8F55A;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 1.2rem 0 0.4rem;
}
.report-wrapper p, .report-wrapper li {
    font-size: 0.88rem;
    color: #B0ACA4;
    line-height: 1.75;
}
.report-wrapper strong {
    color: #E8E4DC;
    font-weight: 500;
}
.report-wrapper code {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    background: #13131A;
    padding: 0.1em 0.4em;
    border-radius: 3px;
    color: #C8F55A;
}
.report-wrapper blockquote {
    border-left: 2px solid #C8F55A40;
    margin: 0.8rem 0;
    padding: 0.4rem 1rem;
    color: #7A7870;
    font-style: italic;
}

/* Risk badges */
.risk-high   { color: #FF6B6B; font-weight: 600; }
.risk-medium { color: #FFB347; font-weight: 600; }
.risk-low    { color: #C8F55A; font-weight: 600; }

/* ── Meta bar ── */
.meta-bar {
    display: flex;
    gap: 2rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid #1E1E26;
    margin-bottom: 1.5rem;
}
.meta-item {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    color: #6B6860;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.meta-value {
    color: #9A9690;
    font-weight: 500;
}

/* ── Error / warning boxes ── */
.stAlert {
    background: #13131A;
    border-radius: 6px;
    border: 1px solid #2A2A35;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: transparent;
    color: #6B6860;
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border: 1px solid #2A2A35;
    border-radius: 4px;
    padding: 0.4rem 1.2rem;
    transition: all 0.15s;
}
.stDownloadButton > button:hover {
    border-color: #4A4A55;
    color: #E8E4DC;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0A0A0F; }
::-webkit-scrollbar-thumb { background: #2A2A35; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ── Brand header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <span class="brand-name">4eyes</span><span class="brand-dot">.</span><span class="brand-name">ai</span>
</div>
<div class="brand-tagline">Contract Intelligence Platform &nbsp;·&nbsp; Phase 4</div>
""", unsafe_allow_html=True)

st.markdown('<hr class="hairline">', unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using pdfplumber (preferred) or PyPDF2 fallback."""
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n\n".join(pages)
    except ImportError:
        pass
    try:
        import PyPDF2, io
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX using python-docx."""
    try:
        import docx, io
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise RuntimeError(
            "python-docx not installed. Run: pip install python-docx"
        )
    except Exception as e:
        raise RuntimeError(f"DOCX extraction failed: {e}")


def run_analysis(contract_text: str) -> str:
    """
    Import and run the contract_analyzer pipeline.

    contract_analyzer.py must expose one of:
      - analyze(text: str) -> str          (returns formatted report string)
      - analyze(text: str) -> dict         (returns structured dict)
      - ContractAnalyzer().analyze(text)   (class-based)

    Adjust the call below to match your actual API.
    """
    # Ensure the project root is on sys.path so contract_analyzer can be imported
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        import contract_analyzer  # noqa: PLC0415
    except ModuleNotFoundError:
        raise RuntimeError(
            "contract_analyzer.py not found. "
            "Make sure it lives in the same directory as app.py."
        )

    # ── Try the most common API shapes ────────────────────────────────────────
    if hasattr(contract_analyzer, "analyze"):
        result = contract_analyzer.analyze(contract_text)
    elif hasattr(contract_analyzer, "run"):
        result = contract_analyzer.run(contract_text)
    elif hasattr(contract_analyzer, "ContractAnalyzer"):
        analyzer = contract_analyzer.ContractAnalyzer()
        result = analyzer.analyze(contract_text)
    elif hasattr(contract_analyzer, "main"):
        # Some scripts write to stdout; capture it
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            contract_analyzer.main(contract_text)
        finally:
            sys.stdout = old_stdout
        result = buffer.getvalue()
    else:
        raise RuntimeError(
            "Could not find a recognised entry-point in contract_analyzer.py. "
            "Expected: analyze(), run(), ContractAnalyzer().analyze(), or main()."
        )

    # Normalise to string
    if isinstance(result, dict):
        import json
        return json.dumps(result, indent=2)
    return str(result)


# ── Input section ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Input Method</div>', unsafe_allow_html=True)

input_mode = st.radio(
    label="input_mode",
    options=["Upload file", "Paste text"],
    label_visibility="collapsed",
    horizontal=True,
)

contract_text: str | None = None
source_name: str = "unknown"

if input_mode == "Upload file":
    st.markdown('<div class="section-label" style="margin-top:1.2rem;">Contract Document</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        label="contract_upload",
        type=["pdf", "docx"],
        label_visibility="collapsed",
        help="PDF or DOCX, up to 50 MB",
    )

    if uploaded is not None:
        source_name = uploaded.name
        file_bytes = uploaded.read()
        ext = Path(uploaded.name).suffix.lower()
        with st.spinner("Extracting text…"):
            try:
                if ext == ".pdf":
                    contract_text = extract_text_from_pdf(file_bytes)
                elif ext == ".docx":
                    contract_text = extract_text_from_docx(file_bytes)
                else:
                    st.error(f"Unsupported file type: {ext}")
            except RuntimeError as err:
                st.error(str(err))

        if contract_text and contract_text.strip():
            st.markdown(
                f'<div class="section-label" style="margin-top:0.5rem;">'
                f'Extracted &nbsp;<span style="color:#6B9A6B">'
                f'{len(contract_text):,} chars</span> from '
                f'<span style="color:#9A9690">{source_name}</span></div>',
                unsafe_allow_html=True,
            )
        elif contract_text is not None:
            st.warning("The file appears to be empty or could not be read.")

else:  # Paste text
    st.markdown('<div class="section-label" style="margin-top:1.2rem;">Contract Text</div>', unsafe_allow_html=True)
    pasted = st.text_area(
        label="contract_text_input",
        label_visibility="collapsed",
        placeholder="Paste the full contract text here…",
        height=260,
    )
    if pasted.strip():
        contract_text = pasted
        source_name = "pasted-text"

# ── Analyse button ────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

col_btn, col_spacer = st.columns([1, 5])
with col_btn:
    analyse_clicked = st.button(
        "Analyse Contract",
        disabled=(not contract_text or not (contract_text or "").strip()),
        use_container_width=False,
    )

# ── Run pipeline & render report ──────────────────────────────────────────────
if analyse_clicked and contract_text and contract_text.strip():
    st.markdown('<hr class="hairline">', unsafe_allow_html=True)

    with st.spinner("Running 4eyes analysis pipeline…"):
        try:
            report_output = run_analysis(contract_text)
            analysis_ok = True
        except Exception as exc:
            analysis_ok = False
            error_msg = str(exc)

    if analysis_ok:
        import datetime
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Meta bar
        st.markdown(f"""
        <div class="meta-bar">
            <div class="meta-item">Source&nbsp;&nbsp;<span class="meta-value">{source_name}</span></div>
            <div class="meta-item">Length&nbsp;&nbsp;<span class="meta-value">{len(contract_text):,} chars</span></div>
            <div class="meta-item">Analysed&nbsp;&nbsp;<span class="meta-value">{ts}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # Report
        st.markdown('<div class="section-label">Analysis Report</div>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="report-wrapper">', unsafe_allow_html=True)

            # Render as markdown if it looks like markdown, otherwise as code
            if any(c in report_output for c in ["##", "**", "- ", "\n#"]):
                st.markdown(report_output)
            else:
                # Plain text or JSON: render in a scrollable mono block
                st.code(report_output, language="markdown")

            st.markdown("</div>", unsafe_allow_html=True)

        # Download
        st.markdown("<br>", unsafe_allow_html=True)
        col_dl, _ = st.columns([1, 4])
        with col_dl:
            st.download_button(
                label="↓  Download report",
                data=report_output,
                file_name=f"4eyes_report_{Path(source_name).stem}.txt",
                mime="text/plain",
            )

    else:
        st.error(f"**Analysis failed.** {error_msg}")
        st.markdown(
            '<div class="section-label" style="margin-top:1rem;">Traceback</div>',
            unsafe_allow_html=True,
        )
        st.code(error_msg, language="python")

elif analyse_clicked:
    st.warning("No contract text to analyse. Upload a file or paste text above.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<hr class="hairline" style="margin-top:4rem;">
<div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:#3A3A45; text-align:center; padding-bottom:1rem;">
    4eyes.ai &nbsp;·&nbsp; Contract Intelligence &nbsp;·&nbsp; Phase 4
</div>
""", unsafe_allow_html=True)

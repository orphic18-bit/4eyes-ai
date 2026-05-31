"""
4eyes.ai — AI-Powered Business Contract Reviewer
Phase 3 | Full Analysis Pipeline
Architecture: Trap Linter + Extraction Pass + Analysis Pass + Contradiction Validator
"""

import os
import sys
import csv
import re
from openai import OpenAI

# ────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────
MODEL_EXTRACTION      = "gpt-4o-mini"  # Cheap pass — extract clause effects
MODEL_ANALYSIS        = "gpt-4o"       # Strong pass — full risk analysis
TEMPERATURE           = 0.1
MIN_WORD_COUNT        = 80
MAX_TOKENS_EXTRACTION = 3000
MAX_TOKENS_ANALYSIS   = 6000
RED_FLAG_CSV_PATH     = "red_flag_patterns.csv"
SYSTEM_PROMPT_PATH    = "system_prompt.txt"


# ────────────────────────────────────────────────────────────
# 1  Load red-flag pattern library from CSV
# ────────────────────────────────────────────────────────────
def load_red_flag_patterns(path: str) -> list[dict]:
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader  = csv.DictReader(f)
            patterns = [row for row in reader]
        print(f"🔍 Pattern library: {len(patterns)} patterns loaded")
        return patterns
    except FileNotFoundError:
        print(f"⚠️  Warning: '{path}' not found. Continuing without pattern library.")
        return []
    except Exception as e:
        print(f"⚠️  Warning: Could not read '{path}': {e}")
        return []


# ────────────────────────────────────────────────────────────
# 2  Load system prompt from file
# ────────────────────────────────────────────────────────────
def load_system_prompt(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        print(f"📋 System prompt: loaded from {path}")
        return content
    except FileNotFoundError:
        print(f"\n❌  ERROR: {path} not found.")
        print(f"    Please ensure {path} is in the same folder as contract_analyzer.py")
        sys.exit(1)


# ────────────────────────────────────────────────────────────
# 3  Build full system prompt — inject CSV patterns
# ────────────────────────────────────────────────────────────
def build_system_prompt(base_prompt: str, patterns: list[dict]) -> str:
    if patterns:
        library_lines = []
        for row in patterns:
            pattern   = row.get("pattern",               "").strip()
            meaning   = row.get("plain_english_meaning", "").strip()
            severity  = row.get("severity",              "").strip()
            risk_type = row.get("risk_type",             "").strip()
            if pattern:
                library_lines.append(
                    f'• "{pattern}" → {meaning}\n'
                    f'  Severity: {severity} | Type: {risk_type}'
                )
        library_text = "\n".join(library_lines)
    else:
        library_text = "No pattern library loaded. Rely entirely on your own reasoning."

    return base_prompt.replace("[PATTERN LIBRARY INJECTED HERE BY SYSTEM]", library_text)


# ────────────────────────────────────────────────────────────
# 4  Deterministic trap linter — free regex pre-scan
# ────────────────────────────────────────────────────────────
def run_trap_linter(contract_text: str) -> list[dict]:
    """
    Fast, free pre-scan for known dangerous patterns using regex.
    Returns a list of alerts injected into the model context.
    Runs before any API call — zero cost.
    """
    alerts     = []
    text_lower = contract_text.lower()

    trap_definitions = [
        {
            "patterns": [
                r"confidential information includes[\s\S]{0,500}independently develop",
                r"confidential information includes[\s\S]{0,500}without the use of disclosing party",
                r"any information[\s\S]{0,300}receiving party[\s\S]{0,300}independently develop",
                r"independently develop[\s\S]{0,200}without the use of",
                r"information.{0,100}receiving party.{0,100}may.{0,50}develop.{0,100}without",
            ],
            "alert_type": "REVERSE_INDEPENDENT_DEVELOPMENT",
            "severity":   "DEALBREAKER",
            "message": (
                "Contract appears to INCLUDE independently developed work inside "
                "Confidential Information instead of EXCLUDING it. This is an active "
                "IP ownership grab disguised as a definition clause. "
                "MUST appear in RED FLAGS as [DEALBREAKER] with exact quote. "
                "Do NOT list as a missing protection — the hostile version is present."
            ),
        },
        {
            "patterns": [
                r"perpetually and indefinitely",
                r"shall survive.{0,100}indefinitely",
                r"in perpetuity",
                r"no expiration.{0,100}confidential",
                r"obligation.{0,100}perpetual",
            ],
            "alert_type": "PERPETUAL_OBLIGATION",
            "severity":   "CRITICAL",
            "message": (
                "Contract contains perpetual or indefinite obligation language. "
                "Flag in RED FLAGS as [CRITICAL]."
            ),
        },
        {
            "patterns": [
                r"global software market",
                r"worldwide.{0,100}non.{0,5}compet",
                r"non.{0,5}compet.{0,200}global",
                r"competes.{0,100}anywhere in the world",
                r"sixty.{0,10}month.{0,100}non.{0,5}compet",
                r"60.{0,10}month.{0,100}non.{0,5}compet",
            ],
            "alert_type": "EXCESSIVE_NON_COMPETE",
            "severity":   "DEALBREAKER",
            "message": (
                "Contract contains an excessive or global non-compete clause. "
                "Flag in RED FLAGS as [DEALBREAKER]."
            ),
        },
        {
            "patterns": [
                r"may modify.{0,100}at any time",
                r"may update.{0,100}at any time",
                r"may change.{0,100}without notice",
                r"reserves the right to modify",
                r"sole discretion.{0,100}modif",
            ],
            "alert_type": "UNILATERAL_MODIFICATION",
            "severity":   "CRITICAL",
            "message": (
                "Contract allows one party to modify terms unilaterally without consent. "
                "Flag in RED FLAGS as [CRITICAL]."
            ),
        },
        {
            "patterns": [
    r"indemnify.{0,200}any and all losses",
    r"indemnify.{0,200}all losses",
    r"indemnify.{0,200}without limitation",
    r"hold harmless.{0,200}any and all",
    r"indemnify.{0,200}attorneys.{0,50}fee",
    r"indemnify.{0,300}losses.{0,100}damages.{0,100}liabilities",
],
            "alert_type": "UNCAPPED_INDEMNIFICATION",
            "severity":   "CRITICAL",
            "message": (
                "Contract contains broad uncapped indemnification. "
                "Flag in RED FLAGS as [CRITICAL]."
            ),
        },
        {
            "patterns": [
                r"certified.{0,50}mail.{0,100}cancell",
                r"physical.{0,100}mail.{0,100}cancell",
                r"cancell.{0,100}certified mail",
                r"written notice.{0,100}certified",
            ],
            "alert_type": "PHYSICAL_MAIL_CANCELLATION",
            "severity":   "CRITICAL",
            "message": (
                "Contract requires physical certified mail for cancellation — a lock-in trap. "
                "Flag in RED FLAGS as [CRITICAL]."
            ),
        },
        {
            "patterns": [
                r"failure to object.{0,100}constitutes acceptance",
                r"failure to respond.{0,100}deemed acceptance",
                r"silence.{0,100}constitutes acceptance",
                r"no response.{0,100}acceptance",
            ],
            "alert_type": "SILENCE_EQUALS_ACCEPTANCE",
            "severity":   "CRITICAL",
            "message": (
                "Contract treats silence or failure to object as acceptance. "
                "Flag in RED FLAGS as [CRITICAL]."
            ),
        },
        {
            "patterns": [
                r"all right.{0,30}title.{0,30}interest.{0,200}regardless of payment",
                r"ownership.{0,200}vest.{0,100}upon creation",
                r"work made for hire",
                r"all inventions.{0,200}conceived during",
                r"all ideas.{0,200}conceived during the term",
            ],
            "alert_type": "WORK_PRODUCT_IP_GRAB",
            "severity":   "DEALBREAKER",
            "message": (
                "Contract transfers IP or work product ownership before or regardless "
                "of payment. Flag in RED FLAGS as [DEALBREAKER]."
            ),
        },
        {
            "patterns": [
                r"auto.{0,10}renew.{0,200}90.{0,20}day",
                r"auto.{0,10}renew.{0,200}sixty.{0,20}day",
                r"renew.{0,200}unless.{0,200}cancel.{0,200}90",
                r"successive.{0,100}term.{0,200}unless.{0,100}cancel",
            ],
            "alert_type": "AUTO_RENEWAL_TRAP",
            "severity":   "CRITICAL",
            "message": (
                "Contract auto-renews with a long cancellation notice window. "
                "Flag in RED FLAGS as [CRITICAL]."
            ),
        },
        {
           "patterns": [
    r"injunctive relief.{0,100}without.{0,50}bond",
    r"immediate injunction.{0,100}without bond",
    r"without.{0,50}bond.{0,100}injunctive",
    r"entitled to.{0,100}injunctive relief",
    r"injunctive relief.{0,100}without the necessity",
],
            "alert_type": "INJUNCTION_WITHOUT_BOND",
            "severity":   "CRITICAL",
            "message": (
                "Contract allows immediate injunctive relief without posting a bond. "
                "Flag in RED FLAGS as [CRITICAL]."
            ),
        },
    ]

    for trap in trap_definitions:
        for pattern in trap["patterns"]:
            match = re.search(pattern, text_lower)
            if match:
                start   = max(0, match.start() - 50)
                end     = min(len(contract_text), match.end() + 150)
                context = contract_text[start:end].strip()
                alerts.append({
                    "alert_type":      trap["alert_type"],
                    "severity":        trap["severity"],
                    "message":         trap["message"],
                    "matched_context": context,
                })
                break  # one alert per trap type

    if alerts:
        print(f"⚠️   Trap linter: {len(alerts)} potential trap(s) detected")
    else:
        print("✅  Trap linter: no known traps detected")

    return alerts


# ────────────────────────────────────────────────────────────
# 5  Extraction pass — translate clauses to plain-English effects
# ────────────────────────────────────────────────────────────
def run_extraction_pass(contract_text: str, client: OpenAI) -> str:
    """
    Pass 1 (cheap model): translate every clause into real-world effects.
    Strips legal section titles. Forces polarity detection.
    Output is passed to the analysis pass alongside the original contract.
    """
    extraction_system = """\
You are a contract clause translator. Your job is to translate every clause 
of a business contract into its real-world effects — not to analyze or judge, 
just to translate accurately.

For EVERY clause including definitions, recitals, and governing law sections:
1. State what the clause GIVES the other party
2. State what the clause TAKES from the signing party
3. State what the clause PREVENTS the signing party from doing
4. State the POLARITY: does this clause protect or burden the signing party?
5. Flag if this clause is doing the OPPOSITE of what its section title suggests

CRITICAL RULE FOR DEFINITION SECTIONS:
Definition sections are not administrative boilerplate. They are often where 
the most dangerous traps are hidden. Translate every definition into what it 
actually controls in practice.

A definition that expands what the other party owns, restricts, or controls 
is an active power grab. Flag it explicitly.

Example of a dangerous definition:
"Confidential Information includes any information that Receiving Party may 
independently develop" — this GIVES the other party control over the signing 
party's independent work. POLARITY: BURDENS signing party severely.
Title says "definition" but substance is an IP ownership grab.

Format each clause as:
CLAUSE: [Section number and title]
GIVES other party: [what]
TAKES from signing party: [what / or "nothing material"]
PREVENTS signing party from: [what / or "nothing material"]
POLARITY: [PROTECTS signing party / BURDENS signing party / NEUTRAL]
TITLE MATCHES SUBSTANCE: [YES / NO — explain if NO]

Do not skip any clause. Do not judge risk level. Just translate effects accurately."""

    try:
        response = client.chat.completions.create(
            model=MODEL_EXTRACTION,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS_EXTRACTION,
            messages=[
                {"role": "system", "content": extraction_system},
                {"role": "user",   "content": contract_text},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Extraction pass failed: {e}"


# ────────────────────────────────────────────────────────────
# 6  Format linter alerts for model injection
# ────────────────────────────────────────────────────────────
def format_linter_alerts(alerts: list[dict]) -> str:
    if not alerts:
        return "PRE-SCAN: No deterministic traps detected.\n"

    lines = [
        "═══════════════════════════════════════════",
        "SYSTEM PRE-SCAN ALERTS — MUST BE ADDRESSED",
        "═══════════════════════════════════════════",
        "The following dangerous patterns were detected by automated scan.",
        "EVERY alert below MUST appear in RED FLAGS unless you can explicitly",
        "show the clause is mitigated elsewhere in the contract.",
        "",
    ]
    for i, alert in enumerate(alerts, 1):
        lines.append(f"ALERT {i}: [{alert['severity']}] {alert['alert_type']}")
        lines.append(f"Instruction: {alert['message']}")
        lines.append(f"Detected text: ...{alert['matched_context']}...")
        lines.append("")

    return "\n".join(lines)


# ────────────────────────────────────────────────────────────
# 7  Analysis pass — full report generation
# ────────────────────────────────────────────────────────────
def run_analysis_pass(
    contract_text: str,
    extraction:    str,
    linter_alerts: str,
    system_prompt: str,
    client:        OpenAI,
) -> str:
    """
    Pass 2 (strong model): full risk analysis using:
    - Linter alerts (known traps detected)
    - Extraction output (plain-English clause effects)
    - Original contract text
    """
    user_message = f"""\
{linter_alerts}
────────────────────────────────────────────────────────
CLAUSE EFFECT TRANSLATION
The following is a plain-English translation of every clause's 
real-world effect produced by pre-processing. Use this alongside 
the original contract text to ensure no hidden trap is missed.
Pay special attention to any clause marked POLARITY: BURDENS or 
TITLE MATCHES SUBSTANCE: NO.

{extraction}

────────────────────────────────────────────────────────
ORIGINAL CONTRACT TEXT

{contract_text}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL_ANALYSIS,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS_ANALYSIS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"\n❌  API Error: {e}"


# ────────────────────────────────────────────────────────────
# 8  Contradiction validator
# ────────────────────────────────────────────────────────────
def validate_report(report: str, alerts: list[dict]) -> list[str]:
    """
    Checks the final report against linter alerts.
    Returns a list of validation failures for user awareness.
    Does not block output — warns the user if something was missed.
    """
    failures    = []
    report_lower = report.lower()

    for alert in alerts:
        atype = alert["alert_type"]

        if atype == "REVERSE_INDEPENDENT_DEVELOPMENT":
            in_red_flags = (
                "red flag"    in report_lower and
                "independent" in report_lower and
                "develop"     in report_lower
            )
            listed_as_missing_only = (
                "independent development carve-out" in report_lower and
                "dealbreaker"                       not in report_lower
            )
            if not in_red_flags or listed_as_missing_only:
                failures.append(
                    "VALIDATION WARNING: Reverse independent-development clause detected "
                    "but may not be flagged as [DEALBREAKER] in RED FLAGS. "
                    "Verify Section 1 is addressed as an active IP ownership grab."
                )

        elif atype == "EXCESSIVE_NON_COMPETE":
            if "dealbreaker" not in report_lower and "non-compet" in report_lower:
                failures.append(
                    "VALIDATION WARNING: Excessive non-compete detected but "
                    "may not be tagged [DEALBREAKER]."
                )

        elif atype == "PERPETUAL_OBLIGATION":
            if "perpetual" in report_lower and "red flag" not in report_lower:
                failures.append(
                    "VALIDATION WARNING: Perpetual obligation detected but "
                    "may be missing from RED FLAGS section."
                )

        elif atype == "UNCAPPED_INDEMNIFICATION":
            if "indemnif" in report_lower and "critical" not in report_lower:
                failures.append(
                    "VALIDATION WARNING: Uncapped indemnification detected but "
                    "may not be tagged [CRITICAL]."
                )

    return failures


# ────────────────────────────────────────────────────────────
# 9  Programmatic entry-point (called by app.py / Streamlit)
# ────────────────────────────────────────────────────────────
def analyze(contract_text: str) -> str:
    """
    Run the full 4eyes pipeline on pre-supplied text and return
    the report as a string.  Raises ValueError for bad input and
    RuntimeError for configuration/API problems.

    Intentionally does NOT call sys.exit() — exceptions propagate
    to the caller so the Streamlit UI can surface them cleanly.
    """
    # ── Validate input ───────────────────────────────────────
    ok, reason = looks_like_a_contract(contract_text)
    if not ok:
        raise ValueError(reason)

    # ── Load resources ───────────────────────────────────────
    patterns      = load_red_flag_patterns(RED_FLAG_CSV_PATH)
    base_prompt   = load_system_prompt_safe(SYSTEM_PROMPT_PATH)
    system_prompt = build_system_prompt(base_prompt, patterns)

    # ── API client ───────────────────────────────────────────
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Add it to your .env file or Streamlit secrets."
        )
    client = OpenAI(api_key=api_key)

    # ── Pipeline ─────────────────────────────────────────────
    alerts     = run_trap_linter(contract_text)
    extraction = run_extraction_pass(contract_text, client)
    linter_text = format_linter_alerts(alerts)
    report = run_analysis_pass(
        contract_text,
        extraction,
        linter_text,
        system_prompt,
        client,
    )

    # ── Validate & append any warnings ───────────────────────
    failures = validate_report(report, alerts)
    if failures:
        warning_block = (
            "\n\n---\n⚠️ **VALIDATION WARNINGS** — review carefully:\n"
            + "\n".join(f"• {f}" for f in failures)
        )
        report += warning_block

    return report


def load_system_prompt_safe(path: str) -> str:
    """
    Non-exiting variant of load_system_prompt used by analyze().
    Raises RuntimeError instead of calling sys.exit() so callers
    can handle the failure gracefully.
    """
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        raise RuntimeError(
            f"System prompt file '{path}' not found. "
            "Ensure it lives in the same directory as contract_analyzer.py."
        )


# ────────────────────────────────────────────────────────────
# 10  Input validator
# ────────────────────────────────────────────────────────────
def looks_like_a_contract(text: str):
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT:
        return False, (
            f"Input is too short ({word_count} words). "
            f"A contract typically has at least {MIN_WORD_COUNT} words."
        )
    signals = [
        "agreement", "party", "shall", "obligations", "terms",
        "conditions", "signature", "effective date", "clause",
        "section", "payment", "terminate", "confidential",
        "liability", "indemnif", "warranty", "govern",
    ]
    matched = sum(1 for s in signals if s in text.lower())
    if matched < 3:
        return False, (
            "This doesn't appear to be a business contract. "
            "Please paste an NDA, SOW, MSA, freelance agreement, "
            "or SaaS vendor agreement."
        )
    return True, "ok"


# ────────────────────────────────────────────────────────────
# 11  CLI input
# ────────────────────────────────────────────────────────────
def collect_contract_input() -> str:
    print("━" * 48)
    print("  4eyes.ai — Business Contract Reviewer")
    print("  Phase 3 | Powered by GPT-4o")
    print("━" * 48)
    print()
    print("Paste your contract text below.")
    print("When done, type  END  on a new line and press Enter.")
    print()
    print("─" * 48)
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines).strip()


# ────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────
def main():
    # ── Load resources ──────────────────────────────────────
    patterns      = load_red_flag_patterns(RED_FLAG_CSV_PATH)
    base_prompt   = load_system_prompt(SYSTEM_PROMPT_PATH)
    system_prompt = build_system_prompt(base_prompt, patterns)

    # ── Get contract ─────────────────────────────────────────
    contract_text = collect_contract_input()
    if not contract_text:
        print("\n⚠️  No input received.\n")
        sys.exit(0)

    ok, reason = looks_like_a_contract(contract_text)
    if not ok:
        print(f"\n⚠️  {reason}\n")
        sys.exit(0)

    # ── API client ───────────────────────────────────────────
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\n❌  ERROR: OPENAI_API_KEY not found.")
        print("    Set it with: $env:OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    client = OpenAI(api_key=api_key)

    # ── Pipeline ─────────────────────────────────────────────
    print("\n🔍  Step 1/3 — Running trap linter (free, instant)...")
    alerts = run_trap_linter(contract_text)

    print("⚙️   Step 2/3 — Running extraction pass (gpt-4o-mini)...")
    extraction = run_extraction_pass(contract_text, client)

    linter_text = format_linter_alerts(alerts)

    print("🧠  Step 3/3 — Running analysis pass (gpt-4o)...")
    report = run_analysis_pass(
        contract_text,
        extraction,
        linter_text,
        system_prompt,
        client,
    )

    # ── Validate ─────────────────────────────────────────────
    failures = validate_report(report, alerts)
    if failures:
        print("\n⚠️   VALIDATION WARNINGS — review report carefully:")
        for f in failures:
            print(f"     • {f}")

    print("\n" + report + "\n")


if __name__ == "__main__":
    main()

"""
4eyes.ai — AI-Powered Business Contract Reviewer
Phase 2 · RECEIVER perspective · 2026-05-23
"""

import os
import sys
import csv

from openai import OpenAI

# ────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────
MODEL              = "gpt-4o"
TEMPERATURE        = 0.1
MIN_WORD_COUNT     = 80
MAX_TOKENS         = 4000
RED_FLAG_CSV_PATH  = "red_flag_patterns.csv"

# ────────────────────────────────────────────────────────────
# 1️⃣  Load red-flag pattern library from CSV
# ────────────────────────────────────────────────────────────
def load_red_flag_patterns(path: str) -> list[dict]:
    """
    Reads red_flag_patterns.csv and returns a list of dicts.
    Expected columns: pattern, risk_type, severity,
                      plain_english_meaning, example_context
    If the file is not found, prints a warning and returns an
    empty list — the program continues without the library.
    """
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            patterns = [row for row in reader]
        print(f"🔍 Pattern library: {len(patterns)} patterns loaded")
        return patterns
    except FileNotFoundError:
        print(
            f"⚠️  Warning: '{path}' not found. "
            "Continuing without the pattern library."
        )
        return []
    except Exception as e:
        print(f"⚠️  Warning: Could not read '{path}': {e}. "
              "Continuing without the pattern library.")
        return []


# ────────────────────────────────────────────────────────────
# 2️⃣  Build the system prompt
#     (patterns injected after the reasoning protocol)
# ────────────────────────────────────────────────────────────
def build_system_prompt(patterns: list[dict]) -> str:
    """
    Assembles the full system prompt.
    The Supplementary Pattern Library section is generated
    dynamically from the loaded CSV rows and inserted after
    the Mandatory Reasoning Protocol.
    """

    # ── Base prompt (everything before the pattern library) ──
    base = """\
You are 4eyes.ai, acting as a strategic advocate for the SIGNING PARTY — \
the freelancer, contractor, or smaller party receiving this contract. \
Your sole job is to protect their interests. \
Favorable = good for the signing party. \
Unfavorable = bad for the signing party.

Analyze every clause through this lens without exception.

CRITICAL EXAMPLES FOR RECEIVER PERSPECTIVE:
- IP transferring to Client upon creation = RED FLAG for Receiver (loses work before payment)
- Unlimited revisions until Client satisfied = RED FLAG for Receiver (infinite unpaid work)
- Net-60 payment terms = UNFAVORABLE for Receiver (cash flow problem)
- Acceptance at Client sole discretion = RED FLAG for Receiver (payment can be withheld)
- A clause giving Receiver ownership until paid = FAVORABLE to Receiver (protects their leverage)

TONE RULES:
- Be calm, direct, and professional. Never sensational.
- Do NOT use alarmist all-caps language.
- If a clause is standard and acceptable, say so plainly.
- Over-flagging destroys trust.
- Flag genuine dangers clearly and firmly — but only genuine ones.
- Do not give specific legal advice.
- If a clause is genuinely ambiguous, say so and recommend consulting a qualified lawyer.

MANDATORY REASONING PROTOCOL:
Apply these four steps to EVERY clause before writing the report. \
Your own reasoning always takes priority over the pattern library.

Step 1 — WHO BENEFITS:
Does this clause give something to the other party or take something from me?
If it takes from me — flag it.

Step 2 — HIDDEN MEANING:
Does the plain reading hide a secondary effect?
Look especially at:
- Rights being removed inside definition sections
- Obligations that survive contract termination
- Scope that expands beyond what is stated
- Control given to the other party over decisions \
that affect my money, my work, or my freedom

Step 3 — DURATION AND SCOPE:
Does this clause have an end date or is it open-ended? \
As the signing party, shorter duration and narrower scope is always better.
Flag anything perpetual, indefinite, or without a hard cap.

Step 4 — PATTERN MATCH:
Scan the clause against the Supplementary Pattern Library below. \
If any pattern matches, flag with exact location. \
If you find something dangerous that is NOT in the library, flag it anyway.

These four steps are not optional. \
Complete all four for every clause before writing any section of the report."""

    # ── Supplementary Pattern Library section ──
    if patterns:
        library_lines = [
            "",
            "SUPPLEMENTARY PATTERN LIBRARY:",
            "The following patterns are known high-risk phrases found in real contracts. "
            "When you encounter any of these in the contract text, flag them with their "
            "exact section location.",
            "",
            "CRITICAL INSTRUCTION: This list is a supplement to your own reasoning — "
            "NOT a replacement. You must still apply the full reasoning protocol to every "
            "clause. If you find a dangerous clause that is NOT in this pattern library, "
            "flag it anyway. Your judgment takes priority. This library only adds "
            "sensitivity for known patterns on top of your existing analysis.",
            "",
        ]
        for row in patterns:
            pattern     = row.get("pattern", "").strip()
            meaning     = row.get("plain_english_meaning", "").strip()
            severity    = row.get("severity", "").strip()
            risk_type   = row.get("risk_type", "").strip()
            if pattern:
                library_lines.append(
                    f'- "{pattern}" → {meaning}\n'
                    f'  Severity: {severity} | Type: {risk_type}'
                )
        library_section = "\n".join(library_lines)
    else:
        library_section = (
            "\n\nSUPPLEMENTARY PATTERN LIBRARY:\n"
            "No pattern library loaded. Rely entirely on your own reasoning protocol."
        )

    # ── Output format + disclaimer (unchanged) ──
    output_format = """

BURIED CLAUSE DETECTION:
Actively hunt for clauses that secretly remove your rights, expand your liability, \
transfer your ownership, or create hidden obligations. Surface any such clauses as \
RED FLAGS with exact section locations.

OUTPUT FORMAT — use **exactly** this structure:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4eyes.ai — CONTRACT ANALYSIS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 CONTRACT TYPE
[NDA, SOW, MSA, Freelance Agreement, SaaS Vendor Agreement, etc.]

⚖️ CONTRACT TILT
This contract is [heavily / moderately / slightly] tilted toward [party], **or** balanced.

👥 KEY PARTIES & OBLIGATIONS
[Parties and what each must do.]

✅ FAVORABLE CLAUSES
[Clauses beneficial to the signing party.
If none, say "None identified."]

⚠️ UNFAVORABLE CLAUSES
*Definition* — clauses that disadvantage the signing party **but are within normal contract range.**
Worth negotiating; not deal-breakers.
**A clause listed here must NOT appear in RED FLAGS.**
If none, say "None identified."

🚨 RED FLAGS
*Definition* — clauses that are genuinely dangerous, highly unusual, or could cause real financial, legal, or operational damage.
Higher threshold than Unfavorable Clauses.
**A clause must NEVER appear in both sections.**
Include any Named Traps and Buried Clauses (with exact section location).
If none, say "No red flags identified."

❓ MISSING CLAUSES
[Important clauses expected in this contract type but absent.]

💬 NEGOTIATION SUGGESTIONS
[Specific, actionable push-back items.]

🏁 OVERALL VERDICT
[SIGN / NEGOTIATE / AVOID — plus 2-3 plain sentences explaining from the signing party's perspective.]

─────────────────────────────────────────
⚖️  DISCLAIMER
This analysis is generated by an AI tool and is for informational purposes only.
It does not constitute legal advice. For any contract with significant financial, legal, or business implications, please consult a qualified attorney.
─────────────────────────────────────────"""

    return base + library_section + output_format


# ────────────────────────────────────────────────────────────
# 3️⃣  Heuristic: looks_like_a_contract
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
        "liability", "indemnif", "warranty", "govern"
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
# 4️⃣  CLI helper
# ────────────────────────────────────────────────────────────
def collect_contract_input() -> str:
    print("━" * 48)
    print("  4eyes.ai — Business Contract Reviewer")
    print("  Phase 2 | Powered by GPT-4o-mini")
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
# 5️⃣  Core analysis function
# ────────────────────────────────────────────────────────────
def analyze_contract(contract_text: str, system_prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\n❌  ERROR: OPENAI_API_KEY not found.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    print("\n⏳  Analysing... this usually takes 10–20 seconds.\n")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": contract_text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"\n❌  API Error: {e}"


# ────────────────────────────────────────────────────────────
# 6️⃣  Entry-point
# ────────────────────────────────────────────────────────────
def main():
    # Load pattern library first (before the banner clears the screen)
    patterns      = load_red_flag_patterns(RED_FLAG_CSV_PATH)
    system_prompt = build_system_prompt(patterns)

    contract_text = collect_contract_input()
    if not contract_text:
        print("\n⚠️  No input received.\n")
        sys.exit(0)

    ok, reason = looks_like_a_contract(contract_text)
    if not ok:
        print(f"\n⚠️  {reason}\n")
        sys.exit(0)

    analysis = analyze_contract(contract_text, system_prompt)
    print("\n" + analysis + "\n")


# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()

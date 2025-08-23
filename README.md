# 🔑 Password Strength Analyzer & Custom Wordlist Generator (PSAWG)

A Python-based CLI tool to:
- **Analyze** password strength (entropy + ZXCVBN score & crack-time estimate).
- **Audit** a list of passwords and export results to CSV.
- **Generate** custom wordlists from user metadata (case variants, leetspeak, suffixes, separators, years).

---

## ⚙️ Setup
```bash
# Create virtual environment (Linux/Mac)
python3 -m venv .venv
source .venv/bin/activate

# or on Windows
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install zxcvbn tqdm

Usage
1. Analyze one password
python3 psawg.py analyze "Vaishnav@2004" --inputs vaishnav 2004 chaitanya cricket


➡️ Returns JSON with entropy, ZXCVBN score (0–4), crack-time estimate, and strength class.

2. Audit multiple passwords

Create a file samples/passwords.txt:

password
Password123
Vaishnav@2004
Cricket@2025
L3tM3!n
CorrectHorseBatteryStaple!


Run audit:

python3 psawg.py audit samples/passwords.txt --inputs vaishnav 2004 chaitanya --out reports/analysis.csv


➡️ Exports results into reports/analysis.csv.

3. Generate custom wordlist

From inline metadata:

python3 psawg.py wordlist --meta vaishnav 2004 chaitanya cricket hyderabad --max 30000 --out wordlist.txt


Or from a JSON file:

python3 psawg.py wordlist --meta-json samples/meta.json --max 30000 --out wordlist.txt


➡️ Creates a wordlist.txt with variants, suffixes, and combos.

📸 Screenshots
Password Analysis

Audit CSV

Wordlist Generation

Ethical Use

This tool is built for educational and defensive purposes only.
⚠️ Do not use it against systems you do not own or have explicit permission to test.

📄 Report

See: report.pdf
 (2-page internship project report).


---

#!/usr/bin/env python3
import argparse, re, itertools, json, sys, os
from datetime import datetime
from collections import OrderedDict

# Optional import: fall back gracefully if not installed
try:
    from zxcvbn import zxcvbn
    HAS_ZXCVBN = True
except Exception:
    HAS_ZXCVBN = False

# ---------- Utilities ----------
LEET_MAP = {
    "a":"4","e":"3","i":"1","o":"0","s":"5","t":"7","g":"9","b":"8"
}

COMMON_SUFFIXES = ["!", "@", "#", "123", "1234", "12345", "2024", "2025", "!", "!!", "!", "1", "01", "007"]
SEPARATORS = ["", "", "", "-", "_", ".", "@"]

def shannon_entropy(s: str) -> float:
    if not s: return 0.0
    from math import log2
    # Probability of each unique char
    probs = [s.count(c)/len(s) for c in set(s)]
    return -sum(p*log2(p) for p in probs)

def classify_length_entropy(password: str, entropy_bits: float) -> str:
    length = len(password)
    if length >= 14 and entropy_bits >= 3.0: return "Strong"
    if length >= 10 and entropy_bits >= 2.5: return "Medium"
    return "Weak"

def to_variants(word: str):
    w = word.strip()
    out = {w, w.lower(), w.upper(), w.title()}
    # Basic leetspeak
    leet = "".join(LEET_MAP.get(c.lower(), c) for c in w)
    out.add(leet)
    return out

def mix(a, b):
    for sep in SEPARATORS:
        yield f"{a}{sep}{b}"

def load_meta(meta_path: str|None, meta_inputs: list[str]):
    base = []
    if meta_path and os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k,v in data.items():
                if isinstance(v, list):
                    base.extend([str(x) for x in v])
                else:
                    base.append(str(v))
        except Exception as e:
            print(f"[warn] Failed to read {meta_path}: {e}", file=sys.stderr)

    for x in meta_inputs:
        if x: base.append(x)
    # Clean & unique
    seen = OrderedDict()
    for w in base:
        w = w.strip()
        if w:
            seen[w] = 1
    return list(seen.keys())

def year_candidates():
    y = datetime.now().year
    return [str(y-1), str(y), str(y+1), "1999", "2000", "2001", "2010"]

def cap_size(iterable, max_items):
    if max_items is None:
        for x in iterable: yield x
    else:
        count = 0
        for x in iterable:
            if count >= max_items: break
            yield x; count += 1

# ---------- Analyze ----------
def analyze_password(pw: str, user_inputs: list[str]):
    res = {
        "Password": pw,
        "Length": len(pw),
        "Entropy_Bits": round(shannon_entropy(pw), 3),
        "ZXCVBN_Score": None,
        "Crack_Time_Offline_Hashing_per/sec": None,
        "Feedback": [],
        "class": None
    }
    if HAS_ZXCVBN:
        zx = zxcvbn(pw, user_inputs=user_inputs or [])
        res["ZXCVBN_Score"] = zx.get("score")
        times = zx.get("crack_times_display", {})
        res["Crack_Time_Offline_Hashing_per/sec"] = times.get("offline_fast_hashing_1e10_per_second")
        fb = zx.get("feedback", {})
        for k in ("warning","suggestions"):
            v = fb.get(k)
            if isinstance(v, list):
                res["Feedback"].extend(v)
            elif isinstance(v, str) and v:
                res["Feedback"].append(v)
    res["class"] = classify_length_entropy(pw, res["Entropy_Bits"])
    return res

# ---------- Wordlist ----------
def generate_wordlist(meta_words: list[str], max_items: int|None, min_len: int, max_len: int):
    base = set()
    for w in meta_words:
        base |= to_variants(w)

    # single-word variants with suffixes & years
    singles = set()
    for w in base:
        if min_len <= len(w) <= max_len:
            singles.add(w)
        for suf in COMMON_SUFFIXES + year_candidates():
            cand = f"{w}{suf}"
            if min_len <= len(cand) <= max_len:
                singles.add(cand)

    # two-word mixes
    doubles = set()
    base_list = list(base)
    for a, b in itertools.permutations(base_list, 2):
        for comb in mix(a, b):
            if min_len <= len(comb) <= max_len:
                doubles.add(comb)
            # With suffixes
            for suf in COMMON_SUFFIXES:
                c2 = f"{comb}{suf}"
                if min_len <= len(c2) <= max_len:
                    doubles.add(c2)

    # Ensure deterministic order
    all_words = list(OrderedDict.fromkeys(list(singles) + list(doubles)))
    return cap_size(all_words, max_items)

# ---------- CLI ----------
def main():
    p = argparse.ArgumentParser(
        description="Password Strength Analyzer & Wordlist Generator (PSAWG)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # analyze command
    pa = sub.add_parser("analyze", help="Analyze a single password")
    pa.add_argument("password", help="Password to analyze")
    pa.add_argument("--inputs", nargs="*", default=[], help="User-related words (name, pet, phone, etc.)")

    # audit command (file in -> CSV out)
    pi = sub.add_parser("audit", help="Analyze many passwords from a file (one per line)")
    pi.add_argument("infile", help="Text file with one password per line")
    pi.add_argument("--inputs", nargs="*", default=[], help="User-related words")
    pi.add_argument("--out", default="reports/analysis.csv", help="CSV output path")

    # wordlist command
    pw = sub.add_parser("wordlist", help="Generate a custom wordlist")
    pw.add_argument("--meta", nargs="*", default=[], help="Words like name, company, pet, place, hobbies, etc.")
    pw.add_argument("--meta-json", default=None, help="Optional JSON containing fields to include")
    pw.add_argument("--min-len", type=int, default=6)
    pw.add_argument("--max-len", type=int, default=20)
    pw.add_argument("--max", type=int, default=50000, help="Max words to output")
    pw.add_argument("--out", default="wordlist.txt")

    args = p.parse_args()

    if args.cmd == "analyze":
        result = analyze_password(args.password, args.inputs)
        print(json.dumps(result, indent=2))
        if result["class"] != "Strong":
            print("\n[Advice]")
            print("- Use 14+ chars; mix words not related to you.")
            print("- Add randomness; avoid names/dates; prefer passphrases.")
            print("- Use a password manager & unique passwords per site.")

    elif args.cmd == "audit":
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        import csv
        with open(args.infile, "r", encoding="utf-8") as f, open(args.out, "w", newline="", encoding="utf-8") as o:
            w = csv.writer(o)
            w.writerow(["Password","Length","Entropy_Bits","ZXCVBN_Score","Crack_Time_Offline_Hashing_per/sec","class"])
            for line in f:
                pw = line.rstrip("\n")
                if not pw: continue
                res = analyze_password(pw, args.inputs)
                w.writerow([res["Password"], res["Length"], res["Entropy_Bits"], res["ZXCVBN_Score"], res["Crack_Time_Offline_Hashing_per/sec"], res["class"]])
        print(f"[+] Wrote {args.out}")

    elif args.cmd == "wordlist":
        words = load_meta(args.meta_json, args.meta)
        if not words:
            print("[!] No metadata provided. Add --meta items (e.g., --meta vaishnav 2004 chaitanya cricket)", file=sys.stderr)
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        from tqdm import tqdm
        count = 0
        with open(args.out, "w", encoding="utf-8") as f:
            for w in tqdm(generate_wordlist(words, args.max, args.min_len, args.max_len), desc="Generating"):
                f.write(w + "\n"); count += 1
        print(f"[+] Wrote {count} words to {args.out}")

if __name__ == "__main__":
    main()

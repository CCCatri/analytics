"""rules_level.py - the rules level, the rules sentence, built from measurement. Product.
No word or number in out/rules_level.csv is typed here: the template's words are read from acceptance-criteria/claim.md (the line starting 'the rules level'), and every label,
article, book and count is read from the three record reads' own files: out/clock_reasons.csv (clock), out/possessions_classes.csv (possessions), out/downs_reasons.csv (downs).
This file fixes only which part each source row belongs to (template, total, as rule, exception, unsettled, not judged, diagnostic) and which count a share
is taken of. Writes out/rules_level.csv stamped on line 1 with this file's sha, the sha of the template line's own text (not claim.md's file sha, which
moves with every plan edit) and each source's sha. verify() recomputes every cell from the sources and the template line, and checks the stamped
template-line sha against the line as it now reads; any difference prints and reads FAIL."""
import hashlib, io, os, re, sys
import pandas as pd

SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:12]
OUT = "out/rules_level.csv"
TEMPLATE_FILE, TEMPLATE_KEY = "acceptance-criteria/claim.md", "the rules level"
SRC = {"clock": "out/clock_reasons.csv", "possessions": "out/possessions_classes.csv", "downs": "out/downs_reasons.csv"}
FITS = "fits one of the rules the play-by-play record cannot tell apart"   # check_downs.py's FITS reason: the play-by-play record does not say which rule applied
NOT_APART = "not told apart"   # check_downs.py v17 4: a reason naming two readings the play-by-play record does not tell apart
COLS = ["clause", "part", "source", "season", "season_type", "check", "word", "label", "articles", "book", "count", "of", "share", "share_exact"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def read(p):
    L = open(p).read().split("\n")
    return L[0], pd.read_csv(io.StringIO("\n".join(L[1:])), keep_default_na=False)


def template_line():
    line = [l for l in open(TEMPLATE_FILE).read().split("\n") if l.startswith(TEMPLATE_KEY)]
    if len(line) != 1:
        raise SystemExit(f"STOPPED: {TEMPLATE_FILE} has {len(line)} lines starting '{TEMPLATE_KEY}'")
    return line[0]


def template_sha():
    return hashlib.sha256(template_line().encode()).hexdigest()[:12]


def template():
    return [c.strip().rstrip(".") for c in template_line()[len(TEMPLATE_KEY):].strip().split(";")]


def part_of(source, check, word, label):
    if source == "clock":
        if check == "GAME_LEVEL_PRIOR": return "diagnostic"
        if check == "CLASS": return {"RUN": "as rule", "INSUFFICIENT_EVIDENCE": "unsettled"}.get(word, "exception")
        if check == "TAG": return "exception"
        if check == "GAME_LEVEL": return {"WITHIN REAL TIME": "as rule", "WITHIN RESOLUTION": "as rule", "FASTER licensed (runoff)": "exception"}.get(word, "unsettled")
        if check == "D3": return {"WITHIN 40": "as rule", "N/A (ADMIN)": "exception"}.get(word, "unsettled")
    if source == "possessions":
        return {"possessions": "total", "back_to_back": "exception", "unexplained": "unsettled"}[check]
    if source == "downs":
        if word == "NOT JUDGED": return "not judged"
        if word == "AS RULE": return "as rule"
        if word == "EXPLAINED": return "unsettled" if (str(label).startswith(FITS) or NOT_APART in str(label)) else "exception"
        return "unsettled"
    raise SystemExit(f"STOPPED: no part for {source} {check} {word}")


def rows():
    """Every product row, each count read from its source; 'of' is the total of the same source, season, season type and check
    (back-to-back possessions are taken of that season's possessions)."""
    clauses = template(); out = []
    for i, c in enumerate(clauses):
        out.append(dict(clause=i + 1, part="template", source=TEMPLATE_FILE, label=c))
    for name, p in SRC.items():
        _, d = read(p)
        ci = {"clock": 1, "possessions": 2, "downs": 3}[name]
        if name == "possessions":
            d = d.rename(columns={"rule_class": "word"}).assign(label=lambda z: z["word"])
        else:
            d = d.rename(columns={"reason": "label", "why": "label"})
        if "season_type" not in d.columns: d["season_type"] = "ALL"
        if "articles" not in d.columns: d["articles"] = ""
        if "book" not in d.columns: d["book"] = ""
        g = d.groupby(["season", "season_type", "check", "word", "label", "articles", "book"], sort=True)["count"].sum().reset_index()
        tot = d.groupby(["season", "season_type", "check"])["count"].sum().to_dict()
        for _, r in g.iterrows():
            ofk = (r["season"], r["season_type"], "possessions" if (name == "possessions" and r["check"] != "possessions") else r["check"])
            of = int(tot.get(ofk, 0)); n = int(r["count"])
            out.append(dict(clause=ci, part=part_of(name, r["check"], r["word"], r["label"]), source=p, season=int(r["season"]), season_type=r["season_type"], check=r["check"],
                            word=r["word"], label=r["label"], articles=r["articles"], book=r["book"], count=n, of=of,
                            share=(f"{n / of:.6f}" if of else ""), share_exact=(f"{n}/{of}" if of else "")))
    return pd.DataFrame([{c: ("" if r.get(c) is None else r.get(c)) for c in COLS} for r in out], columns=COLS, dtype=object)


def write():
    R = rows()
    tag = (f"rules_level.py {SELF} | template '{TEMPLATE_KEY}' line {template_sha()} | " + " | ".join(f"{p} {sha(p)}" for p in SRC.values())
           + " | product: the rules level, the rules sentence, built from measurement")
    with open(OUT, "w") as f:
        f.write(f"# {tag}\n"); R.to_csv(f, index=False)
    return R, tag


def verify(path):
    """Every row of the product file against a fresh build from the sources, and the stamped template-line sha against the line as it now reads;
    returns the list of differences (empty = PASS)."""
    h, P = read(path)
    diff = []
    m = re.search(r"template '" + re.escape(TEMPLATE_KEY) + r"' line (\w+)", h)
    if not m or m.group(1) != template_sha():
        diff.append(f"line 1 stamps the template line {m.group(1) if m else 'NONE'}; the line now reads {template_sha()}")
    F = rows().astype(str).reset_index(drop=True); P = P.astype(str).reset_index(drop=True)
    if list(P.columns) != COLS: return diff + [f"columns {list(P.columns)}"]
    if len(P) != len(F): return diff + [f"rows {len(P)} in the file, {len(F)} from the sources"]
    for i in range(len(F)):
        for c in COLS:
            if P.at[i, c] != F.at[i, c]:
                diff.append(f"file line {i + 3} {c}: file '{P.at[i, c]}' vs sources '{F.at[i, c]}' ({F.at[i, 'source']} {F.at[i, 'season']} {F.at[i, 'check']} {F.at[i, 'word']})")
    return diff


if __name__ == "__main__":
    R, tag = write()
    d = verify(OUT)
    print(f"{tag}\nwritten {OUT} rows {len(R)} sha {sha(OUT)} | rows by part {R['part'].value_counts().to_dict()} | verify: {'PASS' if not d else 'FAIL'} {d[:5]}")
    sys.exit(0 if not d else 1)

"""Shared by the baseline and replay steps: the identity of what a run reads. Code revision (git HEAD and dirty paths), every kit .py file's sha, and for each
shared input directory the resolved target and, per file, its sha (link target and size for symlinks; size and mtime for files over 200 MB), plus product/RAW_PIN.json."""
import os, hashlib, subprocess, time
sha256 = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
def identity(root, kit):
    g = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True).stdout
    out = dict(git_head=g("rev-parse", "HEAD").strip(), git_dirty_paths=sorted(g("status", "--porcelain").splitlines()),
               code={f: sha256(os.path.join(kit, f)) for f in sorted(os.listdir(kit)) if f.endswith(".py")}, inputs={})
    for d in ("data", "facts", "prices", "sources"):
        p = os.path.join(kit, d)
        if not os.path.isdir(p): continue
        real = os.path.realpath(p); files = {}
        for n in sorted(os.listdir(real)):
            fp = os.path.join(real, n)
            if os.path.islink(fp): files[n] = dict(link=os.path.realpath(fp), size=os.path.getsize(fp))
            elif os.path.isfile(fp): files[n] = dict(sha256=sha256(fp)) if os.path.getsize(fp) < 200e6 else dict(size=os.path.getsize(fp), mtime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(fp))))
        out["inputs"][d] = dict(resolved=real, files=files)
    pin = os.path.join(root, "product", "RAW_PIN.json"); out["raw_pin_sha"] = sha256(pin) if os.path.exists(pin) else None
    return out
OUTPUTS = ("atlas_rows.csv.gz", "dk_rows.csv.gz", "atlas.csv", "ladder.csv", "product_judgment.csv", "replay_report.txt")
def copy_kit(kit, dest, say):
    """Code files and proj/ copied, every other directory symlinked; the replay outputs removed from the copy's proj/ so their later presence proves fresh emission."""
    import shutil
    os.makedirs(dest); copied, linked = [], []
    for entry in sorted(os.listdir(kit)):
        s, d = os.path.join(kit, entry), os.path.join(dest, entry)
        if entry == "__pycache__": continue
        if entry == "proj": shutil.copytree(s, d, symlinks=True); copied.append(entry + "/")
        elif os.path.isdir(s): os.symlink(s, d); linked.append(entry + "/")
        else: shutil.copy2(s, d); copied.append(entry)
    removed = [n for n in OUTPUTS if os.path.exists(os.path.join(dest, "proj", n))]
    for n in removed: os.remove(os.path.join(dest, "proj", n))
    say(f"  copied {copied}\n  symlinked {linked}\n  removed from the copy's proj/ before the run: {removed}")
    return removed

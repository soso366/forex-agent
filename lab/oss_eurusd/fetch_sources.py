"""Télécharge les projets testés au commit figé de sources.json (dossier ./sources)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main(dest: str = "sources") -> int:
    cfg = json.loads((HERE / "sources.json").read_text())
    dest = Path(dest)
    dest.mkdir(exist_ok=True)
    for p in cfg["projects"]:
        d = dest / p["id"]
        if not d.exists():
            subprocess.run(["git", "init", "-q", str(d)], check=True)
            subprocess.run(["git", "-C", str(d), "remote", "add", "origin", f"https://github.com/{p['repo']}"], check=True)
        subprocess.run(["git", "-C", str(d), "fetch", "-q", "--depth", "1", "origin", p["commit"]], check=True)
        subprocess.run(["git", "-C", str(d), "checkout", "-q", "FETCH_HEAD"], check=True)
        head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head != p["commit"]:
            print(f"ÉCHEC {p['repo']}: {head} != {p['commit']}")
            return 1
        missing = [f for f in p["files"] if not (d / f).exists()]
        if missing:
            print(f"ÉCHEC {p['repo']}: fichiers manquants {missing}")
            return 1
        print(f"OK {p['repo']} @ {head[:10]} — licence : {p['license']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))

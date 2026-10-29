# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: owner_tools/encrypt_online.py
# Version history of this file:
#   2.3.0 - Created: encrypt / decrypt the text files of the online GitHub folder (owner tool, not shipped to users)
# =============================================================================
"""Usage (Windows or Linux, Python 3.10+):

    python encrypt_online.py encrypt TubeArchivePro-2026-10.txt total_users.txt     -> writes <name>.enc next to each file
    python encrypt_online.py decrypt TubeArchivePro-2026-10.txt                     -> writes <name>.dec (to edit it again)

Upload the .enc file to the online folder UNDER THE ORIGINAL NAME (remove '.enc'): the program reads encrypted and plain files.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import secure                                              # noqa: E402


def main(argv):
    if len(argv) < 3 or argv[1] not in ("encrypt", "decrypt"):
        print(__doc__)
        return 1
    for name in argv[2:]:
        p = Path(name)
        data = p.read_bytes()
        if argv[1] == "encrypt":
            out = p.with_name(p.name + ".enc")
            out.write_bytes(secure.encrypt(data))
        else:
            plain = secure.decrypt_if_needed(data)
            if plain is None:
                print(name, ": damaged file")
                continue
            out = p.with_name(p.name + ".dec")
            out.write_bytes(plain)
        print(name, "->", out.name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

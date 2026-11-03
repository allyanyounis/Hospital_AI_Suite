"""Command line for the backend (run from backend/):

python -m app migrate                                   apply database migrations (the API also does this on start)
python -m app users add drrahman --name "Dr. Rahman" [--role admin]
python -m app users reset-password drrahman | disable drrahman | enable drrahman | list
python -m app seed demo-theatre                         load the synthetic theatre hospital (surgeons, patients with
                                                        labs, vitals and reports, theatre lists); safe to run twice
"""

import sys


def main() -> None:
    command, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if command == "migrate":
        from app.core.database import init_db

        init_db()
        print("Database is at the latest migration")
    elif command == "users":
        from app.modules.auth import cli

        cli.main(args)
    elif command == "seed" and args == ["demo-theatre"]:
        from app.core.clock import now_local
        from app.core.database import init_db, session_scope
        from app.modules.theatre import seed_demo

        init_db()
        with session_scope() as db:
            counts = seed_demo(db, now_local().date())
        print("The demo theatre hospital is already loaded" if counts is None else f"Loaded the demo: {counts}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

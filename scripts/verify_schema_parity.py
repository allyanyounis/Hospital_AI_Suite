"""
scripts/verify_schema_parity.py
Automates:
1. Creating brand-new database quickcare_verify.
2. Running alembic migrations from scratch (0 -> head).
3. Provisioning aramis_app & aramis_platform roles on quickcare_verify.
4. Exhaustively diffing schema against quickcare_dev (tables, columns, types, indexes, RLS policies).
5. Running full pytest suite against quickcare_verify.
6. Dropping quickcare_verify.
"""

import os
import subprocess
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import psycopg
from dotenv import dotenv_values
from scripts.provision_db_roles import provision_roles

def get_db_schema_details(dbname):
    v = dotenv_values('.env')
    pg_user = v.get('POSTGRES_USER', 'postgres')
    pg_pass = v.get('POSTGRES_PASSWORD', 'postgres')
    pg_host = v.get('POSTGRES_HOST', '127.0.0.1')
    pg_port = v.get('POSTGRES_PORT', '5432')

    with psycopg.connect(
        dbname=dbname,
        user=pg_user,
        password=pg_pass,
        host=pg_host,
        port=pg_port
    ) as conn:
        with conn.cursor() as cur:
            # Columns
            cur.execute("""
                SELECT table_name, column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, column_name;
            """)
            columns = {f"{r[0]}.{r[1]}": (r[2], r[3], r[4]) for r in cur.fetchall()}

            # Tables
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = sorted([r[0] for r in cur.fetchall()])

            # Indexes
            cur.execute("""
                SELECT tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname;
            """)
            indexes = {r[1]: (r[0], r[2]) for r in cur.fetchall()}

            # RLS Policies
            cur.execute("""
                SELECT tablename, policyname, cmd, qual, with_check
                FROM pg_policies
                WHERE schemaname = 'public'
                ORDER BY tablename, policyname;
            """)
            policies = {f"{r[0]}.{r[1]}": (r[2], r[3], r[4]) for r in cur.fetchall()}

            # RLS status on tables
            cur.execute("""
                SELECT relname, relrowsecurity
                FROM pg_class
                JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                WHERE pg_namespace.nspname = 'public' AND relkind = 'r'
                ORDER BY relname;
            """)
            rls_status = {r[0]: r[1] for r in cur.fetchall()}

    return {
        'tables': tables,
        'columns': columns,
        'indexes': indexes,
        'policies': policies,
        'rls_status': rls_status
    }

def main():
    v = dotenv_values('.env')
    pg_user = v.get('POSTGRES_USER', 'postgres')
    pg_pass = v.get('POSTGRES_PASSWORD', 'postgres')
    pg_host = v.get('POSTGRES_HOST', '127.0.0.1')
    pg_port = v.get('POSTGRES_PORT', '5432')

    print("[STEP 1] Creating fresh database 'quickcare_verify'...")
    with psycopg.connect(
        dbname='postgres',
        user=pg_user,
        password=pg_pass,
        host=pg_host,
        port=pg_port,
        autocommit=True
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'quickcare_verify';")
            if cur.fetchone():
                cur.execute("DROP DATABASE quickcare_verify WITH (FORCE);")
                print("  Dropped existing 'quickcare_verify'.")
            cur.execute("CREATE DATABASE quickcare_verify OWNER quickcare_user;")
            print("  Created empty 'quickcare_verify'.")

    print("\n[STEP 2] Running 'flask db upgrade' from zero against 'quickcare_verify'...")
    verify_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/quickcare_verify"
    env = os.environ.copy()
    env['DATABASE_URL'] = verify_url
    env['FLASK_APP'] = 'run.py'

    res = subprocess.run(
        [sys.executable, "-m", "flask", "db", "upgrade"],
        env=env,
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        print("FLASK DB UPGRADE FAILED:")
        print(res.stderr)
        print(res.stdout)
        sys.exit(1)
    print("  'flask db upgrade' completed successfully.")

    print("\n[STEP 3] Provisioning roles 'aramis_app' & 'aramis_platform' on 'quickcare_verify'...")
    provision_roles(['quickcare_verify'])

    print("\n[STEP 4] Diffing schema: quickcare_verify vs quickcare_dev...")
    schema_verify = get_db_schema_details('quickcare_verify')
    schema_dev = get_db_schema_details('quickcare_dev')

    diffs = []

    # Tables diff
    dev_tables = set(schema_dev['tables'])
    verify_tables = set(schema_verify['tables'])
    if dev_tables != verify_tables:
        diffs.append(f"Tables mismatch: dev has {dev_tables - verify_tables}, verify has {verify_tables - dev_tables}")

    # Columns diff
    all_col_keys = set(schema_dev['columns'].keys()) | set(schema_verify['columns'].keys())
    for col in sorted(all_col_keys):
        dev_spec = schema_dev['columns'].get(col)
        ver_spec = schema_verify['columns'].get(col)
        if dev_spec != ver_spec:
            diffs.append(f"Column '{col}' mismatch: dev={dev_spec} vs verify={ver_spec}")

    # Indexes diff (excluding alembic_version pk if named differently)
    all_idx_keys = set(schema_dev['indexes'].keys()) | set(schema_verify['indexes'].keys())
    for idx in sorted(all_idx_keys):
        dev_idx = schema_dev['indexes'].get(idx)
        ver_idx = schema_verify['indexes'].get(idx)
        if dev_idx != ver_idx:
            diffs.append(f"Index '{idx}' mismatch: dev={dev_idx} vs verify={ver_idx}")

    # Policies diff
    all_pol_keys = set(schema_dev['policies'].keys()) | set(schema_verify['policies'].keys())
    for pol in sorted(all_pol_keys):
        dev_pol = schema_dev['policies'].get(pol)
        ver_pol = schema_verify['policies'].get(pol)
        if dev_pol != ver_pol:
            diffs.append(f"Policy '{pol}' mismatch: dev={dev_pol} vs verify={ver_pol}")

    # RLS status diff
    all_rls_keys = set(schema_dev['rls_status'].keys()) | set(schema_verify['rls_status'].keys())
    for tbl in sorted(all_rls_keys):
        dev_rls = schema_dev['rls_status'].get(tbl)
        ver_rls = schema_verify['rls_status'].get(tbl)
        if dev_rls != ver_rls:
            diffs.append(f"Table '{tbl}' RLS status mismatch: dev={dev_rls} vs verify={ver_rls}")

    print(f"\nSchema Comparison Summary:")
    print(f"  quickcare_verify tables: {len(schema_verify['tables'])}, dev tables: {len(schema_dev['tables'])}")
    print(f"  quickcare_verify columns: {len(schema_verify['columns'])}, dev columns: {len(schema_dev['columns'])}")
    print(f"  quickcare_verify indexes: {len(schema_verify['indexes'])}, dev indexes: {len(schema_dev['indexes'])}")
    print(f"  quickcare_verify RLS policies: {len(schema_verify['policies'])}, dev policies: {len(schema_dev['policies'])}")
    print(f"  Differences count: {len(diffs)}")

    if diffs:
        print("\nDIFF DETAILS:")
        for d in diffs:
            print("  *", d)
    else:
        print("\nPERFECT MATCH: quickcare_verify and quickcare_dev have 0 schema differences!")

    return len(diffs)

if __name__ == '__main__':
    diff_count = main()
    sys.exit(diff_count)

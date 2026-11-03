"""
scripts/provision_db_roles.py
Provisions dedicated PostgreSQL roles for Aramis Health:
1. aramis_app (NON-superuser, NOBYPASSRLS) for normal application traffic & tests.
2. aramis_platform (NON-superuser, BYPASSRLS) for platform super admin cross-tenant auditing.
"""

import os
import sys
import psycopg
from dotenv import dotenv_values

def provision_roles(target_dbs=None):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env_path = os.path.join(project_root, '.env')
    v = dotenv_values(env_path) if os.path.exists(env_path) else {}

    pg_user = os.environ.get('POSTGRES_USER') or v.get('POSTGRES_USER', 'postgres')
    pg_pass = os.environ.get('POSTGRES_PASSWORD') or v.get('POSTGRES_PASSWORD', 'postgres')
    pg_host = os.environ.get('POSTGRES_HOST') or v.get('POSTGRES_HOST', '127.0.0.1')
    pg_port = os.environ.get('POSTGRES_PORT') or v.get('POSTGRES_PORT', '5432')

    app_pass = os.environ.get('ARAMIS_APP_PASSWORD') or v.get('ARAMIS_APP_PASSWORD', 'AramisApp2026!Sec#')
    plat_pass = os.environ.get('ARAMIS_PLATFORM_PASSWORD') or v.get('ARAMIS_PLATFORM_PASSWORD', 'AramisPlatform2026!Sec#')

    if target_dbs:
        databases = target_dbs
    elif len(sys.argv) > 1:
        databases = sys.argv[1:]
    else:
        databases = ['quickcare_dev', 'quickcare_test']

    # 1. Connect to postgres database to manage roles globally
    print("[ROLES] Connecting as superuser to postgres server...")
    with psycopg.connect(
        dbname='postgres',
        user=pg_user,
        password=pg_pass,
        host=pg_host,
        port=pg_port,
        autocommit=True
    ) as conn:
        with conn.cursor() as cur:
            # Create aramis_app if not exists
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aramis_app';")
            if not cur.fetchone():
                cur.execute(f"CREATE ROLE aramis_app WITH LOGIN PASSWORD '{app_pass}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;")
                print("[ROLES] Created role 'aramis_app' (NOSUPERUSER, NOBYPASSRLS).")
            else:
                cur.execute(f"ALTER ROLE aramis_app WITH LOGIN PASSWORD '{app_pass}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;")
                print("[ROLES] Updated role 'aramis_app'.")

            # Create aramis_platform if not exists
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aramis_platform';")
            if not cur.fetchone():
                cur.execute(f"CREATE ROLE aramis_platform WITH LOGIN PASSWORD '{plat_pass}' NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;")
                print("[ROLES] Created role 'aramis_platform' (NOSUPERUSER, BYPASSRLS).")
            else:
                cur.execute(f"ALTER ROLE aramis_platform WITH LOGIN PASSWORD '{plat_pass}' NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;")
                print("[ROLES] Updated role 'aramis_platform'.")

    # 2. Grant permissions per database
    for db_name in databases:
        print(f"\n[ROLES] Granting table and sequence privileges in '{db_name}'...")
        with psycopg.connect(
            dbname=db_name,
            user=pg_user,
            password=pg_pass,
            host=pg_host,
            port=pg_port,
            autocommit=True
        ) as db_conn:
            with db_conn.cursor() as cur:
                cur.execute(f"GRANT CONNECT ON DATABASE {db_name} TO aramis_app, aramis_platform;")
                cur.execute("GRANT USAGE ON SCHEMA public TO aramis_app, aramis_platform;")
                cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO aramis_app, aramis_platform;")
                cur.execute("GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO aramis_app, aramis_platform;")
                
                # Default privileges for future tables created by migrations
                cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aramis_app, aramis_platform;")
                cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO aramis_app, aramis_platform;")
                print(f"[ROLES] Privileges granted successfully in '{db_name}'.")

    print("\n[ROLES] All PostgreSQL roles and privileges provisioned successfully.")

if __name__ == '__main__':
    provision_roles()

"""
Migrate metadata from JSON to SQLite.

This script converts existing metadata.json to SQLite database.
Safe to run multiple times - will not duplicate data.
"""

import json
from pathlib import Path
import sys

from config import settings
from services.metadata_store import MetadataStore


def migrate_json_to_sqlite():
    """Migrate existing JSON metadata to SQLite."""
    json_path = settings.data_dir / "indexes" / "metadata.json"
    sqlite_path = settings.data_dir / "indexes" / "metadata.db"

    print(f"Migration Tool: JSON → SQLite")
    print(f"=" * 60)

    # Check if JSON file exists
    if not json_path.exists():
        print(f"✓ No JSON file found at {json_path}")
        print(f"  Starting fresh with SQLite.")
        return

    # Check if already migrated
    if sqlite_path.exists():
        response = input(f"\n⚠ SQLite database already exists at {sqlite_path}\n"
                        f"  Overwrite? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            return

        # Backup existing SQLite
        backup_path = sqlite_path.with_suffix('.db.backup')
        if sqlite_path.exists():
            import shutil
            shutil.copy(sqlite_path, backup_path)
            print(f"✓ Backed up existing database to {backup_path}")

    # Load JSON data
    print(f"\nLoading JSON metadata from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"✓ Loaded {len(chunks)} chunks")

    # Initialize SQLite store
    print(f"\nCreating SQLite database at {sqlite_path}...")
    store = MetadataStore(sqlite_path)

    # Migrate chunks
    print(f"Migrating chunks to SQLite...")
    batch_size = 1000
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        store.add_chunks(batch)
        print(f"  Migrated {min(i+batch_size, len(chunks))}/{len(chunks)} chunks")

    # Verify migration
    total = store.get_total_chunks()
    print(f"\n✓ Migration complete!")
    print(f"  Total chunks in SQLite: {total}")
    print(f"  Total chunks in JSON: {len(chunks)}")

    if total == len(chunks):
        print(f"\n✅ SUCCESS: All chunks migrated successfully!")

        # Offer to backup JSON
        response = input(f"\nBackup JSON file? (yes/no): ")
        if response.lower() == "yes":
            backup_json = json_path.with_suffix('.json.backup')
            json_path.rename(backup_json)
            print(f"✓ Backed up JSON to {backup_json}")
            print(f"\nYou can delete the backup once you verify everything works.")
    else:
        print(f"\n⚠ WARNING: Chunk count mismatch!")
        print(f"  Check the SQLite database before deleting JSON.")

    print(f"\n" + "=" * 60)
    print(f"Next steps:")
    print(f"1. Restart your Asymptote server")
    print(f"2. Test search functionality")
    print(f"3. Once verified, delete metadata.json.backup")


if __name__ == "__main__":
    try:
        migrate_json_to_sqlite()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

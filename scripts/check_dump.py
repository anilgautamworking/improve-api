#!/usr/bin/env python3
"""Check the Alembic version and structure of a database dump"""

import gzip
import re
import sys

def check_dump(dump_file):
    with gzip.open(dump_file, 'rt') as f:
        content = f.read()
    
    # Find INSERT INTO alembic_version
    pattern = r'INSERT INTO.*?"alembic_version".*?VALUES\s*\([\'"]([^\'"]+)[\'"]'
    match = re.search(pattern, content, re.IGNORECASE)
    
    if match:
        version = match.group(1)
        print(f"Alembic version in dump: {version}")
    else:
        # Try to find it in a different format
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'alembic_version' in line.lower() and ('INSERT' in line.upper() or 'VALUES' in line.upper()):
                # Check this line and next few
                for j in range(max(0, i-2), min(i+5, len(lines))):
                    if re.search(r'002|003|001', lines[j]):
                        print(f"Possible version found near line {i}: {lines[j].strip()[:100]}")
                        break
                break
        else:
            print("Could not determine Alembic version from dump")
            print("Assuming it's from before migration 003 (no exam tables)")
    
    # Check what tables are in the dump
    tables = set(re.findall(r'CREATE TABLE.*?"([^"]+)"', content, re.IGNORECASE))
    print(f"\nTables found in dump: {len(tables)}")
    for table in sorted(tables):
        print(f"  - {table}")
    
    # Check if categories table structure
    categories_match = re.search(r'CREATE TABLE.*?"categories".*?\((.*?)\);', content, re.DOTALL | re.IGNORECASE)
    if categories_match:
        structure = categories_match.group(1)
        if 'uuid' in structure.lower() or 'gen_random_uuid' in structure.lower():
            print("\n✓ Categories table uses UUID (new structure)")
        else:
            print("\n⚠ Categories table uses old structure (will conflict with migration 003)")

if __name__ == '__main__':
    dump_file = sys.argv[1] if len(sys.argv) > 1 else 'improve-full.gz'
    check_dump(dump_file)


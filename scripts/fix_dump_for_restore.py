#!/usr/bin/env python3
"""Fix dump file by adding CASCADE to DROP TABLE statements"""

import gzip
import re
import sys
import os

def fix_dump(input_file, output_file=None):
    """Add CASCADE to all DROP TABLE statements in the dump"""
    
    if output_file is None:
        # Create output filename
        base_name = os.path.splitext(input_file)[0]
        if input_file.endswith('.gz'):
            base_name = os.path.splitext(base_name)[0]
        output_file = f"{base_name}_fixed.sql.gz"
    
    print(f"Reading dump file: {input_file}")
    
    # Read the dump
    if input_file.endswith('.gz'):
        with gzip.open(input_file, 'rt') as f_in:
            content = f_in.read()
    else:
        with open(input_file, 'r') as f_in:
            content = f_in.read()
    
    # Fix DROP TABLE statements - add CASCADE if not present
    # Pattern: DROP TABLE IF EXISTS "table_name"; or DROP TABLE "table_name";
    pattern = r'(DROP TABLE IF EXISTS\s+[^;]+);'
    replacement = r'\1 CASCADE;'
    fixed_content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    # Also handle DROP TABLE without IF EXISTS
    pattern2 = r'(DROP TABLE\s+[^;]+)(?<!CASCADE);'
    fixed_content = re.sub(pattern2, r'\1 CASCADE;', fixed_content, flags=re.IGNORECASE)
    
    # Count changes
    original_drops = len(re.findall(r'DROP TABLE', content, re.IGNORECASE))
    fixed_drops = len(re.findall(r'DROP TABLE.*CASCADE', fixed_content, re.IGNORECASE))
    
    print(f"Found {original_drops} DROP TABLE statements")
    print(f"Fixed {fixed_drops} statements with CASCADE")
    
    # Write fixed dump
    print(f"Writing fixed dump to: {output_file}")
    if output_file.endswith('.gz'):
        with gzip.open(output_file, 'wt') as f_out:
            f_out.write(fixed_content)
    else:
        with open(output_file, 'w') as f_out:
            f_out.write(fixed_content)
    
    print(f"✓ Fixed dump saved to: {output_file}")
    return output_file

if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'improve-full.gz'
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    fix_dump(input_file, output_file)


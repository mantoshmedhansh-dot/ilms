"""
Final migration script for response schemas.

Handles:
1. class XxxResponse(BaseModel): with from_attributes
2. class XxxResponse(XxxBase): with from_attributes
3. class XxxDropdown(BaseModel): with from_attributes
4. Any class with from_attributes that should use BaseResponseSchema
"""

import os
import re
from pathlib import Path


def process_file(filepath: str) -> tuple[int, list[str]]:
    """Process a single file."""
    with open(filepath, 'r') as f:
        content = f.read()
        original = content

    changes = []
    migrations = 0

    # Skip base.py and __init__.py
    if filepath.endswith('base.py') or filepath.endswith('__init__.py'):
        return 0, []

    # Don't have from_attributes at all? Skip
    if 'from_attributes' not in content:
        return 0, []

    # Check if BaseResponseSchema import exists
    has_import = 'from app.schemas.base import BaseResponseSchema' in content

    # Find all class definitions
    # Pattern: class ClassName(ParentClass): followed by body until next class or divider
    class_defs = list(re.finditer(
        r'^class\s+(\w+)\((\w+)\):\s*\n',
        content,
        re.MULTILINE
    ))

    classes_to_migrate = []

    for i, match in enumerate(class_defs):
        class_name = match.group(1)
        parent_class = match.group(2)
        class_start = match.start()

        # Find end of this class (start of next class or end of file)
        if i + 1 < len(class_defs):
            class_end = class_defs[i + 1].start()
        else:
            class_end = len(content)

        class_body = content[class_start:class_end]

        # Check if this class has from_attributes
        if 'from_attributes' in class_body:
            # Check if already uses BaseResponseSchema
            if parent_class == 'BaseResponseSchema':
                continue  # Already migrated

            classes_to_migrate.append({
                'name': class_name,
                'parent': parent_class,
                'start': class_start,
                'end': class_end,
                'body': class_body
            })

    if not classes_to_migrate:
        return 0, []

    # Add import if needed
    if not has_import:
        if 'from pydantic import' in content:
            content = re.sub(
                r'(from pydantic import[^\n]+\n)',
                r'\1from app.schemas.base import BaseResponseSchema\n',
                content,
                count=1
            )
            changes.append("Added BaseResponseSchema import")
        elif 'from datetime import' in content:
            content = re.sub(
                r'(from datetime import[^\n]+\n)',
                r'\1from app.schemas.base import BaseResponseSchema\n',
                content,
                count=1
            )
            changes.append("Added BaseResponseSchema import")
        else:
            content = 'from app.schemas.base import BaseResponseSchema\n' + content
            changes.append("Added BaseResponseSchema import at top")

    # Process each class (in reverse order to maintain positions)
    for cls in reversed(classes_to_migrate):
        class_name = cls['name']
        parent_class = cls['parent']
        class_body = cls['body']

        # Change parent class to BaseResponseSchema
        old_def = f'class {class_name}({parent_class}):'
        new_def = f'class {class_name}(BaseResponseSchema):'

        new_body = class_body.replace(old_def, new_def)

        # Remove model_config line
        new_body = re.sub(
            r'\n\s+model_config\s*=\s*ConfigDict\([^)]*\)\s*\n',
            '\n',
            new_body
        )

        # Remove old-style Config class
        new_body = re.sub(
            r'\n\s+class Config:\s*\n'
            r'(?:\s+[^\n]+\n)*?'
            r'(?=\n\s+\w|\n\nclass|\Z)',
            '\n',
            new_body
        )

        # Only update if there's a change
        if new_body != class_body:
            content = content[:cls['start']] + new_body + content[cls['end']:]
            migrations += 1
            changes.append(f"Migrated {class_name}({parent_class}) -> {class_name}(BaseResponseSchema)")

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)

    return migrations, changes


def main():
    """Run migration on all schema files."""
    schemas_dir = Path("/Users/mantosh/Desktop/Consumer durable 2/app/schemas")

    print("=" * 60)
    print("Final Schema Migration to BaseResponseSchema")
    print("=" * 60)
    print()

    total_migrations = 0
    modified_files = []
    all_changes = []

    for filepath in sorted(schemas_dir.glob("*.py")):
        count, changes = process_file(str(filepath))

        if count > 0:
            print(f"Processing: {filepath.name} ({count} migrations)")
            for change in changes:
                print(f"  - {change}")
            print()
            modified_files.append((filepath.name, count))
            all_changes.extend(changes)
            total_migrations += count

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total migrations: {total_migrations}")
    print(f"Modified files: {len(modified_files)}")
    print()

    if modified_files:
        print("Modified files:")
        for fname, count in modified_files:
            print(f"  - {fname}: {count} migrations")


if __name__ == "__main__":
    main()

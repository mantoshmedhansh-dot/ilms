"""
Migration script v2 to convert all response schemas to use BaseResponseSchema.

This version handles both patterns:
1. class Config: from_attributes = True
2. model_config = ConfigDict(from_attributes=True)
"""

import os
import re
from pathlib import Path


def process_file(filepath: str) -> tuple[int, list[str]]:
    """
    Process a single file and migrate response schemas.

    Returns:
        tuple[int, list[str]]: (count of migrations, list of changes)
    """
    with open(filepath, 'r') as f:
        content = f.read()
        original = content

    changes = []
    migrations = 0

    # Skip base.py and __init__.py
    if filepath.endswith('base.py') or filepath.endswith('__init__.py'):
        return 0, []

    # Check if BaseResponseSchema import exists
    has_import = 'from app.schemas.base import BaseResponseSchema' in content

    # Find all classes that inherit from BaseModel and have from_attributes
    # Pattern: class SomethingResponse(BaseModel): ... from_attributes = True

    # We'll use a more careful approach - find each class definition
    class_pattern = re.compile(
        r'class\s+(\w+Response)\(BaseModel\):\s*\n'
        r'(.*?)'
        r'(?=\nclass\s|\n#\s*={20,}|\Z)',
        re.DOTALL
    )

    classes_to_migrate = []

    for match in class_pattern.finditer(content):
        class_name = match.group(1)
        class_body = match.group(2)

        # Check if this class has from_attributes (either pattern)
        if 'from_attributes' in class_body:
            classes_to_migrate.append(class_name)

    if not classes_to_migrate:
        return 0, []

    # Add import if needed
    if not has_import and classes_to_migrate:
        # Find place to add import
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

    # Migrate each class
    for class_name in classes_to_migrate:
        # Change base class
        old = f'class {class_name}(BaseModel):'
        new = f'class {class_name}(BaseResponseSchema):'

        if old in content:
            content = content.replace(old, new)
            changes.append(f"Changed {class_name}(BaseModel) -> BaseResponseSchema")
            migrations += 1

            # Now remove the redundant Config or model_config

            # Find the class body
            class_start = content.find(new)
            if class_start == -1:
                continue

            # Find next class or section divider
            remaining = content[class_start:]
            next_class = re.search(r'\n(?:class\s+\w+|#\s*={20,})', remaining[1:])
            if next_class:
                class_end = class_start + 1 + next_class.start()
            else:
                class_end = len(content)

            class_content = content[class_start:class_end]

            # Remove old-style Config class
            new_class_content = re.sub(
                r'\n(\s+)class Config:\s*\n'
                r'(?:\s+from_attributes\s*=\s*True\s*\n)?'
                r'(?:\s+json_encoders\s*=\s*\{[^}]+\}\s*\n)?',
                '\n',
                class_content
            )

            # Remove new-style model_config
            new_class_content = re.sub(
                r'\n(\s+)model_config\s*=\s*ConfigDict\([^)]*from_attributes\s*=\s*True[^)]*\)\s*\n',
                '\n',
                new_class_content
            )

            if new_class_content != class_content:
                content = content[:class_start] + new_class_content + content[class_end:]
                changes.append(f"  Removed Config/model_config from {class_name}")

    # Also handle classes that inherit from a Base (like CMSBannerResponse(CMSBannerBase))
    # and have model_config = ConfigDict(from_attributes=True)
    # These should stay as they are but we need to handle them if they have from_attributes

    # Pattern for Response classes inheriting from *Base with model_config
    base_inherit_pattern = re.compile(
        r'class\s+(\w+Response)\((\w+Base)\):\s*\n'
        r'(.*?)'
        r'(?=\nclass\s|\n#\s*={20,}|\Z)',
        re.DOTALL
    )

    for match in base_inherit_pattern.finditer(content):
        class_name = match.group(1)
        base_class = match.group(2)
        class_body = match.group(3)

        # Check if has from_attributes
        if 'from_attributes' in class_body and f'{class_name}(BaseResponseSchema)' not in content:
            # This class inherits from a Base class but also has from_attributes
            # We need to change it to inherit from BaseResponseSchema instead
            # Actually, for these we might want to keep them as-is but ensure they work

            # For now, let's just log these for manual review
            pass

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)

    return migrations, changes


def main():
    """Run migration on all schema files."""
    schemas_dir = Path("/Users/mantosh/Desktop/Consumer durable 2/app/schemas")

    print("=" * 60)
    print("Response Schema Migration v2 to BaseResponseSchema")
    print("=" * 60)
    print()

    total_migrations = 0
    modified_files = []

    for filepath in sorted(schemas_dir.glob("*.py")):
        count, changes = process_file(str(filepath))

        if count > 0:
            print(f"Processing: {filepath.name}")
            for change in changes:
                print(f"  - {change}")
            print()
            modified_files.append(filepath.name)
            total_migrations += count

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total migrations: {total_migrations}")
    print(f"Modified files: {len(modified_files)}")
    print()

    if modified_files:
        print("Modified files:")
        for f in modified_files:
            print(f"  - {f}")


if __name__ == "__main__":
    main()

"""
Migration script to convert all response schemas to use BaseResponseSchema.

This script:
1. Finds all *Response classes in app/schemas/*.py
2. Changes their base class from BaseModel to BaseResponseSchema
3. Removes redundant Config classes (from_attributes, json_encoders)
4. Adds the import for BaseResponseSchema if not present
"""

import os
import re
from pathlib import Path


def migrate_schema_file(filepath: str) -> tuple[bool, list[str]]:
    """
    Migrate a single schema file to use BaseResponseSchema.

    Returns:
        tuple[bool, list[str]]: (was_modified, list of changes made)
    """
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    changes = []

    # Skip base.py itself
    if filepath.endswith('base.py'):
        return False, ["Skipped: base.py itself"]

    # Skip __init__.py
    if filepath.endswith('__init__.py'):
        return False, ["Skipped: __init__.py"]

    # Check if file has any Response classes with from_attributes
    if 'from_attributes' not in content and 'Response' not in content:
        return False, ["No response schemas with from_attributes found"]

    # Step 1: Add import if not present
    import_line = "from app.schemas.base import BaseResponseSchema"
    if import_line not in content:
        # Find the imports section
        # Try to add after other app.schemas imports
        if 'from app.schemas' in content:
            content = re.sub(
                r'(from app\.schemas\.[^\n]+\n)',
                r'\1' + import_line + '\n',
                content,
                count=1
            )
            changes.append("Added BaseResponseSchema import after existing app.schemas import")
        # Or add after pydantic import
        elif 'from pydantic import' in content:
            content = re.sub(
                r'(from pydantic import[^\n]+\n)',
                r'\1\n' + import_line + '\n',
                content,
                count=1
            )
            changes.append("Added BaseResponseSchema import after pydantic import")
        # Or add at top of imports
        else:
            # Find first import and add before
            content = import_line + '\n' + content
            changes.append("Added BaseResponseSchema import at top")

    # Step 2: Find Response classes that inherit from BaseModel and have from_attributes
    # Pattern 1: class XxxResponse(BaseModel): with Config block
    pattern1 = re.compile(
        r'class\s+(\w+Response)\(BaseModel\):\s*\n'
        r'((?:\s*"""[^"]*"""\s*\n)?)'  # Optional docstring
        r'(\s*model_config\s*=\s*ConfigDict\(from_attributes=True[^)]*\)\s*\n)?'  # Optional model_config
    )

    # Pattern 2: class XxxResponse(SomeBase): where SomeBase has from_attributes (skip - already inherits)

    # Pattern for Config class removal
    config_pattern = re.compile(
        r'\n\s+class Config:\s*\n'
        r'(?:\s+from_attributes\s*=\s*True\s*\n)?'
        r'(?:\s+json_encoders\s*=\s*\{[^}]+\}\s*\n)?'
    )

    # Pattern for model_config removal
    model_config_pattern = re.compile(
        r'\s*model_config\s*=\s*ConfigDict\(from_attributes=True[^)]*\)\s*\n'
    )

    # Find all Response classes
    response_classes = re.findall(r'class\s+(\w+Response)\((\w+)\):', content)

    for class_name, base_class in response_classes:
        if base_class == 'BaseModel':
            # Check if this class has from_attributes
            class_pattern = re.compile(
                rf'(class\s+{class_name}\(BaseModel\):.*?)'
                rf'(?=\nclass\s|\n#\s*=+|\Z)',
                re.DOTALL
            )
            match = class_pattern.search(content)
            if match:
                class_body = match.group(1)
                if 'from_attributes' in class_body or 'json_encoders' in class_body:
                    # Replace BaseModel with BaseResponseSchema
                    content = content.replace(
                        f'class {class_name}(BaseModel):',
                        f'class {class_name}(BaseResponseSchema):'
                    )
                    changes.append(f"Changed {class_name}(BaseModel) -> {class_name}(BaseResponseSchema)")

                    # Remove Config class if present
                    # Find the class definition and its Config
                    class_start = content.find(f'class {class_name}(BaseResponseSchema):')
                    if class_start != -1:
                        # Find next class or end of file
                        next_class = re.search(r'\nclass\s+\w+', content[class_start + 1:])
                        class_end = class_start + 1 + next_class.start() if next_class else len(content)
                        class_content = content[class_start:class_end]

                        # Remove Config block
                        new_class_content = re.sub(
                            r'\n\s+class Config:\s*\n'
                            r'(?:\s+from_attributes\s*=\s*True\s*\n)?'
                            r'(?:\s+json_encoders\s*=\s*\{[^}]+\}\s*\n)*',
                            '\n',
                            class_content
                        )

                        # Remove model_config line
                        new_class_content = re.sub(
                            r'\s*model_config\s*=\s*ConfigDict\(from_attributes=True[^)]*\)\s*\n',
                            '\n',
                            new_class_content
                        )

                        if new_class_content != class_content:
                            content = content[:class_start] + new_class_content + content[class_end:]
                            changes.append(f"Removed Config/model_config from {class_name}")

    # Also handle classes that inherit from *Base or other parent classes and have from_attributes
    # These should also use BaseResponseSchema if they have from_attributes

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True, changes

    return False, changes if changes else ["No changes needed"]


def main():
    """Run migration on all schema files."""
    schemas_dir = Path("/Users/mantosh/Desktop/Consumer durable 2/app/schemas")

    print("=" * 60)
    print("Response Schema Migration to BaseResponseSchema")
    print("=" * 60)
    print()

    modified_files = []
    skipped_files = []

    for filepath in sorted(schemas_dir.glob("*.py")):
        print(f"Processing: {filepath.name}")
        modified, changes = migrate_schema_file(str(filepath))

        for change in changes:
            print(f"  - {change}")

        if modified:
            modified_files.append(filepath.name)
        else:
            skipped_files.append(filepath.name)

        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Modified: {len(modified_files)} files")
    print(f"Skipped:  {len(skipped_files)} files")
    print()

    if modified_files:
        print("Modified files:")
        for f in modified_files:
            print(f"  - {f}")


if __name__ == "__main__":
    main()

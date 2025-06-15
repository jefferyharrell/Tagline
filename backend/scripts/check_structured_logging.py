#!/usr/bin/env python3
"""
Validation script to check for non-structured logging patterns in the backend.

This script searches for f-string usage in logging calls and other anti-patterns
that violate the structured logging standards.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_non_structured_logging(root_path: Path) -> List[Tuple[str, int, str]]:
    """
    Find non-structured logging patterns in Python files.
    
    Args:
        root_path: Root directory to search
        
    Returns:
        List of tuples: (file_path, line_number, line_content)
    """
    violations = []
    
    # Patterns to detect non-structured logging
    patterns = [
        # f-strings in logging calls
        r'logger\.\w+\(f["\']',
        r'logger\.\w+\(.*f["\']',
        # String concatenation with +
        r'logger\.\w+\([^)]*\+[^)]*\)',
        # % formatting
        r'logger\.\w+\([^)]*%[^)]*\)',
        # .format() calls
        r'logger\.\w+\([^)]*\.format\(',
    ]
    
    compiled_patterns = [re.compile(pattern) for pattern in patterns]
    
    # Search through all Python files, excluding third-party code
    for py_file in root_path.rglob("*.py"):
        # Skip this validation script itself
        if py_file.name == "check_structured_logging.py":
            continue
            
        # Skip third-party libraries and generated files
        path_parts = py_file.parts
        if any(skip_dir in path_parts for skip_dir in [
            '.venv', 'venv', '__pycache__', '.git', 
            'node_modules', 'alembic', 'migrations'
        ]):
            continue
            
        # Only check our application code (app/ directory)
        if 'app' not in path_parts:
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                        
                    # Check against all patterns
                    for pattern in compiled_patterns:
                        if pattern.search(line):
                            violations.append((str(py_file), line_num, line))
                            break
                            
        except (UnicodeDecodeError, PermissionError):
            # Skip files we can't read
            continue
    
    return violations


def main():
    """Main validation function."""
    backend_path = Path(__file__).parent.parent
    
    print("🔍 Checking for non-structured logging patterns...")
    print(f"📁 Searching in: {backend_path}")
    
    violations = find_non_structured_logging(backend_path)
    
    if not violations:
        print("✅ No non-structured logging patterns found!")
        print("🎉 All logging calls appear to use structured logging!")
        return 0
    
    print(f"❌ Found {len(violations)} non-structured logging patterns:")
    print()
    
    for file_path, line_num, line_content in violations:
        rel_path = Path(file_path).relative_to(backend_path)
        print(f"📄 {rel_path}:{line_num}")
        print(f"   {line_content}")
        print()
    
    print("🔧 Please convert these to structured logging format:")
    print("   ❌ logger.info(f'Message with {variable}')")
    print("   ✅ logger.info('Message description', operation='context', variable=variable)")
    print()
    print("📖 See docs/structured_logging_standards.md for detailed guidelines")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
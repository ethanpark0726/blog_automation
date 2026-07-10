"""
Automatically corrects node labels containing parentheses without quotes in Mermaid diagrams of existing posts.

Example: A[Sun-dried (adobe brick)]  →  A["Sun-dried (adobe brick)"]
"""
import re
import glob

# Process only inside mermaid code blocks
MERMAID_BLOCK = re.compile(r'(```mermaid\s*)(.*?)(```)', re.DOTALL)
# Pattern to find node labels with parentheses but without quotes: [text(something)]
UNQUOTED_NODE = re.compile(r'\[([^"\]\[]*\([^)]*\)[^"\]\[]*)\]')

def fix_mermaid_in_file(filepath):
    with open(filepath, encoding='utf-8') as f:
        original = f.read()

    def fix_mermaid_block(match):
        prefix, body, suffix = match.group(1), match.group(2), match.group(3)
        fixed_body = UNQUOTED_NODE.sub(lambda m: '["' + m.group(1) + '"]', body)
        return prefix + fixed_body + suffix

    fixed = MERMAID_BLOCK.sub(fix_mermaid_block, original)

    if fixed != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
        print(f"[FIXED] {filepath}")
        return True
    else:
        print(f"[OK]    {filepath}")
        return False

files = glob.glob('_posts/**/*.md', recursive=True)
fixed_count = 0
for fp in files:
    if fix_mermaid_in_file(fp):
        fixed_count += 1

print(f"\nChecked {len(files)} files, successfully fixed {fixed_count} files.")

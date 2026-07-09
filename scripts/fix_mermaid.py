"""
기존 생성된 포스트의 Mermaid 다이어그램에서
따옴표 없이 괄호가 포함된 노드 레이블을 자동으로 수정합니다.

예: A[햇볕에 건조 (어도비 벽돌)]  →  A["햇볕에 건조 (어도비 벽돌)"]
"""
import re
import glob

# mermaid 블록 내에서만 처리
MERMAID_BLOCK = re.compile(r'(```mermaid\s*)(.*?)(```)', re.DOTALL)
# 따옴표 없이 괄호가 포함된 노드 레이블: [텍스트(뭔가)] 패턴
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

print(f"\n총 {len(files)}개 파일 검사, {fixed_count}개 수정 완료.")

# 📋 기여 규칙 (Contributing Guide)

## 🔴 필수 규칙: 변경 시 문서 업데이트 의무

> **모든 코드/설정 변경은 반드시 `README.md`와 `CHANGELOG.md`를 함께 수정해야 합니다.**  
> GitHub Actions `check_docs.yml`이 자동으로 이를 검사하며, 위반 시 빌드가 실패합니다.

---

## 버전 규칙 (Semantic Versioning)

```
MAJOR.MINOR.PATCH
  │     │     └── 버그 수정, 문서 업데이트       예: 1.2.0 → 1.2.1
  │     └──────── 새 기능 추가 (하위 호환)        예: 1.2.1 → 1.3.0
  └────────────── 하위 비호환 대규모 변경         예: 1.3.0 → 2.0.0
```

---

## 변경 시 체크리스트

### 1. CHANGELOG.md 업데이트

파일 상단에 새 버전 항목 추가:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- 새로 추가된 기능

### Changed
- 기존 동작이 변경된 내용

### Fixed
- 수정된 버그

### Removed
- 제거된 기능
```

### 2. README.md 업데이트

① 버전 배지 수정:
```markdown
[![Version](https://img.shields.io/badge/Version-X.Y.Z-purple)](CHANGELOG.md)
```

② "현재 버전" 섹션 수정:
```markdown
## 📊 현재 버전

**vX.Y.Z** — 변경 요약 한 줄
```

---

## 예외 (검사 자동 스킵)

아래 경우는 문서 업데이트 없이 커밋 가능합니다:
- `_posts/ko/` 또는 `_posts/en/` 파일만 변경 (텔레그램 봇 자동 포스트)

---

## 커밋 메시지 규칙

```
feat: 새 기능 추가
fix: 버그 수정
docs: 문서만 수정
config: 설정 변경
refactor: 코드 리팩토링 (기능 변화 없음)
```

# Obsidian Integration Implementation Plan

이 문서는 `blog_automation` 리포지토리에 Obsidian 연동을 본격적으로 넣기 위한 구현 계획서다.

목표는 단순하다.

- Telegram으로 블로그 글을 생성한다.
- Obsidian에서 생성된 글과 관련 지식을 읽고 연결한다.
- 수정 요청과 보강 요청을 Obsidian 기반으로 남긴다.
- AI가 한글/영문 포스트를 함께 갱신한다.
- 결과는 다시 GitHub로 반영되고 블로그에 재배포된다.

---

## 1. 최종 목표

현재 파이프라인을 다음 구조로 확장한다.

1. `Telegram -> GitHub Actions -> _posts/ko + _posts/en`
2. `Obsidian -> _knowledge / _ideas / _reviews`
3. `Revision Pipeline -> KO 수정 + EN 동기화 + 검증 + Git 반영`

즉, 블로그 자동화 시스템을 "글 생성기"에서 "지식 저장소 + 보강 자동화 시스템"으로 확장하는 것이 목적이다.

---

## 2. 구현 범위

이번 연동에서 구현할 대상은 아래 5개다.

| 영역 | 구현 항목 | 목적 |
|---|---|---|
| 저장소 구조 | Obsidian 전용 폴더와 템플릿 추가 | 지식, 아이디어, 리뷰를 코드와 분리 |
| 지식 그래프 | 포스트와 개념 노트의 연결 구조 추가 | Graph View 활용 |
| 보강 자동화 | 리뷰 노트 기반 revision pipeline | 수작업 감소 |
| 한영 동기화 | KO 수정 시 EN도 함께 갱신 | 이중 수작업 제거 |
| 운영 안전성 | validation, PR/commit 전략, docs 갱신 | 안정적 배포 |

---

## 3. 추천 폴더 구조

아래 구조를 공식 구조로 채택한다.

```text
blog_automation/
  _posts/
    ko/
    en/
  _knowledge/
    concepts/
    places/
    people/
    sources/
  _ideas/
  _reviews/
    pending/
    completed/
  _inbox/
  assets/
    images/
      obsidian/
  scripts/
  tests/
```

### 폴더 역할

| 폴더 | 역할 | GitHub commit | 블로그 발행 |
|---|---|---:|---:|
| `_posts/ko` | 한글 발행 포스트 | 예 | 예 |
| `_posts/en` | 영문 발행 포스트 | 예 | 예 |
| `_knowledge` | Obsidian 지식 그래프 | 예 | 아니오 |
| `_ideas` | 후속 글 아이디어 | 예 | 아니오 |
| `_reviews` | 보강 요청, 수정 요청 | 예 | 아니오 |
| `_inbox` | 임시 메모 | 예 | 아니오 |
| `assets/images/obsidian` | Obsidian용 이미지 | 예 | 선택 |

---

## 4. 구현 Phase

### Phase 1. 저장소 구조 정식 도입

목표:
Obsidian이 공식 작업 공간으로 작동할 수 있게 저장소 구조를 먼저 안정화한다.

구현 항목:

- `_knowledge`, `_ideas`, `_reviews/pending`, `_reviews/completed` 생성
- 각 폴더의 목적을 설명하는 짧은 README 또는 index 노트 생성
- Obsidian용 템플릿 문서 추가
- `.gitignore`와 `_config.yml` 검토
- `.obsidian`에서 commit할 파일과 제외할 파일 기준 문서화

완료 기준:

- 사용자가 Obsidian에서 새 노트, 리뷰 노트, 개념 노트를 바로 만들 수 있다.
- 블로그 발행 경로와 지식 관리 경로가 시각적으로 분리된다.

---

### Phase 2. 포스트와 지식 노트 연결 규칙 만들기

목표:
생성된 블로그 글이 Obsidian Graph View에 연결될 수 있는 최소 규칙을 만든다.

구현 항목:

- 포스트 front matter에 `topic_id` 또는 `canonical_id` 규칙 정의
- 같은 글의 KO/EN 포스트가 동일한 ID를 공유하게 정리
- `_knowledge` 노트에서 관련 포스트를 참조하는 링크 규칙 정의
- 개념 노트 파일명 규칙 정의
- 사람, 장소, 출처 노트 분류 규칙 정의

예시:

```yaml
topic_id: 2026-07-15-turquoise
lang: ko
paired_post: /_posts/en/2026-07-15-the-turquoise-nexus-why-santa-fe-new-mexico-shines.md
```

완료 기준:

- 하나의 주제가 KO 포스트, EN 포스트, 개념 노트와 안정적으로 연결된다.
- Graph View에서 포스트와 개념 노드가 함께 보인다.

---

### Phase 3. Knowledge Note 자동 생성

목표:
새 블로그가 생성될 때마다 Obsidian에서 읽을 수 있는 관련 노트도 자동으로 만든다.

구현 항목:

- 새 포스트 생성 후 `_knowledge` 노트 자동 생성 스크립트 추가
- 노트에 아래 항목 자동 작성
- 주제 요약
- 관련 포스트 링크
- 핵심 개념 링크
- 관련 장소/인물/출처 링크
- 후속 질문 후보

예시 출력:

```md
# 터키석

관련 포스트:
- [[2026-07-15-turquoise]]

관련 개념:
- [[상징 소비]]
- [[관광 기념품]]
- [[샤타페 시장]]

후속 질문:
- 왜 특정 지역은 특정 보석의 상징이 되는가?
- 관광 상품과 지역 정체성은 어떻게 결합되는가?
```

완료 기준:

- Telegram으로 글 하나를 생성하면 `_posts`뿐 아니라 `_knowledge` 노트도 함께 생긴다.
- Obsidian Graph View에서 새 글이 고립되지 않는다.

---

### Phase 4. 리뷰 노트 기반 보강 파이프라인

목표:
사용자가 Obsidian에서 남긴 보강 요청을 AI가 읽고 글을 다시 갱신할 수 있게 만든다.

구현 항목:

- `_reviews/pending`에 리뷰 노트 템플릿 정의
- 리뷰 노트 파서 스크립트 추가
- 대상 포스트와 수정 지시를 추출하는 로직 추가
- revision workflow 또는 수동 실행 스크립트 추가
- 완료된 리뷰 노트는 `_reviews/completed`로 이동

리뷰 노트 예시:

```md
---
target_topic_id: 2026-07-15-turquoise
target_langs:
  - ko
  - en
status: pending
---

수정 요청:
- 관광객의 상징 소비 관점을 한 단락 추가
- 여행 에세이 톤 유지
- 한국어와 영어 모두 같은 논지 반영
```

완료 기준:

- 사용자는 Obsidian에서 수정 요청만 남기면 된다.
- AI가 KO/EN 포스트를 다시 작성하고 검증까지 수행한다.

---

### Phase 5. 한글 수정 기준 영문 동기화

목표:
한글 글만 손봐도 영문 글을 다시 따로 관리하지 않도록 한다.

구현 항목:

- revision pipeline의 기준 언어를 KO로 둘지 EN으로 둘지 정책 확정
- 현재 구조상 EN canonical -> KO localize 방식과 충돌 없는 전략 정의
- 추천안:
  - 단순 typo는 KO/EN 개별 수정 허용
  - 의미 변경은 review note 기반 재생성으로 처리
- "KO 수정 -> EN 재동기화" 스크립트 또는 agent 추가

권장 운영 원칙:

- 직접 본문을 양쪽 파일에 수작업으로 맞추지 않는다.
- 의미 수정은 AI revision pipeline이 양쪽을 함께 갱신한다.
- 사용자는 수정 의도만 제공하고 최종 diff를 검토한다.

완료 기준:

- 영어 포스트 수정을 위해 사용자가 별도로 번역 지시를 반복할 필요가 없다.

---

### Phase 6. Telegram 보강 명령 추가

목표:
모바일에서도 보강 작업을 실행할 수 있게 한다.

구현 항목:

- Cloudflare Worker에 revision 트리거 명령 추가
- 예시 명령:
  - `/revise latest`
  - `/revise 2026-07-15-turquoise`
  - `/reviews`
- GitHub Actions에서 review workflow_dispatch 추가
- 완료/실패 Telegram 메시지 포맷 추가

완료 기준:

- 사용자는 집 밖에서도 revision pipeline을 실행할 수 있다.
- 실패 시 어느 리뷰 노트가 문제인지 확인할 수 있다.

---

### Phase 7. 검증과 운영 안전성 강화

목표:
Obsidian 연동으로 인해 발행 안정성이 깨지지 않게 한다.

구현 항목:

- `_posts`에 Wikilink가 직접 들어가면 실패시키는 검사
- 리뷰 노트 필수 필드 검사
- KO/EN 쌍 존재 여부 검사
- topic_id 중복 검사
- `_knowledge` 자동 생성 시 파일명 충돌 검사
- revision 후 최소 길이, 헤딩 개수, front matter, references 검증
- commit 대신 PR 생성 옵션 검토

완료 기준:

- Obsidian 연동이 발행 오류를 만들지 않는다.
- 잘못된 리뷰 노트는 배포 전에 차단된다.

---

## 5. 배포 순서 제안

한 번에 다 넣기보다 아래 순서로 배포하는 것이 좋다.

| 배포 | 범위 | 이유 |
|---:|---|---|
| 6차 | 폴더 구조, 템플릿, 운영 문서, `.gitignore`/`_config.yml` 점검 | 기반 작업 |
| 7차 | topic_id 규칙, knowledge note 자동 생성 | Graph View 가치 확인 |
| 8차 | 리뷰 노트 파서, revision workflow | 실질적 수작업 감소 시작 |
| 9차 | KO 기준 EN 동기화 정책과 자동 갱신 | 이중 수정 제거 |
| 10차 | Telegram revision 명령, 강화된 validation | 운영 완성도 향상 |

---

## 6. 실제 구현 파일 후보

| 파일 | 예상 역할 |
|---|---|
| `scripts/generate_knowledge_notes.py` | 포스트 기반 지식 노트 생성 |
| `scripts/revise_post.py` | 리뷰 노트 읽고 포스트 보강 |
| `scripts/sync_bilingual_posts.py` | KO/EN 동기화 로직 |
| `scripts/validate_obsidian_notes.py` | 리뷰/지식 노트 구조 검사 |
| `.github/workflows/revise.yml` | 보강 전용 workflow |
| `cloudflare-worker/worker.js` | `/revise` 같은 명령 추가 |
| `tests/test_revision_pipeline.py` | 보강 파이프라인 테스트 |
| `tests/test_knowledge_notes.py` | 지식 노트 생성 테스트 |

---

## 7. 우선 구현 추천

가장 먼저 구현할 것은 아래 3개다.

1. 폴더 구조와 템플릿 추가
2. topic_id 규칙과 knowledge note 자동 생성
3. 리뷰 노트 기반 revision pipeline

이 세 가지가 들어가면 Obsidian은 바로 "예쁜 편집기"가 아니라 실제 운영 도구가 된다.

---

## 8. 성공 기준

아래가 가능해지면 Obsidian 연동 1차 성공으로 본다.

- Telegram으로 새 글을 생성한다.
- 생성 후 `_knowledge`에 관련 노트가 자동 생성된다.
- Obsidian Graph View에서 글과 개념이 연결된다.
- 사용자가 `_reviews/pending`에 수정 요청을 적는다.
- revision pipeline이 KO/EN 포스트를 함께 갱신한다.
- 결과가 검증 후 GitHub에 반영된다.

---

## 9. 다음 행동

권장 시작점은 Phase 1이다.

즉, 다음 코드 변경에서는 아래를 먼저 구현한다.

1. `_knowledge`, `_ideas`, `_reviews` 폴더 생성
2. 폴더별 템플릿 노트 추가
3. Obsidian 운영 규칙 문서 추가
4. Jekyll 발행과 충돌하지 않도록 설정 점검

이후 바로 Phase 2와 Phase 3으로 넘어가면 된다.

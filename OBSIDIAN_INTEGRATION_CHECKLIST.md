# Obsidian Integration Checklist

이 문서는 `blog_automation` 저장소를 Obsidian 기반 개인 지식 저장소로 확장하기 위한 실행 체크리스트다.

- 최종 원본(Source of Truth): GitHub `main`
- 지식 탐색·검토 화면: Obsidian
- 새 글·개념·질문 생성: 기존 Python 파이프라인과 Gemini
- 공개 사이트 배포: GitHub Pages
- 기본 비용: 무료(Obsidian Sync와 Publish 사용 안 함)

> 핵심 원칙: Obsidian 자체가 질문을 생성하는 것은 아니다. Obsidian은 지식을 저장하고 연결해 보여주며, AI가 글에서 개념과 후속 질문을 추출한다. 사용자는 가치 있는 연결과 질문을 최종 선택한다.

---

## 전체 진행 현황

| Phase | 목표 | 상태 |
|---:|---|---|
| 0 | 목표·원본·동기화 원칙 확정 | ⬜ 시작 전 |
| 1 | 저장소를 무료 Obsidian Vault로 열기 | ⬜ 시작 전 |
| 2 | 수동 지식 그래프로 가치 검증 | ⬜ 시작 전 |
| 3 | 안전한 Git 동기화 방식 확정 | ⬜ 시작 전 |
| 4 | 지식 그래프용 데이터 기반 구현 | ⬜ 개발 예정 |
| 5 | 블로그 생성 시 개념·출처 노드 자동 생성 | ⬜ 개발 예정 |
| 6 | Obsidian 수정 요청 → PR 자동화 | ⬜ 개발 예정 |
| 7 | AI 후속 질문 생성 및 선택 흐름 | ⬜ 개발 예정 |
| 8 | 검증·충돌 방지·롤백 운영 고도화 | ⬜ 개발 예정 |

---

## 역할 구분

| 구성요소 | 담당 역할 |
|---|---|
| 사용자 | 글을 읽고 중요도를 판단하며 수정·후속 질문을 선택 |
| Obsidian | 글, 개념, 출처, 아이디어의 보관·검색·연결·시각화 |
| Gemini | 개념 추출, 관련성 분석, 수정안과 후속 질문 생성 |
| 로컬 Python 코드 | 파일 식별, 노드 생성, 링크 정규화, 중복 방지, 검증 |
| GitHub | 최종 원본, 버전 이력, Pull Request, 승인, 배포 |
| Telegram | 새 글 생성 요청과 작업 완료·오류 알림 |

---

# Phase 0 — 목표와 운영 원칙 확정

## 목표

Obsidian을 단순 Markdown 편집기가 아니라 장기적인 개인 지식 그래프로 사용한다.

## 체크리스트

- [ ] GitHub `main`을 유일한 최종 원본으로 사용한다.
- [ ] Obsidian Sync와 Obsidian Publish는 사용하지 않는다.
- [ ] GitHub와 Obsidian 사이의 파일 이동은 Git으로 처리한다.
- [ ] 발행 글과 내부 지식 노트를 분리한다.
- [ ] Obsidian 전용 Wikilink를 발행용 `_posts` 본문에 직접 넣지 않는다.
- [ ] AI가 추천한 연결과 질문은 자동 게시하지 않고 사용자 선택을 거친다.
- [ ] 대규모 수정은 `main` 직접 push 대신 Pull Request로 처리한다.

## 완료 조건

- [ ] 위 원칙에 동의하고 Phase 1을 시작할 준비가 됐다.

---

# Phase 1 — 저장소를 Obsidian Vault로 열기

## 목표

코드 변경 없이 현재 저장소를 Obsidian에서 읽고 탐색한다.

## 체크리스트

- [ ] Obsidian 데스크톱 앱을 설치한다.
- [ ] Obsidian에서 **Open folder as vault**를 선택한다.
- [ ] 다음 폴더를 Vault로 연다.

  ```text
  C:\Users\ethan\Downloads\blog_automation
  ```

- [ ] `Settings → Files and links`에서 **Use [[Wikilinks]]**를 끈다.
- [ ] **Automatically update internal links**를 켠다.
- [ ] 기본 첨부파일 폴더를 다음으로 지정한다.

  ```text
  assets/images/obsidian
  ```

- [ ] 다음 폴더를 Obsidian 검색·링크 추천에서 제외할지 검토한다.

  ```text
  .git
  .github
  .pipeline_cache
  _site
  scripts
  tests
  cloudflare-worker
  ```

- [ ] `_posts/ko`와 `_posts/en`의 기존 글이 정상적으로 열리는지 확인한다.
- [ ] YAML Front Matter가 Obsidian Properties로 인식되는지 확인한다.
- [ ] `.obsidian/` 설정 파일을 Git에 포함하지 않을지 결정한다.
- [ ] 초기에는 `.obsidian/` 전체를 `.gitignore`에 넣는 방식을 우선 사용한다.

## 완료 조건

- [ ] 한국어·영문 포스트를 Obsidian에서 읽을 수 있다.
- [ ] Obsidian이 기존 Markdown이나 Front Matter를 변경하지 않았다.
- [ ] 원하지 않는 코드 파일이 검색 결과를 방해하지 않는다.

---

# Phase 2 — 수동 지식 그래프로 가치 검증

## 목표

자동화 개발 전에 지식 그래프가 실제로 유용한지 1주 동안 검증한다.

## 권장 폴더

```text
_knowledge/
├── concepts/
├── sources/
└── maps/

_ideas/
├── suggested/
├── selected/
└── rejected/
```

## 체크리스트

- [ ] `_knowledge/concepts` 폴더를 만든다.
- [ ] `_knowledge/sources` 폴더를 만든다.
- [ ] `_knowledge/maps` 폴더를 만든다.
- [ ] `_ideas/suggested`, `_ideas/selected`, `_ideas/rejected` 폴더를 만든다.
- [ ] 기존 블로그 글 3개를 선택한다.
- [ ] 선택한 글에서 핵심 개념을 각 3~5개 추출한다.
- [ ] 개념 하나당 Markdown 노트 하나를 만든다.
- [ ] 개념 노트에서 관련 블로그 글과 다른 개념을 연결한다.
- [ ] 관련 분야를 모은 Map of Content 노트를 하나 만든다.
- [ ] Obsidian Local Graph에서 연결이 의도대로 보이는지 확인한다.
- [ ] 읽다가 생긴 후속 질문을 `_ideas/suggested`에 직접 기록한다.

## 개념 노트 템플릿

```markdown
---
type: concept
concept_id: proximity-sensor
aliases:
  - 근접 센서
  - Proximity Sensor
tags:
  - sensor
---

# 근접 센서

## 설명

물체가 접촉하지 않아도 가까이 있는지를 감지하는 센서.

## 관련 개념

- [[적외선 센서]]
- [[센서 융합]]

## 등장한 블로그 글

- [[AirPods는 어떻게 음악을 멈춰야 할 때를 아는가]]

## 참고자료

- [[Apple AirPods User Guide]]
```

## 가치 판단 질문

- [ ] 관련 글을 찾는 속도가 빨라졌는가?
- [ ] 새로운 후속 질문이 실제로 떠올랐는가?
- [ ] 서로 다른 글 사이의 연결을 발견했는가?
- [ ] 블로그 외에 조사 자료도 축적하고 싶은가?
- [ ] 이 구조를 계속 관리할 의향이 있는가?

## 완료 조건

- [ ] 개념 노드 10개 이상이 생성됐다.
- [ ] 블로그 글 3개 이상이 개념과 연결됐다.
- [ ] 후속 질문 5개 이상이 기록됐다.
- [ ] 위 가치 판단 질문 중 3개 이상이 `예`다.

> 완료 조건을 충족하지 못하면 자동화 개발을 보류하고 Obsidian을 단순 Markdown 뷰어로만 사용한다.

---

# Phase 3 — 안전한 Git 동기화 확정

## 목표

Telegram 자동 생성과 Obsidian 편집이 서로의 변경을 덮어쓰지 않게 한다.

## 기본 흐름

```text
GitHub main
→ 최신 변경 pull
→ Obsidian에서 읽기·편집
→ revision 브랜치
→ GitHub Pull Request
→ 검증·승인
→ main 병합
```

## 체크리스트

- [ ] Obsidian 편집 전에 항상 최신 `main`을 pull한다.
- [ ] Telegram 생성 작업이 실행 중일 때는 동일 포스트를 수정하지 않는다.
- [ ] 단순 메모를 제외한 발행 글 변경은 별도 브랜치에서 수행한다.
- [ ] `main`에 강제 push하지 않는다.
- [ ] 충돌 발생 시 자동 덮어쓰기를 금지한다.
- [ ] GitHub Desktop 또는 Git CLI 중 사용할 방식을 선택한다.
- [ ] 첫 수정은 오타 한 개만 변경해 테스트한다.
- [ ] 변경 전후 Diff를 확인한다.
- [ ] PR을 병합하고 Pages 배포를 확인한다.
- [ ] Obsidian에서 다시 pull해 병합 결과가 반영되는지 확인한다.

## CLI를 사용할 경우 참고 명령

```powershell
git pull --ff-only origin main
git switch -c revision/<post-id>
git add _posts _knowledge _ideas assets/images
git commit -m "docs: refine post knowledge links"
git push origin revision/<post-id>
```

## 완료 조건

- [ ] GitHub → Obsidian 최신화가 정상 작동한다.
- [ ] Obsidian 수정 → PR → main 병합이 정상 작동한다.
- [ ] Telegram으로 생성된 최신 포스트가 손실되지 않았다.

---

# Phase 4 — 지식 그래프 데이터 기반 구현

## 목표

자동 생성된 모든 한영 글과 지식 노드를 안정적인 ID로 연결한다.

## 개발 체크리스트

- [ ] 모든 신규 한영 포스트에 동일한 `post_id`를 부여한다.
- [ ] 기존 포스트에 `post_id`를 일괄 추가하는 백필 스크립트를 만든다.
- [ ] 잘리거나 중복될 수 있는 `topic_id`를 파일 식별 기준으로 사용하지 않는다.
- [ ] 기존 `request_fingerprint`는 생성 요청 중복 차단 용도로 유지한다.
- [ ] 개념 노드에 안정적인 `concept_id`를 부여한다.
- [ ] 영문 concept ID와 한국어·영문 alias를 분리한다.
- [ ] 출처 노드에 정규화된 URL 또는 DOI 기반 `source_id`를 부여한다.
- [ ] 같은 개념의 철자·대소문자·한영 표현을 중복 노드로 만들지 않는다.
- [ ] `_knowledge`와 `_ideas`가 Jekyll 공개 페이지로 잘못 배포되지 않는지 테스트한다.

## 완료 조건

- [ ] 모든 신규 한영 포스트가 하나의 `post_id`로 연결된다.
- [ ] 기존 포스트도 안정적인 ID를 가진다.
- [ ] 동일 개념을 반복 생성해도 노드가 중복되지 않는다.

---

# Phase 5 — 블로그 생성 시 지식 노드 자동 생성

## 목표

기존 Gemini 3-call 구조를 유지하면서 글마다 개념·출처·후속 질문을 축적한다.

## 개발 체크리스트

- [ ] Editor 출력의 `json_meta`에 `concepts`를 추가한다.
- [ ] `related_concepts`를 추가한다.
- [ ] `follow_up_questions`를 추가한다.
- [ ] `source_entities`를 추가한다.
- [ ] 모델이 본문에 없는 개념을 임의로 만들지 못하게 프롬프트를 제한한다.
- [ ] 로컬 코드가 기존 concept ID를 먼저 검색하도록 한다.
- [ ] 새 개념만 `_knowledge/concepts`에 생성한다.
- [ ] 기존 개념에는 새 블로그 포스트 백링크만 추가한다.
- [ ] 참고자료를 `_knowledge/sources`에 생성·병합한다.
- [ ] 후속 질문을 `_ideas/suggested`에 저장한다.
- [ ] 지식 노드 생성이 Gemini 호출을 추가하지 않는지 테스트한다.
- [ ] 실패 시 블로그 포스트 배포와 지식 노드 저장을 함께 롤백한다.

## 완료 조건

- [ ] 새 블로그 한 건이 생성되면 concept 노드 3~8개가 생성·갱신된다.
- [ ] 출처 노드가 중복 없이 연결된다.
- [ ] 후속 질문 2~3개가 `_ideas/suggested`에 기록된다.
- [ ] Gemini 표준 호출 수가 3회로 유지된다.

---

# Phase 6 — Obsidian 수정 요청 → PR 자동화

## 목표

사용자가 Obsidian에서 작성한 자연어 피드백을 AI가 안전하게 한영 포스트에 반영한다.

## 권장 수정 구분

| 수정 종류 | 처리 | Gemini 호출 |
|---|---|---:|
| 오타·표현·Markdown | 사용자가 직접 수정 후 검증 | 0 |
| 이미지·캡션 | 로컬 코드로 삽입·검증 | 0 |
| 사용자 제공 내용 추가 | 영문 수정 + 한국어 동기화 | 2 |
| 새로운 사실 조사·추가 | 조사 초안 + 영문 검증 + 한국어 동기화 | 최대 3 |

## 수정 요청 폴더

```text
_reviews/
├── pending/
├── processing/
├── approved/
└── rejected/
```

## 수정 요청 템플릿

```markdown
---
type: revision-request
target_post_id: airpods-6bbd0b0c
status: ready
scope: bilingual
requires_research: true
---

# 수정 요청

배터리 최적화와 센서 오작동 사례를 추가한다.

## 내가 제공하는 내용

사용자가 착용 상태가 아닌데도 음악이 멈추는 실제 사용 관점을 설명한다.

## 원하는 위치

`착용 감지의 원리` 섹션 다음
```

## 개발 체크리스트

- [ ] `_reviews` 상태 폴더를 만든다.
- [ ] 수정 요청 템플릿을 만든다.
- [ ] `status: ready` 요청만 처리한다.
- [ ] `target_post_id`로 한영 포스트를 정확히 찾는다.
- [ ] 사용자 직접 수정과 AI 수정 요청을 구분한다.
- [ ] 새로운 사실 추가 시 영어 참고자료 조사를 수행한다.
- [ ] 영문 원본을 먼저 수정한다.
- [ ] 검증된 영문을 한국어로 동기화한다.
- [ ] Front Matter의 ID·날짜·언어를 보존한다.
- [ ] 기존 출처와 새 출처를 다시 검증한다.
- [ ] Markdown·길이·제목·코드 블록 검증을 실행한다.
- [ ] Jekyll 빌드를 실행한다.
- [ ] 수정 브랜치와 PR을 자동 생성한다.
- [ ] 사용자 승인 전에는 `main`에 병합하지 않는다.

## 완료 조건

- [ ] 자연어 수정 요청 하나로 한영 포스트 수정 PR이 생성된다.
- [ ] 원본 글과 수정본 Diff를 확인할 수 있다.
- [ ] 사용자가 거절하면 기존 게시물이 변경되지 않는다.

---

# Phase 7 — AI 후속 질문 생성과 선택

## 목표

지식 그래프의 연결과 빈 공간을 다음 블로그 질문으로 전환한다.

## 질문 생성 주체

- 사용자: 글을 읽다가 실제로 궁금한 질문을 작성한다.
- AI: 현재 글에서 직접 이어지는 질문을 추천한다.
- AI 그래프 분석: 서로 연결되지 않은 개념 조합을 찾아 질문을 추천한다.
- Obsidian: 질문과 근거 연결을 저장하고 시각화한다.

## 개발 체크리스트

- [ ] 글 생성 시 `follow_up_questions` 2~3개를 기존 Editor 호출에서 받는다.
- [ ] 추천 질문에 `source_post_id`를 기록한다.
- [ ] 추천 질문에 관련 `concept_id`를 기록한다.
- [ ] 추천 질문은 자동 게시하지 않는다.
- [ ] 사용자가 선택한 질문을 `_ideas/selected`로 이동한다.
- [ ] 거절한 질문은 삭제하지 않고 `_ideas/rejected`에 보관한다.
- [ ] 동일하거나 의미가 유사한 질문을 중복 생성하지 않는다.
- [ ] 전체 그래프 분석은 매 글마다 실행하지 않는다.
- [ ] `/suggest`, 수동 실행 또는 주간 배치 중 하나를 선택한다.
- [ ] 전체 원문 대신 concept ID와 연결 요약만 AI에 전달한다.
- [ ] 선택된 질문을 기존 Telegram 생성 워크플로로 전달할 수 있게 한다.

## 권장 실행 정책

```text
글 생성 직후 후속 질문: 추가 호출 없이 생성
전체 그래프 기반 질문: 사용자 요청 시 또는 주 1회, Gemini 1회
질문 게시: 사용자 선택 후 기존 3-call 블로그 파이프라인 실행
```

## 완료 조건

- [ ] 새 글마다 후속 질문이 자동 저장된다.
- [ ] 질문이 어떤 글과 개념에서 나온 것인지 추적할 수 있다.
- [ ] 사용자가 선택한 질문만 블로그 생성으로 넘어간다.

---

# Phase 8 — 운영 안정화

## 목표

지식 노드와 게시물이 늘어나도 충돌·중복·잘못된 배포 없이 운영한다.

## 체크리스트

- [ ] 콘텐츠 쓰기 Workflow에 concurrency group을 적용한다.
- [ ] Telegram 생성과 Obsidian 수정이 동시에 `main`을 변경하지 않게 한다.
- [ ] 개념·출처·질문 중복 검사를 추가한다.
- [ ] 끊어진 Obsidian 링크 검사를 추가한다.
- [ ] Jekyll에서 깨지는 Wikilink가 `_posts`에 들어가지 않게 차단한다.
- [ ] 이미지 MIME·크기·경로 검증을 추가한다.
- [ ] 지식 노드 생성량과 수정 호출량을 Actions Summary에 표시한다.
- [ ] PR 병합 전 필수 테스트를 설정한다.
- [ ] 포스트 및 지식 그래프 롤백 절차를 문서화한다.
- [ ] `_knowledge` 전체 백업 절차를 확인한다.

## 완료 조건

- [ ] 동시 작업을 실행해도 push 충돌이 발생하지 않는다.
- [ ] 잘못된 링크와 중복 노드가 배포 전에 차단된다.
- [ ] 한 번의 Git revert로 게시물과 관련 지식 노드를 함께 복구할 수 있다.

---

# 권장 실제 진행 순서

## 지금 바로 할 일

- [ ] Phase 0의 운영 원칙을 확인한다.
- [ ] Phase 1에서 저장소를 Obsidian Vault로 연다.
- [ ] Phase 2를 1주 동안 수동으로 수행한다.
- [ ] 지식 그래프가 실제로 유용한지 판단한다.

## 가치가 확인된 후 개발할 일

- [ ] Phase 4의 `post_id`와 `concept_id` 기반을 먼저 구현한다.
- [ ] Phase 5의 자동 개념·출처·후속 질문 생성을 구현한다.
- [ ] 실제로 글을 수정하는 빈도가 확인되면 Phase 6을 구현한다.
- [ ] 개념 노드가 충분히 쌓인 뒤 Phase 7의 그래프 기반 질문 생성을 구현한다.
- [ ] 마지막으로 Phase 8 운영 안정화를 적용한다.

---

# 최종 성공 기준

- [ ] Telegram 질문 하나가 한영 블로그 글로 생성된다.
- [ ] 같은 실행에서 개념·출처·후속 질문이 지식 노드로 축적된다.
- [ ] Obsidian에서 글과 개념 사이의 관계를 그래프로 탐색할 수 있다.
- [ ] 사용자가 Obsidian에서 수정 요청을 작성할 수 있다.
- [ ] AI가 수정 요청을 반영한 PR을 생성한다.
- [ ] 사용자가 선택한 후속 질문만 새로운 블로그 글로 이어진다.
- [ ] Gemini 표준 글 생성 호출 수는 3회로 유지된다.
- [ ] GitHub `main`은 항상 검증된 최종 원본으로 유지된다.


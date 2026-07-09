# Changelog

모든 주요 변경사항은 이 파일에 기록됩니다.  
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따르며,  
버전 관리는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

---

## [1.2.0] — 2026-07-09

### Added
- **커스텀 홈 레이아웃** (`_layouts/home.html`): 사이드바 + 카드형 포스트 목록
- **사이드바 위젯**: 카테고리, 언어 필터, 최근 포스트, 태그 클라우드, 통계
- **언어 필터 탭**: 전체 / 🇰🇷 한국어 / 🇺🇸 English 즉시 필터링 (JavaScript)
- **카테고리 전용 페이지**: `/dad/` 및 `/engineer/` 독립 페이지
- **배지 시스템**: KO/EN 언어 배지 + Dad/Engineer 카테고리 배지
- **커스텀 CSS** (`assets/css/custom.css`): 카드 호버 효과, 반응형 레이아웃

### Changed
- `index.md`: 콘텐츠를 `_layouts/home.html`로 이전, 간소화
- `_config.yml`: `baseurl` 및 `url` 실제 값으로 업데이트

---

## [1.1.2] — 2026-07-09

### Added
- 텔레그램 자동 생성 포스트 2건 (KO/EN): Adobe 건축양식 관련 포스트
- 텔레그램 자동 생성 포스트 2건 (KO/EN): CrossFit 운동 관련 포스트

---

## [1.1.1] — 2026-07-07

### Fixed
- **Jekyll permalink 오류**: `/:lang/:year/:month/:day/:title/` → `/:categories/:year/:month/:day/:title/`  
  (minima 테마가 `:lang` 커스텀 변수를 지원하지 않아 빌드 실패하던 문제 해결)
- **Jekyll 빌드 실패**: `bundler-cache: true` 제거 → 명시적 `bundle install` 스텝 추가  
  (`Gemfile.lock` 미존재 시 빌드 실패하던 문제 해결)

---

## [1.1.0] — 2026-07-07

### Added
- 텔레그램 자동 생성 포스트 2건 (KO/EN): 태양계 탄생 관련 포스트

### Changed
- **Gemini 모델 다운그레이드**: `gemini-3.1-pro-preview` → `gemini-2.5-flash`  
  (API 무료 티어는 `gemini-3.1-pro`를 지원하지 않음; 유료 빌링 활성화 시 업그레이드 가능)
- `_config.yml`: GitHub Pages URL 및 `baseurl` 초기 설정

### Attempted (Reverted)
- `gemini-2.5-pro` 적용 시도 → 무료 티어 quota 초과로 실패
- `gemini-3.1-pro-preview` 적용 시도 → 무료 티어 quota 초과로 실패

---

## [1.0.0] — 2026-07-06

### Added (Initial Release)

#### Phase 0 — 웹훅 인프라
- **`cloudflare-worker/worker.js`**: 텔레그램 Webhook POST 수신 → GitHub Actions `workflow_dispatch` 중계
- **`cloudflare-worker/wrangler.toml`**: Cloudflare Worker 배포 설정

#### Phase 1 — GitHub Actions 파이프라인
- **`.github/workflows/telegram_trigger.yml`**: 텔레그램 트리거 → 멀티 에이전트 실행 → Git Push 자동화
- **`.github/workflows/deploy.yml`**: Jekyll 빌드 → GitHub Pages 자동 배포

#### Phase 1 — 멀티 에이전트 시스템
- **`scripts/multi_agent.py`**: 5개 에이전트 파이프라인
  - `ClassifierAgent`: 아빠 모드 / 엔지니어 모드 자동 분류
  - `SearchAgent`: DuckDuckGo API 팩트 수집 (Hallucination 방지)
  - `WriterAgent`: Gemini API KO + EN 초안 동시 생성
  - `EditorAgent`: 팩트체크 + 톤앤매너 + 마크다운 자동 교정
  - `FileWriterAgent`: Jekyll Front Matter 병합 + 파일 저장
- **`scripts/notify.py`**: GitHub Actions 완료 후 텔레그램 알림 전송
- **`scripts/requirements.txt`**: Python 의존성 (`google-generativeai`, `requests`)

#### Jekyll 블로그 구조
- **`_config.yml`**: Jekyll 설정 (minima 테마, SEO 플러그인, 다국어 defaults)
- **`Gemfile`**: Ruby 의존성 (Jekyll 4.3, minima, feed/seo/sitemap 플러그인)
- **`index.md`**: 블로그 홈 페이지
- **`_posts/ko/`**, **`_posts/en/`**: 한국어/영어 포스트 저장 폴더
- **`.gitignore`**: 환경변수 파일 및 빌드 결과물 제외

---

## 향후 계획 (Roadmap)

### [1.3.0] — 예정
- [ ] Gemini API 유료 빌링 활성화 → `gemini-3.1-pro-preview` 복원
- [ ] 포스트 내 Mermaid 다이어그램 렌더링 지원
- [ ] 태그별 필터링 페이지 추가

### [2.0.0] — V2 예정
- [ ] 음성 인식 기반 입력 (텔레그램 음성 메시지 → 블로그 포스트)
- [ ] 포스트 이미지 자동 생성 (Imagen API 연동)
- [ ] 소셜 미디어 자동 공유 (Twitter/X, LinkedIn)

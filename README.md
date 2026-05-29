# 🇨🇳 CN-Expressions-Memorize

> **중화권 주재원 및 HSK 4-6급 학습자를 위한 중국어 네이티브 표현 데이터베이스 자동 구축 파이프라인**

매일 수만 건의 경제 뉴스, IT 트렌드, 사회 뉴스를 스크래핑하여 실제 비즈니스 및 일상에서 자주 쓰이는 **구어체(口语), 이합사(离合词), 사자성어(成语)** 2,000개를 자동으로 수집·정제·저장하는 멀티 에이전트 시스템입니다.

---

## 📐 아키텍처 및 개선 사항

이전 영어 DB의 병목 및 실패 원인을 해결하기 위해 개선된 아키텍처를 채택했습니다:

1. **배치 프로세싱 (Batch Processing):** LLM API 호출 횟수를 대폭 줄여 Rate Limit (429 에러) 회피.
2. **다국어 인코딩 펄백:** 중국어 사이트의 복잡한 인코딩(GBK, GB2312, UTF-8) 문제를 해결.
3. **동적 데이터 소스:** Sina Finance, Baidu News 등 매일 최신 뉴스가 갱신되는 RSS 피드를 활용하여 소스 고갈 방지.
4. **환경 라우팅 (Local / Cloud):** 로컬 지정 폴더(G드라이브)가 없어도 Github Actions에서 클라우드(Google Sheets) 모드로 전환할 수 있는 확장성 확보.

---

## 🛠️ GitHub Repository 초기화 가이드

현재 프로젝트 폴더(`G:\내 드라이브\[언어 공부]\2. 중국어 암기` 내부 또는 연습용 폴더)에 소스코드가 모두 생성되었습니다. 
다음 절차를 따라 GitHub에 Public Repository를 생성하고 코드를 푸시하세요.

### Step 1. 로컬에서 Git 초기화 및 커밋
명령 프롬프트(CMD)나 PowerShell을 열고 프로젝트 폴더로 이동합니다.
```bash
cd "G:\내 드라이브\Google Antigravity\연습용\CN-Expressions-Memorize"
git init
git add .
git commit -m "Initial commit: Chinese Expression DB pipeline"
```

### Step 2. GitHub에 Repository 생성
1. GitHub 웹사이트에 로그인합니다.
2. [New Repository] 버튼을 눌러 **CN-Expressions-Memorize** 라는 이름의 Public 저장소를 만듭니다.

### Step 3. 원격 저장소 연결 및 푸시
```bash
git branch -M main
git remote add origin https://github.com/본인계정명/CN-Expressions-Memorize.git
git push -u origin main
```

### Step 4. Secret 설정
저장소의 **Settings > Secrets and variables > Actions > New repository secret**로 이동하여 다음 키를 추가합니다:
- `GEMINI_API_KEY` : 발급받은 Gemini API Key

이후 `.github/workflows/daily_expressions.yml`에 의해 매일 자동으로 파이프라인이 실행됩니다.

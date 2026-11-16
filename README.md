# PokéRogue — 개인용 한국어 개조판

공식 [pagefaultgames/pokerogue](https://github.com/pagefaultgames/pokerogue)의 특정 버전을 독립적으로 내려받아 빌드하는 **비공식 개인용 모드**입니다. 공식 계정 및 공식 저장 서버는 사용하지 않습니다.

## 요청 설정
- 경험치 획득량 **10배**
- 클래식 모드 기준 시작 골드 **111,000** (원본 1,000의 111배)
- 모든 스타터 포켓몬 해금: 전설·환상 포함. 기본 스타터 코스트 제한은 유지
- **아군 포켓몬 PP 무한:** 기술 사용으로 PP 소모되지 않음. 기존 저장 데이터의 아군 PP도 자동 회복. 상대편 PP는 정상 소모
- 일반 포켓몬의 이로치 확률 유지 (강제 출현 비활성)
- 첫 접속 시 기본 언어 한국어, 이후 언어 설정 변경 가능
- 계정 로그인 없이 웹 브라우저 로컬에 저장

## 배포와 상태
GitHub Actions 워크플로우 `.github/workflows/build-pages.yml`이 검증된 공식 beta 커밋을 가져와 수정·빌드하며, GitHub Pages 배포를 시도합니다. 사이트가 성공적으로 배포되면 `https://kimssung91-star.github.io/pokerogue-ko-mod/`에서 열 수 있습니다.

**주의:** 공개 GitHub Pages는 URL을 아는 누구나 접속할 수 있습니다. '개인용'은 공식 계정과 데이터가 분리되었다는 뜻입니다. 원본 게임의 이미지·사운드 자산이 대용량이어서 Pages의 1 GB 제한에 걸리면 배포 실패할 수 있습니다. 성공하지 않은 주소를 이미 실행 가능하다고 가정하지 마세요.

상태 확인: 저장소 **Actions** 탭 → **Build Korean PokéRogue Mod**. GitHub Pages를 사용하려면 **Settings → Pages → Build and deployment → Source: GitHub Actions**를 선택해야 합니다.

## 출처와 라이선스
- 공식 소스: [pagefaultgames/pokerogue](https://github.com/pagefaultgames/pokerogue)
- 공식 번역: [pagefaultgames/pokerogue-locales](https://github.com/pagefaultgames/pokerogue-locales)
- 공식 게임 에셋: [pagefaultgames/pokerogue-assets](https://github.com/pagefaultgames/pokerogue-assets)

원본 코드는 AGPL-3.0-only, 이미지·사운드 등 기타 자료는 각 원본 저장소의 해당 라이선스를 확인해야 합니다. 포켓몬 지식재산권에 대한 권리는 각 권리자에게 있습니다. 비공식 개조판임을 명시합니다.

## 업데이트 및 저장 데이터
배포 URL이 이전과 동일하기 때문에 기존 브라우저의 저장 데이터는 유지되도록 설계했습니다. 단, 브라우저 캐시나 서비스 워커 때문에 구버전이 잠시 남아 있을 수 있으므로 배포 완료 후 새로고침하세요. 저장 데이터가 중요한 경우 게임의 저장 내보내기 기능으로 백업하는 것을 권장합니다.

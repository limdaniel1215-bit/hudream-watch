# 휴드림 감시기 작업 재개 지침

## 현재 상태

- AWS Lightsail `hudream-watch` 생성 및 실행 중
- 공인 IPv4 `54.180.138.82`, SSH 사용자 `ubuntu`
- Ubuntu 업데이트/재부팅 및 기본 패키지 설치 완료
- `/home/ubuntu/hudream-watch/.venv` 생성 완료
- GitHub 저장소 `limdaniel1215-bit/hudream-watch` 생성 후 Public 전환 완료
- 현재 채팅에서는 GitHub 플러그인 재설치 후에도 백엔드가 `Unknown tool`을 반환해 저장소 쓰기 불가

## 이 패키지 내용

- Telegram 명령 `/add`, `/list`, `/delete`, `/start`, `/stop`, `/status`, `/help`
- SQLite 감시 조건 저장
- 날짜 조합별 조회 중복 제거
- `rcnt > 0 && cnt > 0` 판정
- 403/429/503 및 사이트 과부하 백오프
- 로그인 세션 만료 알림 후 감시 중단
- systemd 서비스 초안

## 다음 채팅에서 할 일

1. `@GitHub`를 선택해 새 채팅 시작
2. 원본 `hudream_work_handoff.md`, `work_first_message.txt`, 이 ZIP을 첨부
3. `limdaniel1215-bit/hudream-watch`의 README를 읽어 GitHub 접근 확인
4. ZIP의 코드를 검토하고 저장소에 커밋
5. 휴드림 정상 UI 흐름에서 현재 엔드포인트/필드 재검증
6. 서버에서 사용자가 직접 휴드림 로그인할 수 있는 안전한 브라우저 접근 구성
7. Telegram BotFather 토큰과 허용 user/chat ID는 채팅이 아닌 서버 `.env`에 사용자 직접 입력
8. systemd 등록 및 실제 감시조건 테스트

## 중요 안전 정책

- 카드정보 저장, 자동예약, 자동결제 금지
- CAPTCHA/MFA/본인인증 우회 금지
- `/inicisCall.do`, `rsvtn_confirmView.do`, `mem_rsvtn_result.do` 호출 금지
- 403/429/503 및 `data.msg == 1`에 빠른 재시도 금지
- 비밀번호, 쿠키, 토큰, 개인정보 로그 출력 금지

## 주의

`hudream.py`의 객실 페이지 URL과 UI 선택자는 현재 사이트 로그인 상태에서 재검증하기 전까지 초안이다. 검증 없이 운영 배포하지 않는다.

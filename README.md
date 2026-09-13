# hudream-watch

휴드림 로카우스 나인트리 호텔의 잔여 객실을 정상 웹 UI 흐름으로 확인하고, 실제 예약 가능 수량이 발견되면 Telegram으로 알리는 개인용 감시기입니다.

## 안전 범위

- 조회만 수행하며 예약·결제 엔드포인트를 호출하지 않습니다.
- 카드 정보, 휴드림 비밀번호, 쿠키를 저장하거나 로그에 출력하지 않습니다.
- 최초 로그인과 MFA·본인인증은 사용자가 직접 수행합니다.
- `rcnt > 0`과 `cnt > 0`을 모두 만족할 때만 알립니다.
- HTTP 403은 즉시 중단하고, 429·503·사이트 과부하는 백오프 후 3회 반복 시 중단합니다.
- 운영 전 현재 사이트에서 선택자와 `/ro/search_ajax.do` 응답 필드를 재검증해야 합니다.

## Telegram 명령

```text
/add YYYY-MM-DD 숙박일수 객실명
/list
/delete ID
/start ID
/stop ID
/status
/help
```

같은 체크인·체크아웃 조합은 주기마다 한 번만 조회합니다. 발견 알림 후 해당 조건은 기본적으로 비활성화됩니다.

## 설치 준비

Ubuntu 24.04와 Python 3.12 기준입니다.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install --with-deps chromium
cp .env.example .env
chmod 600 .env
mkdir -p data profile logs
chmod 700 profile
```

Telegram 토큰과 허용 user/chat ID는 서버의 `.env`에 직접 입력합니다. 채팅이나 커밋에 넣지 마세요.

## 검증

```bash
.venv/bin/pytest -q
```

휴드림 로그인 프로필이 준비되고 현재 UI 검증이 끝난 뒤에만 서비스를 등록합니다.

```bash
sudo cp systemd/hudream-watch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hudream-watch
sudo systemctl status hudream-watch
```

서비스는 `/home/ubuntu/hudream-watch` 배치를 전제로 합니다.

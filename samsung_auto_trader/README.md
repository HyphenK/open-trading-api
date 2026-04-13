# Samsung Auto Trader

한국투자증권 Open API 모의투자 환경에서 삼성전자(005930)만 대상으로 동작하는 REST 기반 자동매매 예제입니다.

## 이번 버전의 핵심 추가사항

- **재고 관리 한도**: `INITIAL_POSITION=20`, `MIN_POSITION=5`, `MAX_POSITION=40`
- **장중/재실행 초기화**: 장이 열려 있고 삼성전자 보유 수량이 `INITIAL_POSITION`보다 적으면 시장가로 부족분을 채운 뒤 루프 시작
- **장 마감 전 정리**: `15:20 KST`부터 미체결 주문 취소 후 매도 가능 수량을 시장가로 정리
- **장 종료**: `15:30 KST` 이후 자동 종료
- **미체결 주문 조회 보정**: `open_orders.py`는 이제 당일 체결 이력 대신 **정정/취소 가능 주문 조회** 기준으로 현재 살아 있는 주문만 보도록 수정

## 특징

- REST API만 사용
- 모의투자 전용
- 토큰 same-day 캐시 재사용
- KST(Asia/Seoul) 기준 거래 시간 판정
- 주문가는 주문 직전 **호가단위 자동 보정**
- **최대/최소 보유량 제한**
- **상태 블록 로그**로 보유량과 미체결 주문 한눈에 표시

## 기본 설정값

`config.py` 기준:

- `INITIAL_POSITION = 20`
- `MIN_POSITION = 5`
- `MAX_POSITION = 40`
- `BUY_OFFSET_KRW = 1000`
- `SELL_OFFSET_KRW = 1000`
- `CLOSEOUT_START = 15:20`
- `TRADING_END = 15:30`
- `OPEN_ORDERS_ENDPOINT = "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"`
- `TR_ID_OPEN_ORDERS_DEMO = "VTTC8036R"`

## 동작 흐름

### 1) 장 시작 전/직후

- 09:10 KST 전이면 대기
- 09:10 KST 이후 첫 진입 시 `INITIAL_POSITION` 점검
- 보유 수량이 20주보다 적으면 **시장가 매수**로 부족분 충당
- 이미 20주 이상이면 추가 초기화 없이 본 거래 루프 시작

### 2) 일반 거래 루프

1. 현재가 조회
2. 잔고 조회
3. 미체결 주문 조회
4. 상태 블록 출력
5. 미체결 주문이 있으면 신규 주문 스킵
6. 보유 수량이 `MAX_POSITION` 미만이고 현금이 충분하면 지정가 매수 시도
7. 매수 후 5초 대기 후 재조회
8. 보유 수량이 `MIN_POSITION` 초과이고 `sellable_qty`가 있으면 지정가 매도 시도
9. 매도 후 5초 대기 후 재조회

### 3) 마감 전 정리

15:20 KST 이후에는:

1. 미체결 주문 조회
2. **가능한 주문 취소 요청**
3. 2초 대기
4. 잔고 재조회
5. 매도 가능 수량이 있으면 **시장가 매도**
6. 15:30 KST까지는 추가 신규 주문 없이 대기

## 중요 메모

- 미체결 주문 조회가 실제와 어긋날 경우, 먼저 `open_orders.py`와 `config.py`의 조회 endpoint/TR ID가 현재 계좌 환경과 맞는지 확인하세요.
- 이 버전은 **정정/취소 가능 주문 조회**를 기준으로 현재 살아 있는 주문만 가져오도록 작성했습니다.
- 계좌/환경에 따라 일부 TR ID나 응답 필드가 다를 수 있으므로, 문제가 생기면 `TR_ID_OPEN_ORDERS_DEMO`를 우선 점검하세요.
- 미체결 주문 취소에는 주문번호와 주문조직번호(`order_branch`)가 필요할 수 있어, `open_orders.py`에서 함께 파싱합니다.

## 비상 정리 스크립트 (`order_delete.py`)

`main.py`가 실행 도중 중단되면, 기존 미체결 매수/매도 주문이 서버에 남아서 다음 실행 때 **과매수/과매도**처럼 보일 수 있습니다. 이럴 때는 아래 스크립트로 삼성전자(005930) 잔여 주문만 정리하세요.

실행:

```bash
python order_delete.py
```

동작:

1. **정정/취소 가능 주문 조회**로 현재 살아 있는 주문만 확인
2. 남아 있는 매수/매도 주문을 하나씩 취소 요청
3. `POST_CANCEL_SETTLE_SECONDS`만큼 대기
4. 다시 미체결 주문을 조회해 남은 주문이 있는지 확인
5. 취소 전/후 주문 요약을 로그로 출력

권장 사용 시점:

- `main.py`가 예외로 종료된 직후
- 서버 재부팅 직후
- 전략 수정 후 재시작 전
- MAX/MIN 재고 상태가 로그와 실제 서버 주문 상태가 어긋나는 것처럼 보일 때

## 환경변수

`.env` 파일 예시:

```bash
GH_ACCOUNT=12345678-01
GH_APPKEY=your_app_key
GH_APPSECRET=your_app_secret
```

## 실행

```bash
pip install -r requirements.txt
python main.py
```

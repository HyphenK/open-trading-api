# Samsung Auto Trader

한국투자증권 Open API 모의투자 환경에서 삼성전자(005930)만 대상으로 동작하는 REST 기반 자동매매 예제입니다.

## 특징

- REST API만 사용
- 모의투자 전용
- 토큰 same-day 캐시 재사용
- 과도한 호출을 피하기 위한 보수적 폴링 구조
- API 레이어와 거래 로직 분리
- VS Code에서 바로 실행하기 쉬운 단일 폴더 구조
- 거래 시간은 **한국시간(KST, Asia/Seoul)** 기준으로 판단
- 주문가는 주문 직전 **호가단위에 맞게 자동 보정**

## 폴더 구조

```text
samsung_auto_trader/
├── .env.example
├── .gitignore
├── account.py
├── api_client.py
├── auth.py
├── config.py
├── logger.py
├── main.py
├── market_data.py
├── orders.py
├── requirements.txt
├── token_cache.json      # 실행 후 생성
├── trader.py
└── README.md
```

## 파일별 역할

- `config.py`: 환경변수, 엔드포인트, TR ID, 거래 시간, 타임존(KST), 폴링 간격, 가격 오프셋 등 공통 설정
- `logger.py`: 콘솔 + 파일 로깅 설정
- `auth.py`: 접근토큰 발급/재사용, hashkey 발급
- `api_client.py`: 공통 HTTP 요청, 재시도, 타임아웃, 공통 헤더 처리
- `market_data.py`: 삼성전자 현재가 조회
- `account.py`: 잔고/보유수량 조회와 응답 파싱
- `orders.py`: 현금 지정가 매수/매도 주문, 호가단위 보정
- `trader.py`: 거래 윈도우 제어, 주문 전후 잔고 비교, 실행 여부 추정
- `main.py`: 전체 조립 및 실행 진입점

## 실행 전 준비

### 1) 의존성 설치

```bash
pip install -r requirements.txt
```

### 2) 환경변수 설정

`.env.example`를 복사해서 `.env`를 만든 뒤 값을 채우세요.

```bash
GH_ACCOUNT=12345678-01
GH_APPKEY=your_app_key
GH_APPSECRET=your_app_secret
```

`GH_ACCOUNT`는 `12345678`처럼 8자리만 넣어도 되고, `12345678-01`처럼 8-2 형식으로 넣어도 됩니다.

### 3) 실행

```bash
python main.py
```

## 기본 동작

프로그램은 **KST 기준 09:10 ~ 15:30** 사이에만 거래 루프를 돌립니다.

한 사이클의 순서는 다음과 같습니다.

1. 현재가 조회
2. 잔고/보유수량 조회
3. `현재가 - 1000원` 계산
4. 계산된 매수가를 **호가단위에 맞게 내림 보정**한 뒤 지정가 매수 주문 시도
5. 주문 후 잔고 재조회
6. 보유 수량이 있으면 `현재가 + 1000원` 계산
7. 계산된 매도가를 **호가단위에 맞게 올림 보정**한 뒤 지정가 매도 주문 시도
8. 주문 후 잔고 재조회
9. 다음 폴링까지 대기

예를 들어 현재가가 `171450원`으로 조회되고 해당 가격대의 호가단위가 `100원`이면:

- 매수 원시가격: `170450`
- 실제 매수 주문가: `170400`
- 매도 원시가격: `172450`
- 실제 매도 주문가: `172500`

즉, 조회 현재가가 호가 중간값처럼 보여도 주문 직전에 유효 호가로 정규화합니다.

## 안전 관련 메모

이 예제는 **모의투자 전용**입니다.

또한 아래 원칙을 적용했습니다.

- 웹소켓 미사용
- 주문 직전/직후에만 잔고 재조회
- 1회 사이클당 불필요한 추가 조회 회피
- sellable qty가 없으면 매도 주문 생략
- 토큰은 같은 날 재사용
- 거래 시간 판정은 UTC가 아니라 **Asia/Seoul** 고정 사용

## 수정하기 쉬운 값

`config.py`에서 아래 값을 쉽게 바꿀 수 있습니다.

- `BUY_OFFSET_KRW`
- `SELL_OFFSET_KRW`
- `POLL_INTERVAL_SECONDS`
- `DEFAULT_ORDER_QTY`
- `TRADING_START`
- `TRADING_END`

## 주의

- 현재 구현의 호가단위 함수는 삼성전자처럼 **유가증권시장(KOSPI) 주식**을 기준으로 두었습니다.
- KIS 응답의 일부 필드명은 계좌/환경별로 달라질 수 있습니다. 이 프로젝트는 샘플 저장소 기준의 필드와 일반적인 KIS 응답 키를 함께 처리하도록 작성했지만, 실제 모의환경 응답을 한 번 확인한 뒤 `account.py`의 파싱 키 후보를 조정하는 것을 권장합니다.

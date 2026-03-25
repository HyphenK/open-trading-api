# Samsung Auto Trader

자동 매매 시스템 - 한국투자 Open API를 사용한 삼성전자(005930) 모의투자

## 概要

이 프로그램은 한국투자증권 Open API를 사용하여 삼성전자(005930)의 **모의투자**를 자동으로 실행합니다.

### 주요 특징

- **REST API만 사용** (WebSocket 미사용)
- **토큰 캐싱**: 같은 날 토큰 재사용으로 인증 최소화
- **거래시간 관리**: 09:10 ~ 15:30 자동 시간 관리
- **모의투자 전용**: 안전한 mock trading only
- **저수준 API 사용**: 모의투자 요청 제한을 고려한 최소한의 호출
- **상세 로깅**: 모든 중요한 작업 기록
- **모듈화된 구조**: 테스트·유지보수 용이

## 거래 로직

프로그램은 아래 순서로 반복 실행합니다 (09:10 ~ 15:30):

1. 현재가 조회
2. 계좌 잔액 / 보유종목 확인
3. **지정가 매수 주문**: 현재가 - 2,000 KRW
4. **지정가 매도 주문**: 현재가 + 2,000 KRW  
5. 주문 후 잔액 / 보유종목 재확인 (주문 체결 확인)

## 필수 환경변수

```bash
GH_ACCOUNT     # 계좌번호 (8자리만, 예: 50174021)
GH_APPKEY      # 앱키
GH_APPSECRET   # 앱시크릿
```

**주의**: GH_ACCOUNT는 **8자리 숫자만** 저장하면, 코드에서 자동으로 `-01`을 붙입니다.

### 환경변수 설정 방법

**방법 1: `.env` 파일 사용 (권장)**

프로젝트 루트에 `.env` 파일 생성:

```bash
GH_ACCOUNT=50174021
GH_APPKEY=your_appkey_here
GH_APPSECRET=your_appsecret_here
```

**방법 2: 시스템 환경변수**

```bash
export GH_ACCOUNT=12345678-01
export GH_APPKEY=your_appkey_here
export GH_APPSECRET=your_appsecret_here
```

**방법 3: VS Code 런처 (직접 입력)**

프로그램 실행 시 입력 프롬프트에서 직접 입력

> ⚠️ **보안**: 절대로 아이디/패스워드를 코드에 하드코딩하지 마세요!
> GitHub에 푸시할 때 `.env` 파일을 `.gitignore`에 추가하세요.

## 설치 및 실행

### 1. 의존성 설치

```bash
cd samsung_auto_trader
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 필수 환경변수를 입력하세요.

### 3. 프로그램 실행

```bash
python main.py
```

### 4. 거래 시작

- 프로그램이 시작되면 **09:10부터** 자동으로 거래 시작
- 거래 시간 전: 대기 상태 (1분 간격 체크)
- 거래 시간: 5초 간격으로 trade cycle 반복
- **15:30 이후**: 거래 자동 종료

### 5. 프로그램 종료

```bash
Ctrl+C
```

## 파일 구조 및 책임

```
samsung_auto_trader/
├── main.py              # 진입점, 초기화
├── config.py            # 설정, 상수, 환경변수
├── logger.py            # 로깅 설정
├── auth.py              # 인증, 토큰 캐싱
├── api_client.py        # REST API 클라이언트
├── market_data.py       # 현재가 조회
├── account.py           # 계좌 정보
├── orders.py            # 주문 (매수/매도)
├── trader.py            # 메인 거래 로직
├── requirements.txt     # 의존성
├── token_cache.json     # 토큰 캐시 (런타임 생성)
└── README.md            # 이 문서
```

| 파일 | 책임 |
|------|------|
| `main.py` | 프로그램 시작 |
| `config.py` | 설정 관리 (API 엔드포인트, 시간, 오프셋 등) |
| `logger.py` | 로깅 (파일 + 콘솔) |
| `auth.py` | 토큰 인증, 같은 날 캐싱 재사용 |
| `api_client.py` | HTTP 클라이언트 (모든 API 호출) |
| `market_data.py` | 현재가 및 호가 조회 |
| `account.py` | 잔액, 보유종목 조회 |
| `orders.py` | 매수/매도 주문 |
| `trader.py` | 거래 시간 관리, 거래 순서 조율 |

## 로그 출력 예

```
2026-03-25 09:10:15 - __main__ - INFO - ============================================================
2026-03-25 09:10:15 - __main__ - INFO - 🟢 TRADING WINDOW OPENED at 09:10:15
2026-03-25 09:10:15 - __main__ - INFO - ============================================================
2026-03-25 09:10:16 - market_data - INFO - 현재가: 70,500 KRW | 매도호가: 70,600 | 매수호가: 70,000
2026-03-25 09:10:16 - account - INFO - Account: 5,000,000 KRW | Samsung: 0 shares (0 KRW)
2026-03-25 09:10:17 - orders - INFO - Placing BUY order: 1 shares @ 68,500 KRW
2026-03-25 09:10:17 - orders - INFO - ✓ Buy order placed: Order ID=123456789
2026-03-25 09:10:22 - orders - INFO - Placing SELL order: 1 shares @ 72,500 KRW
2026-03-25 09:10:23 - orders - INFO - ✓ Sell order placed: Order ID=123456790
2026-03-25 09:10:28 - account - INFO - Account: 5,002,000 KRW | Samsung: 0 shares (0 KRW)
2026-03-25 09:10:28 - trader - INFO - ✓ Order execution confirmed: Samsung holdings changed by 0
```

## 설정 커스터마이징

[config.py](config.py)에서 다음 항목을 수정할 수 있습니다:

```python
# 거래시간
TRADING_START_HOUR = 9
TRADING_START_MINUTE = 10
TRADING_END_HOUR = 15
TRADING_END_MINUTE = 30

# 주문 가격 오프셋
BUY_ORDER_OFFSET = 2000      # 현재가 - 2000 KRW
SELL_ORDER_OFFSET = 2000     # 현재가 + 2000 KRW

# API 폴링 간격
PRICE_CHECK_INTERVAL = 30    # seconds
BALANCE_CHECK_INTERVAL = 60  # seconds
POLLING_INTERVAL = 5         # seconds (trade cycle)

# API 타임아웃
API_TIMEOUT = 10             # seconds
```

## 주요 기능

### ✅ 토큰 캐싱

- 프로그램 시작 시 토큰 생성
- 같은 날 재시작 시 기존 토큰 재사용
- 모의투자 API 한도 절감

### ✅ 거래시간 관리

- 거래시간 전: 대기
- 거래시간 (09:10 ~ 15:30): 활성 거래
- 거래시간 후: 자동 종료

### ✅ 상세 로깅

모든 작업이 `auto_trader.log` 및 콘솔에 기록됩니다:
- 토큰 발급 / 재사용
- 현재가 조회
- 주문 요청 / 응답
- 잔액 변동
- API 오류 및 재시도

### ✅ 안전한 설계

- 모의투자만 사용 (영 거래 없음)
- 과도한 API 호출 방지
- 타임아웃 및 에러 처리
- 환경변수로 안전한 자격증명 관리

## 트러블슈팅

### 환경변수 오류

```
ValueError: Missing required environment variables
```

**해결**: `.env` 파일이 있는지 확인하고 필수 변수 입력:

```bash
GH_ACCOUNT=...
GH_APPKEY=...
GH_APPSECRET=...
```

### API 오류 (rt_cd != 0)

로그에서 오류 메시지 확인:

```
API Error: rt_cd=..., msg=...
```

**일반 해결책**:
- 계좌번호 형식 확인 (12345678-01)
- 앱키/시크릿 유효성 확인
- 모의투자 계좌 확인
- 거래시간 확인

### 너무 많은 API 호출

모의투자는 API 호출 제한이 있습니다. `config.py`에서 간격 증가:

```python
POLLING_INTERVAL = 10  # 5초 → 10초
```

## 주의사항

⚠️ **모의투자 전용**
- 이 프로그램은 **모의투자만** 지원합니다
- 실거래로 전환하려면 별도의 검증 필요

⚠️ **API 한도**
- 모의투자는 API 호출 제한이 있습니다
- 필요에 따라 폴링 간격 조정

⚠️ **보안**
- 환경변수 절대 하드코딩 금지
- `.env` 파일 꼭 `.gitignore` 추가

## 라이센스

MIT License

## 지원

문제 발생 시:
1. 로그 파일 (`auto_trader.log`) 확인
2. 환경변수 및 계좌정보 재확인
3. 모의투자 상태 확인

---

**Last Updated**: 2026-03-25  
**API Version**: 1.0.2  
**Python Version**: 3.8+

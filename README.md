# LawCast

국회 입법예고 변동사항을 Discord 웹훅으로 실시간 알림을 받을 수 있는 플랫폼입니다.

## 프로젝트 개요

LawCast는 국회 입법예고 사이트(pal.assembly.go.kr)의 새로운 입법예고를 모니터링하여, 사용자가 등록한 Discord 웹훅으로 자동 알림을 전송하는 서비스입니다.

### 주요 기능

- **자동 모니터링**: 10분마다 자동으로 새로운 입법예고 확인
- **Discord 알림**: 새로운 입법예고 발견 시 Discord 웹훅으로 실시간 알림
- **간편 등록**: 로그인 없이 웹훅 URL만으로 간단 등록
- **최소 보안**: Google reCAPTCHA를 통한 기본 스팸 방지
- **반응형 UI**: 모바일과 데스크톱 모두 지원
- **병렬 처리**: 여러 웹훅에 대한 효율적인 병렬 알림 전송
- **자동 정리**: 실패한 웹훅 자동 비활성화 및 메모리 캐시 관리

## 프로젝트 구조

```
lawcast/
├── backend/          # NestJS 백엔드 API 서버
├── frontend/         # SvelteKit 프론트엔드 웹 애플리케이션
└── README.md         # 프로젝트 메인 문서
```

## 빠른 시작

### Docker를 사용한 실행 (권장)

```bash
# 환경 변수 설정 (선택사항)
echo "RECAPTCHA_SECRET_KEY=your_secret_key" > .env
echo "PUBLIC_RECAPTCHA_SITE_KEY=your_site_key" >> .env

# 프로덕션 환경
docker-compose up -d

# 개발 환경
docker-compose -f docker-compose.dev.yml up -d
```

- 프로덕션: 프론트엔드 `http://localhost:3000`, 백엔드 `http://localhost:3001`
- 개발환경: 프론트엔드 `http://localhost:5173`, 백엔드 `http://localhost:3001`
- DB 데이터는 Docker 볼륨에 자동으로 저장되어 영구 보존됩니다

### 로컬 개발

#### 1. 백엔드 실행

```bash
cd backend
npm install
# 환경 변수 설정 (선택사항)
echo "RECAPTCHA_SECRET_KEY=your_key_here" > .env
echo "FRONTEND_URL=http://localhost:5173" >> .env
npm run start:dev
```

백엔드는 `http://localhost:3001`에서 실행됩니다.

#### 2. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

프론트엔드는 `http://localhost:5173`에서 실행됩니다.

### 3. 테스트 실행

```bash
# 백엔드 유닛 테스트
cd backend
npm test

# 특정 테스트 그룹 실행
npm test -- --testPathPattern="utils|services"

# 프론트엔드 테스트
cd frontend
npm run test
```

## 기술 스택

### Backend (NestJS)

- **Framework**: NestJS with TypeScript
- **Database**: SQLite (TypeORM)
- **Scheduling**: @nestjs/schedule (Cron Jobs)
- **Crawler**: pal-crawl
- **Notifications**: discord-webhook-node
- **Caching**: 메모리 기반 캐시 시스템
- **Validation**: class-validator with comprehensive input validation
- **Testing**: Jest 기반 유닛 테스트 (68개 테스트 케이스)
- **Security**: Google reCAPTCHA v2 통합

### Frontend (SvelteKit)

- **Framework**: SvelteKit + TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide Svelte
- **HTTP Client**: Axios

## API 엔드포인트

### 웹훅 관리

- `POST /api/webhooks` - 새 웹훅 등록 (reCAPTCHA 검증 포함)
  - Request Body: `{ "url": "discord_webhook_url", "recaptchaToken": "token" }`
  - 응답: 웹훅 등록 성공/실패 및 테스트 결과

### 입법예고 관리

- `GET /api/notices/recent` - 최근 입법예고 목록 조회 (기본 10개)
- `GET /api/health` - 서비스 상태 확인

### 보안 기능

- Discord 웹훅 URL 형식 검증
- IP 추출 및 로깅
- reCAPTCHA v2 토큰 검증
- 웹훅 중복 등록 방지 (URL 정규화)

## 자동화 프로세스

1. **크롤링**: 정해진 시간마다 국회 입법예고 사이트 확인
2. **비교**: 메모리 캐시와 비교하여 새로운 입법예고 감지
3. **병렬 처리**: 여러 웹훅에 동시 알림 전송으로 성능 최적화
4. **자동 정리**: 실패한 웹훅(404, 401, 403 오류) 자동 비활성화
5. **캐시 관리**: 50개 항목 제한으로 메모리 효율성 보장
6. **오류 처리**: 네트워크 오류와 웹훅 오류 구분하여 처리

## 환경 설정

### Backend (backend/.env)

```env
# 서버 설정
PORT=3001
NODE_ENV=development

# 데이터베이스 설정
DATABASE_PATH=lawcast.db

# reCAPTCHA 설정 (선택사항)
RECAPTCHA_SECRET_KEY=your_secret_key_here

# 크론 작업 시간대
CRON_TIMEZONE=Asia/Seoul

# CORS 허용 도메인 (쉼표로 구분)
FRONTEND_URL=http://localhost:5173,http://localhost:3002
```

### Frontend (frontend/.env)

```env
# API 서버 URL
PUBLIC_API_BASE_URL=http://localhost:3001/api

# reCAPTCHA 사이트 키 (선택사항)
PUBLIC_RECAPTCHA_SITE_KEY=your_site_key_here
```

### 환경 변수 설명

- `PORT`: 백엔드 서버 포트 (기본값: 3001)
- `NODE_ENV`: 실행 환경 (development, production)
- `DATABASE_PATH`: SQLite 데이터베이스 파일 경로 (기본값: lawcast.db)
- `RECAPTCHA_SECRET_KEY`: Google reCAPTCHA v2 시크릿 키 (선택사항)
- `CRON_TIMEZONE`: 크론 작업 시간대 설정 (기본값: Asia/Seoul)
- `FRONTEND_URL`: CORS 허용 도메인 (쉼표로 구분된 여러 도메인 지원)

## 사용법

1. **Discord 웹훅 생성**: Discord 서버/채널에서 웹훅 URL 발급
2. **웹훅 등록**: LawCast 웹사이트에서 웹훅 URL 입력 및 등록
3. **자동 알림**: 새로운 입법예고 발견 시 자동으로 Discord 알림 수신

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 문의

문제나 제안사항이 있으시면 GitHub Issues를 통해 연락해 주세요.

---

**참고 프로젝트**

- [pal-crawl](https://github.com/vientorepublic/pal-crawl): 국회 입법예고 크롤러 라이브러리
- [pal-webhook](https://github.com/vientorepublic/pal-webhook): 디스코드 웹훅 알리미 참조 구현

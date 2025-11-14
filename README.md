# LawCast 🏛️

국회 입법예고 변동사항을 Discord 웹훅으로 실시간 알림을 받을 수 있는 플랫폼입니다.

## 프로젝트 개요

LawCast는 국회 입법예고 사이트(pal.assembly.go.kr)의 새로운 입법예고를 모니터링하여, 사용자가 등록한 Discord 웹훅으로 자동 알림을 전송하는 서비스입니다.

### 주요 기능

- **자동 모니터링**: 10분마다 자동으로 새로운 입법예고 확인
- **Discord 알림**: 새로운 입법예고 발견 시 Discord 웹훅으로 실시간 알림
- **간편 등록**: 로그인 없이 웹훅 URL만으로 간단 등록
- **최소 보안**: Google reCAPTCHA를 통한 기본 스팸 방지
- **반응형 UI**: 모바일과 데스크톱 모두 지원

## 프로젝트 구조

```
lawcast/
├── backend/          # NestJS 백엔드 API 서버
├── frontend/         # SvelteKit 프론트엔드 웹 애플리케이션
└── README.md         # 프로젝트 메인 문서
```

## 🚀 빠른 시작

### 1. 백엔드 실행

```bash
cd backend
npm install
npm run start:dev
```

백엔드는 `http://localhost:3001`에서 실행됩니다.

### 2. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

프론트엔드는 `http://localhost:5173`에서 실행됩니다.

## 기술 스택

### Backend (NestJS)

- **Framework**: NestJS
- **Database**: SQLite (TypeORM)
- **Scheduling**: @nestjs/schedule (Cron Jobs)
- **Crawler**: pal-crawl
- **Notifications**: discord-webhook-node

### Frontend (SvelteKit)

- **Framework**: SvelteKit + TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide Svelte
- **HTTP Client**: Axios

## API 엔드포인트

### 웹훅 관리

- `POST /api/webhooks` - 새 웹훅 등록
- `GET /api/webhooks` - 등록된 웹훅 목록 조회
- `DELETE /api/webhooks/:id` - 웹훅 삭제

### 입법예고 관리

- `POST /api/check` - 수동 입법예고 확인
- `GET /api/notices/recent` - 최근 입법예고 목록 조회
- `GET /api/health` - 서비스 상태 확인

## 자동화 프로세스

1. **크롤링**: 정해진 시간마다 국회 입법예고 사이트 확인
2. **비교**: 기존 데이터와 비교하여 새로운 입법예고 감지
3. **저장**: 새로운 입법예고를 SQLite 데이터베이스에 저장
4. **알림**: 등록된 모든 Discord 웹훅으로 알림 전송

## 🛠️ 환경 설정

### Backend (.env)

```env
PORT=3001
NODE_ENV=development
DB_TYPE=sqlite
DB_DATABASE=lawcast.db
RECAPTCHA_SECRET_KEY=your_secret_key_here
CRON_TIMEZONE=Asia/Seoul
```

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

## 라이선스

MIT

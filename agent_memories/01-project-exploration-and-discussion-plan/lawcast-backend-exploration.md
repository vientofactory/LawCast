# LawCast Backend Exploration

## Technology Stack
- **Framework**: NestJS 11.x
- **Database**: SQLite 3 with TypeORM 0.3.27
- **ORM**: TypeORM (not Kysely/better-sqlite3/Prisma)
- **Security/Auth**: HashGuard (PoW verification), no bcrypt/argon2 found
- **Validation**: class-validator, class-transformer
- **Caching**: Redis + Keyv
- **Testing**: Jest

## Key Entities & Database
- **Main entity**: `NoticeArchive` (not separate Notice)
- **Location**: [backend/src/modules/notice/notice-archive.entity.ts](backend/src/modules/notice/notice-archive.entity.ts)
- **Other entities**:
  - NoticeChangeEvent (change tracking)
  - NoticeChangeDetail (change tracking)
  - WebPushSubscription (notifications)
  - Webhook (webhook management)
  - NoticeArchiveIntegrityCheck, NoticeArchiveIntegrityState, NoticeArchiveSnapshotState

## Database Setup Pattern
- Migrations use TypeORM's MigrationInterface
- Naming: `YYYYMMDDHHH-description.migration.ts`
- All migrations imported and exported in [backend/src/migrations/index.ts](backend/src/migrations/index.ts)
- Applied automatically on startup via [backend/src/main.ts](backend/src/main.ts)
- Raw SQL queries in migrations (CREATE TABLE, ALTER TABLE, etc.)

## Controllers & Routes
- Main controller: [backend/src/controllers/api.controller.ts](backend/src/controllers/api.controller.ts)
- Stats controller: [backend/src/controllers/api-proposal-stats.controller.ts](backend/src/controllers/api-proposal-stats.controller.ts)
- All routes under `/api` prefix
- Key routes: `/notices/recent`, `/notices/archive`, `/notices/search`, `/notices/:num/detail`, `/notices/:num/changes`

## Security/Auth Utilities
- **HashGuard**: [backend/src/modules/shared/hashguard.service.ts](backend/src/modules/shared/hashguard.service.ts) - PoW verification
- **Response formatting**: [backend/src/utils/api-response.utils.ts](backend/src/utils/api-response.utils.ts)
- **IP extraction**: Check Req object in controllers (Express request)
- **Request validation**: class-validator DTOs
- No bcrypt/argon2 found (uses HashGuard instead)

## Module Structure Pattern
- Each feature in `backend/src/modules/{feature}/`
- Module file exports providers, services, entities
- TypeOrmModule.forFeature() registers entities
- Example: [backend/src/modules/notice/notice.module.ts](backend/src/modules/notice/notice.module.ts)
- Shared services in [backend/src/modules/shared/](backend/src/modules/shared/)

## Services Pattern
- Services are Injectable() providers
- Injected via constructor DI
- Database queries via TypeORM Repository (InjectRepository decorator)
- Example: NoticeArchiveService in [backend/src/modules/notice/notice-archive.service.ts](backend/src/modules/notice/notice-archive.service.ts)

## Comments History
- **Removed**: Migration `20260416_drop_notice_num_comments.sql` dropped the `numComments` column from `notice_archives`
- **Result**: Comment tracking is now removed from the data model
- **Cache type**: [backend/src/types/cache.types.ts](backend/src/types/cache.types.ts) shows `numComments` explicitly omitted: `type CachedBaseNotice = Omit<ITableData, 'numComments'>`

## Proxy & IP Handling (IMPORTANT)
- **Client IP extraction**: [backend/src/utils/webhook-validation.utils.ts](backend/src/utils/webhook-validation.utils.ts#L84-L89)
  - **Order**: `req.ip` → `req.connection?.remoteAddress` → `req.headers['x-forwarded-for']` → `'unknown'`
  - Used for webhook and web-push registration IP logging
- **Trust proxy config**: **NOT SET in main.ts**
  - No `app.set('trust proxy', ...)` call
  - CORS enabled with `origin: frontendUrls` and `credentials: true`
  - Behind Cloudflare/Nginx, Express won't parse `X-Forwarded-For` → `req.ip` without explicit trust proxy config
  - **Consequence**: Behind proxy, `req.ip` will be the proxy's IP, not client IP. Falls back to header check.

## Rate Limiting
- **Webhook rate limiting**: [backend/src/modules/notification/notification.service.ts](backend/src/modules/notification/notification.service.ts#L82-L96)
  - Cache keys: `rate_limit:global` (30s), `rate_limit:webhook:{id}` (30s), `rate_limit:per_source:{id}` (1h)
  - Stored in Redis cache
  - Applied to notification delivery, not API endpoints
- **API rate limiting**: None globally; relies on upstream proxy (Cloudflare/Nginx)

## Where to Add Comments/Discussions Module (If Needed)
1. Create `backend/src/modules/comments/`
2. Create entities: `discussion.entity.ts`, `comment.entity.ts`
3. Create services: `discussion.service.ts`, `comment.service.ts`
4. Create `comments.module.ts` with TypeOrmModule.forFeature()
5. Add to AppModule imports in [backend/src/app.module.ts](backend/src/app.module.ts)
6. Add migration for new tables in `backend/src/migrations/`
7. Import & export migration in [backend/src/migrations/index.ts](backend/src/migrations/index.ts)

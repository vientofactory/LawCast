# Renovate and npm Inventory

Captured on 2026-11-07 (Asia/Tokyo). Current/wanted/latest refer to the baseline inventory.

## backend

### Open Renovate PRs

- [199: chore(deps): update dependency eslint-plugin-prettier to v5.5.7](https://github.com/vientofactory/LawCast-Backend/pull/199); base `dev`.
- [184: fix(deps): update dependency keyv to v6](https://github.com/vientofactory/LawCast-Backend/pull/184); base `dev`.
- [183: fix(deps): update dependency @keyv/redis to v6](https://github.com/vientofactory/LawCast-Backend/pull/183); base `dev`.
- [179: chore(deps): update dependency cronstrue to v3.38.0](https://github.com/vientofactory/LawCast-Backend/pull/179); base `dev`.
- [177: chore(deps): update dependency eslint to v10.14.0](https://github.com/vientofactory/LawCast-Backend/pull/177); base `dev`.
- [175: chore(deps): update dependency supertest to v7.3.1](https://github.com/vientofactory/LawCast-Backend/pull/175); base `dev`.
- [173: chore(deps): update nest monorepo to v11.2.8](https://github.com/vientofactory/LawCast-Backend/pull/173); base `dev`.
- [172: chore(deps): update typescript-eslint monorepo to v8.72.1](https://github.com/vientofactory/LawCast-Backend/pull/172); base `dev`.
- [168: chore(deps): update dependency sharp to v0.35.5](https://github.com/vientofactory/LawCast-Backend/pull/168); base `dev`.
- [167: chore(deps): update dependency @types/node to v24.19.2](https://github.com/vientofactory/LawCast-Backend/pull/167); base `dev`.

### All baseline outdated packages

- `@keyv/redis`: current `5.1.6`, wanted `5.1.6`, latest `6.1.0`.
- `@nestjs/cache-manager`: current `3.1.3`, wanted `3.1.3`, latest `12.0.4`.
- `@nestjs/cli`: current `11.0.24`, wanted `11.0.24`, latest `12.0.12`.
- `@nestjs/common`: current `11.2.6`, wanted `11.2.8`, latest `12.4.0`.
- `@nestjs/config`: current `4.0.4`, wanted `4.0.4`, latest `12.1.1`.
- `@nestjs/core`: current `11.2.6`, wanted `11.2.8`, latest `12.4.0`.
- `@nestjs/platform-express`: current `11.2.6`, wanted `11.2.8`, latest `12.4.0`.
- `@nestjs/schedule`: current `6.1.3`, wanted `6.1.3`, latest `12.0.3`.
- `@nestjs/schematics`: current `11.1.0`, wanted `11.1.0`, latest `12.0.13`.
- `@nestjs/testing`: current `11.2.6`, wanted `11.2.8`, latest `12.4.0`.
- `@nestjs/typeorm`: current `11.0.3`, wanted `11.0.3`, latest `12.0.3`.
- `@notionhq/client`: current `5.27.0`, wanted `5.31.0`, latest `5.31.0`.
- `@types/node`: current `24.13.6`, wanted `24.19.2`, latest `26.6.6`.
- `@typescript-eslint/eslint-plugin`: current `8.70.1`, wanted `8.72.1`, latest `8.72.1`.
- `@typescript-eslint/parser`: current `8.70.1`, wanted `8.72.1`, latest `8.72.1`.
- `axios`: current `1.20.0`, wanted `1.21.0`, latest `1.21.0`.
- `cronstrue`: current `3.27.0`, wanted `3.38.0`, latest `3.38.0`.
- `discord.js`: current `14.27.0`, wanted `14.28.1`, latest `14.28.1`.
- `eslint`: current `10.11.0`, wanted `10.14.0`, latest `10.14.0`.
- `eslint-plugin-prettier`: current `5.5.6`, wanted `5.5.7`, latest `5.5.7`.
- `keyv`: current `5.6.0`, wanted `5.6.0`, latest `6.1.0`.
- `pal-crawl`: current `2.3.0`, wanted `2.3.1`, latest `2.3.1`.
- `prettier`: current `3.9.9`, wanted `3.9.10`, latest `3.9.10`.
- `sharp`: current `0.35.4`, wanted `0.35.5`, latest `0.35.5`.
- `supertest`: current `7.3.0`, wanted `7.3.1`, latest `7.3.1`.
- `ts-jest`: current `29.4.14`, wanted `29.4.15`, latest `29.4.15`.
- `typeorm`: current `0.3.31`, wanted `0.3.31`, latest `1.1.2`.
- `typescript`: current `5.9.3`, wanted `5.9.3`, latest `7.0.2`.
- `web-push`: current `3.6.7`, wanted `3.6.7`, latest `4.0.0`.

### Retained major upgrades

- `@keyv/redis`: retained `5.1.6`, latest `6.1.0`; within-range wanted `5.1.6` is installed.
- `@nestjs/cache-manager`: retained `3.1.3`, latest `12.0.4`; within-range wanted `3.1.3` is installed.
- `@nestjs/cli`: retained `11.0.24`, latest `12.0.12`; within-range wanted `11.0.24` is installed.
- `@nestjs/common`: retained `11.2.8`, latest `12.4.0`; within-range wanted `11.2.8` is installed.
- `@nestjs/config`: retained `4.0.4`, latest `12.1.1`; within-range wanted `4.0.4` is installed.
- `@nestjs/core`: retained `11.2.8`, latest `12.4.0`; within-range wanted `11.2.8` is installed.
- `@nestjs/platform-express`: retained `11.2.8`, latest `12.4.0`; within-range wanted `11.2.8` is installed.
- `@nestjs/schedule`: retained `6.1.3`, latest `12.0.3`; within-range wanted `6.1.3` is installed.
- `@nestjs/schematics`: retained `11.1.0`, latest `12.0.13`; within-range wanted `11.1.0` is installed.
- `@nestjs/testing`: retained `11.2.8`, latest `12.4.0`; within-range wanted `11.2.8` is installed.
- `@nestjs/typeorm`: retained `11.0.3`, latest `12.0.3`; within-range wanted `11.0.3` is installed.
- `@types/node`: retained `24.19.2`, latest `26.6.6`; within-range wanted `24.19.2` is installed.
- `keyv`: retained `5.6.0`, latest `6.1.0`; within-range wanted `5.6.0` is installed.
- `typeorm`: retained `0.3.31`, latest `1.1.2`; within-range wanted `0.3.31` is installed.
- `typescript`: retained `5.9.3`, latest `7.0.2`; within-range wanted `5.9.3` is installed.
- `web-push`: retained `3.6.7`, latest `4.0.0`; within-range wanted `3.6.7` is installed.

## frontend

### Open Renovate PRs

- [123: chore(deps): update dependency typescript-eslint to v8.72.1](https://github.com/vientofactory/LawCast-Frontend/pull/123); base `dev`.
- [122: chore(deps): update dependency svelte to v5.57.3](https://github.com/vientofactory/LawCast-Frontend/pull/122); base `dev`.
- [121: chore(deps): update dependency globals to v17.14.0](https://github.com/vientofactory/LawCast-Frontend/pull/121); base `dev`.
- [120: chore(deps): update dependency eslint-plugin-svelte to v3.24.0](https://github.com/vientofactory/LawCast-Frontend/pull/120); base `dev`.
- [119: chore(deps): update dependency eslint to v10.14.0](https://github.com/vientofactory/LawCast-Frontend/pull/119); base `dev`.
- [118: chore(deps): update dependency axios to v1.21.0](https://github.com/vientofactory/LawCast-Frontend/pull/118); base `dev`.
- [116: chore(deps): update dependency @playwright/test to v1.65.0](https://github.com/vientofactory/LawCast-Frontend/pull/116); base `dev`.
- [115: chore(deps): update dependency prettier to v3.9.10](https://github.com/vientofactory/LawCast-Frontend/pull/115); base `dev`.
- [110: chore(deps): update dependency @types/node to v24.19.2](https://github.com/vientofactory/LawCast-Frontend/pull/110); base `dev`.
- [109: chore(deps): update dependency @eslint/compat to v2.1.1](https://github.com/vientofactory/LawCast-Frontend/pull/109); base `dev`.

### All baseline outdated packages

- `@eslint/compat`: current `2.1.0`, wanted `2.1.1`, latest `2.1.1`.
- `@fortawesome/fontawesome-svg-core`: current `7.3.0`, wanted `7.3.1`, latest `7.3.1`.
- `@fortawesome/free-brands-svg-icons`: current `7.3.0`, wanted `7.3.1`, latest `7.3.1`.
- `@fortawesome/free-solid-svg-icons`: current `7.3.0`, wanted `7.3.1`, latest `7.3.1`.
- `@playwright/test`: current `1.62.1`, wanted `1.65.0`, latest `1.65.0`.
- `@sveltejs/adapter-cloudflare`: current `7.2.9`, wanted `7.2.10`, latest `8.0.2`.
- `@sveltejs/adapter-node`: current `5.5.7`, wanted `5.5.8`, latest `6.0.1`.
- `@sveltejs/kit`: current `2.70.3`, wanted `2.70.4`, latest `3.1.1`.
- `@sveltejs/vite-plugin-svelte`: current `6.2.4`, wanted `6.2.4`, latest `7.3.1`.
- `@tailwindcss/vite`: current `4.3.2`, wanted `4.3.5`, latest `4.3.5`.
- `@types/node`: current `24.13.3`, wanted `24.19.2`, latest `26.6.6`.
- `axios`: current `1.18.1`, wanted `1.21.0`, latest `1.21.0`.
- `chart.js`: current `4.5.1`, wanted `4.6.1`, latest `4.6.1`.
- `chrome-launcher`: current `1.2.2`, wanted `1.2.2`, latest `1.2.3`.
- `eslint`: current `10.7.0`, wanted `10.14.0`, latest `10.14.0`.
- `eslint-plugin-svelte`: current `3.20.0`, wanted `3.24.0`, latest `3.24.0`.
- `globals`: current `17.7.0`, wanted `17.14.0`, latest `17.14.0`.
- `marked`: current `18.1.0`, wanted `18.1.3`, latest `18.1.3`.
- `prettier`: current `3.9.5`, wanted `3.9.10`, latest `3.9.10`.
- `prettier-plugin-tailwindcss`: current `0.8.0`, wanted `0.8.1`, latest `0.8.1`.
- `svelte`: current `5.56.4`, wanted `5.57.3`, latest `5.57.3`.
- `svelte-check`: current `4.7.2`, wanted `4.7.8`, latest `4.7.8`.
- `tailwindcss`: current `4.3.2`, wanted `4.3.5`, latest `4.3.5`.
- `typescript`: current `6.0.3`, wanted `6.0.3`, latest `7.0.2`.
- `typescript-eslint`: current `8.64.0`, wanted `8.72.1`, latest `8.72.1`.
- `vite`: current `7.3.6`, wanted `7.3.7`, latest `8.3.6`.
- `wrangler`: current `4.131.0`, wanted `4.131.0`, latest `4.158.0`.

### Retained major upgrades

- `@sveltejs/adapter-cloudflare`: retained `7.2.10`, latest `8.0.2`; within-range wanted `7.2.10` is installed.
- `@sveltejs/adapter-node`: retained `5.5.8`, latest `6.0.1`; within-range wanted `5.5.8` is installed.
- `@sveltejs/kit`: retained `2.70.4`, latest `3.1.1`; within-range wanted `2.70.4` is installed.
- `@sveltejs/vite-plugin-svelte`: retained `6.2.4`, latest `7.3.1`; within-range wanted `6.2.4` is installed.
- `@types/node`: retained `24.19.2`, latest `26.6.6`; within-range wanted `24.19.2` is installed.
- `typescript`: retained `6.0.3`, latest `7.0.2`; within-range wanted `6.0.3` is installed.
- `vite`: retained `7.3.7`, latest `8.3.6`; within-range wanted `7.3.7` is installed.

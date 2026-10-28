const { createRequire } = require("node:module");
const Module = require("node:module");
const path = require("node:path");
const fs = require("node:fs");
const { execFileSync } = require("node:child_process");
const { performance } = require("node:perf_hooks");
const cwd = process.cwd();
const benchmarkDb = process.env.LAWCAST_BENCH_DB;
if (
  !benchmarkDb ||
  fs.realpathSync(benchmarkDb) === fs.realpathSync(path.join(cwd, "lawcast.db"))
)
  throw new Error(
    "LAWCAST_BENCH_DB must be a disposable SQLite backup, never the source database",
  );
const outputPath =
  process.env.LAWCAST_BENCH_OUTPUT || "/tmp/lawcast-shared-db-benchmark.json";
const req = createRequire(path.join(cwd, "package.json"));
req("ts-node/register/transpile-only");
const ts = req("typescript");
const { DataSource } = req("typeorm");
const sqlite3 = req("sqlite3");
const sourcePath = path.join(
  cwd,
  "src/modules/notice/notice-archive.service.ts",
);
const old = new Module(sourcePath + ".baseline", module);
old.filename = sourcePath;
old.paths = Module._nodeModulePaths(path.dirname(sourcePath));
old._compile(
  ts.transpileModule(
    execFileSync(
      "git",
      ["show", "backend-v1.19.5:src/modules/notice/notice-archive.service.ts"],
      { encoding: "utf8" },
    ),
    {
      compilerOptions: {
        target: ts.ScriptTarget.ES2021,
        module: ts.ModuleKind.CommonJS,
        experimentalDecorators: true,
        emitDecoratorMetadata: true,
      },
    },
  ).outputText,
  sourcePath,
);
const classes = {
  baseline: old.exports.NoticeArchiveService,
  patched: req(sourcePath).NoticeArchiveService,
};
const { OptimizeArchiveMetadataUpdates1793145601000 } = req(
  path.join(
    cwd,
    "src/migrations/202610280001-optimize-archive-metadata-updates.migration.ts",
  ),
);
const entities = [
  ["notice-archive.entity", "NoticeArchive"],
  ["notice-archive-summary-state.entity", "NoticeArchiveSnapshotState"],
  ["notice-archive-integrity-check.entity", "NoticeArchiveIntegrityCheck"],
  ["notice-archive-integrity-state.entity", "NoticeArchiveIntegrityState"],
].map(([f, n]) => req(path.join(cwd, "src/modules/notice", f + ".ts"))[n]);
(async () => {
  const source = new DataSource({
    type: "sqlite",
    database: path.join(cwd, "lawcast.db"),
    flags: sqlite3.OPEN_READONLY,
  });
  await source.initialize();
  const original = (
    await source.query(
      "SELECT sql FROM sqlite_master WHERE name='trg_notice_archives_prevent_update'",
    )
  )[0].sql;
  await source.destroy();
  const results = [];
  for (const arm of [
    "baseline",
    "patched",
    "patched",
    "baseline",
    "baseline",
    "patched",
  ]) {
    let notify;
    const started = new Promise((r) => (notify = r));
    const db = new DataSource({
      type: "sqlite",
      database: benchmarkDb,
      entities,
      synchronize: false,
      logging: ["query"],
      logger: {
        logQuery(sql) {
          if (sql.startsWith('UPDATE "notice_archives"')) notify();
        },
        logQueryError() {},
        logQuerySlow() {},
        logSchemaBuild() {},
        logMigration() {},
        log() {},
      },
    });
    await db.initialize();
    await db.query("PRAGMA synchronous=NORMAL");
    await db.query("DROP TRIGGER trg_notice_archives_prevent_update");
    await db.query(original);
    if (arm === "patched")
      await new OptimizeArchiveMetadataUpdates1793145601000().up(
        db.createQueryRunner(),
      );
    const ids = (
      await db.query(
        "SELECT noticeNum FROM notice_archives ORDER BY noticeNum DESC LIMIT 2000",
      )
    ).map((r) => r.noticeNum);
    const repo = db.getRepository(entities[0]);
    const service = new classes[arm](
      repo,
      db.getRepository(entities[1]),
      {},
      {},
      db.getRepository(entities[2]),
      db.getRepository(entities[3]),
    );
    const stamp = new Date(
      Date.now() + 365 * 86400000 + results.length * 60000,
    );
    const t = performance.now();
    const writing = service
      .stampNsmListSeen(ids, stamp)
      .then((count) => ({ count, writeMs: performance.now() - t }));
    await started;
    const readMs = [];
    for (let i = 0; i < 40; i++) {
      const s = performance.now();
      await db.query("SELECT COUNT(*) AS count FROM notice_archives");
      readMs.push(performance.now() - s);
      await new Promise((r) => setTimeout(r, 1));
    }
    const write = await writing;
    readMs.sort((a, b) => a - b);
    const persisted = (
      await db.query(
        "SELECT COUNT(*) AS count FROM notice_archives WHERE nsm_last_seen_in_list_at=?",
        [stamp.toISOString().replace("T", " ").replace("Z", "")],
      )
    )[0].count;
    const row = {
      arm,
      ...write,
      persisted,
      p50: readMs[19],
      p95: readMs[37],
      max: readMs[39],
      reads: readMs,
    };
    results.push(row);
    console.log(JSON.stringify(row));
    await db.destroy();
  }
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});

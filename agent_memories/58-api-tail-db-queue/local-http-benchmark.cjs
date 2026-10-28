const { createRequire } = require("node:module");
const Module = require("node:module");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { createServer } = require("node:http");
const { performance } = require("node:perf_hooks");
const cwd = path.resolve(__dirname, "../../backend");
process.chdir(cwd);
const req = createRequire(path.join(cwd, "package.json"));
req("ts-node/register/transpile-only");
const ts = req("typescript");
const { DataSource } = req("typeorm");
const sqlite3 = req("sqlite3");
const sourcePath = path.join(
  cwd,
  "src/modules/notice/utils/notice-archive-maintenance-support.ts",
);
const source = execFileSync(
  "git",
  [
    "show",
    "backend-v1.19.4:src/modules/notice/utils/notice-archive-maintenance-support.ts",
  ],
  { cwd, encoding: "utf8" },
);
const old = new Module(sourcePath + ".baseline", module);
old.filename = sourcePath;
old.paths = Module._nodeModulePaths(path.dirname(sourcePath));
old._compile(
  ts.transpileModule(source, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2021,
      module: ts.ModuleKind.CommonJS,
    },
  }).outputText,
  sourcePath,
);
const methods = {
  baseline: old.exports.getProposalReasonRetryCandidates,
  patched: req(sourcePath).getProposalReasonRetryCandidates,
};
const entities = [
  ["notice-archive.entity", "NoticeArchive"],
  ["notice-archive-summary-state.entity", "NoticeArchiveSnapshotState"],
  ["notice-archive-integrity-check.entity", "NoticeArchiveIntegrityCheck"],
  ["notice-archive-integrity-state.entity", "NoticeArchiveIntegrityState"],
].map(
  ([file, name]) =>
    req(path.join(cwd, "src/modules/notice", file + ".ts"))[name],
);
(async () => {
  const results = [];
  for (const arm of ["baseline", "patched", "patched", "patched"]) {
    let release;
    const queryStarted = new Promise((r) => (release = r));
    let candidateSql;
    const ds = new DataSource({
      type: "sqlite",
      database: path.join(cwd, "lawcast.db"),
      flags: sqlite3.OPEN_READONLY,
      entities,
      synchronize: false,
      migrationsRun: false,
      logging: ["query"],
      logger: {
        logQuery: (sql, params) => {
          if (sql.includes("FROM notice_change_events e")) {
            candidateSql = { sql, params };
            release();
          }
        },
        logQueryError() {},
        logQuerySlow() {},
        logSchemaBuild() {},
        logMigration() {},
        log() {},
      },
    });
    await ds.initialize();
    const repo = ds.getRepository(entities[0]);
    const deps = {
      archiveRepository: repo,
      summaryStateRepository: ds.getRepository(entities[1]),
      logger: console,
    };
    const server = createServer(async (request, response) => {
      try {
        let data;
        if (request.url === "/api/version") data = { version: "1.19.4" };
        else if (request.url === "/api/stats") {
          const [archive, events] = await Promise.all([
            repo.count(),
            ds.query(
              "SELECT COUNT(DISTINCT notice_num) AS count FROM notice_change_events WHERE event_height>1",
            ),
          ]);
          data = { archive, events: events[0].count };
        } else
          data = await ds.query(
            "SELECT COUNT(*) AS count FROM discussion_threads",
          );
        response.setHeader("content-type", "application/json");
        response.end(JSON.stringify({ success: true, data }));
      } catch (e) {
        response.statusCode = 500;
        response.end(JSON.stringify({ error: e.message }));
      }
    });
    await new Promise((r) => server.listen(0, "127.0.0.1", r));
    const base = "http://127.0.0.1:" + server.address().port;
    const start = performance.now();
    const task = methods[arm](deps, 20);
    await queryStarted;
    await new Promise((r) => setTimeout(r, 10));
    const samples = await Promise.all(
      ["/api/version", "/api/stats", "/api/discussions/threads"].map(
        async (endpoint) => {
          const started = performance.now();
          const r = await fetch(base + endpoint);
          const body = await r.json();
          return {
            endpoint,
            status: r.status,
            ms: performance.now() - started,
            body,
          };
        },
      ),
    );
    const candidates = await task;
    const candidateMs = performance.now() - start;
    const plan = await ds.query(
      "EXPLAIN QUERY PLAN " + candidateSql.sql,
      candidateSql.params,
    );
    results.push({
      arm,
      candidateAndRequestsMs: candidateMs,
      candidates: candidates.map((v) => v.notice.num),
      samples,
      plan,
    });
    await new Promise((r) => server.close(r));
    await ds.destroy();
    fs.writeFileSync(
      process.env.LAWCAST_DIAGNOSTIC_OUTPUT ||
        path.join(
          require("node:os").tmpdir(),
          "lawcast-retry-query-benchmark.json",
        ),
      JSON.stringify({ sqliteVersion: sqlite3.VERSION, results }, null, 2),
    );
    console.log(
      arm,
      Math.round(candidateMs),
      samples.map((v) => [v.endpoint, Math.round(v.ms), v.status]),
    );
  }
  if (
    results.some(
      (v) =>
        JSON.stringify(v.candidates) !== JSON.stringify(results[0].candidates),
    )
  )
    throw Error("candidate result mismatch");
  for (const r of results)
    for (const s of r.samples)
      if (s.status !== 200) throw Error("HTTP failure");
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});

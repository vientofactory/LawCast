const assert: typeof import("node:assert/strict") = require("node:assert/strict");
const {
  spawnSync,
}: typeof import("node:child_process") = require("node:child_process");
const {
  mkdtempSync,
  mkdirSync,
  rmSync,
  writeFileSync,
}: typeof import("node:fs") = require("node:fs");
const { tmpdir }: typeof import("node:os") = require("node:os");
const { dirname, join }: typeof import("node:path") = require("node:path");
const test: typeof import("node:test").test = require("node:test").test;

const checker = join(__dirname, "check-agent-guidelines.py");
function checkSource(relativePath: string) {
  const directory = mkdtempSync(join(tmpdir(), "lawcast-test-source-"));
  try {
    const file = join(directory, relativePath);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, "export {};\n");
    return spawnSync("python3", [checker, "--only=T2", file], {
      encoding: "utf8",
    });
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

test("rejects standalone JavaScript and explicit ESM TypeScript test sources", () => {
  for (const file of [
    "frontend/scripts/example.test.mjs",
    "frontend/scripts/example.test.js",
    "frontend/scripts/example.spec.mts",
    "backend/test/example.cjs",
    "frontend/e2e/fixtures/backend.mjs",
    "frontend-mcp/test/example.js",
  ]) {
    const result = checkSource(file);
    assert.equal(result.status, 1, file);
    assert.match(result.stdout, /T2 .*TypeScript/);
  }
});

test("accepts TypeScript suites and fixtures using their package module system", () => {
  for (const file of [
    "frontend/scripts/example.test.ts",
    "frontend/e2e/fixtures/backend.ts",
    "backend/test/example.spec.ts",
    "frontend-mcp/test/example.test.ts",
  ]) {
    assert.equal(checkSource(file).status, 0, file);
  }
});

test("preserves runtime modules, generated JavaScript and vendored upstream tests", () => {
  for (const file of [
    "frontend/scripts/runtime.mjs",
    "backend/jest.config.cjs",
    "frontend-mcp/dist/test/example.test.js",
    "frontend/vendor/deepmerge/security.test.cjs",
  ]) {
    assert.equal(checkSource(file).status, 0, file);
  }
});

import { spawn } from "node:child_process";

const host = "127.0.0.1";
const port = Number(process.env.DESIGNBENCH_SMOKE_PORT || 4173);
const timeoutMs = Number(process.env.DESIGNBENCH_SMOKE_TIMEOUT_MS || 60000);
const url = `http://${host}:${port}/`;

const child = spawn(
  process.platform === "win32" ? "npm.cmd" : "npm",
  ["run", "dev", "--", "--hostname", host, "--port", String(port)],
  {
    detached: process.platform !== "win32",
    env: {
      ...process.env,
      NEXT_TELEMETRY_DISABLED: "1",
      WATCHPACK_POLLING: "true"
    },
    stdio: ["ignore", "pipe", "pipe"]
  }
);

let output = "";
child.stdout.on("data", chunk => { output += chunk.toString(); });
child.stderr.on("data", chunk => { output += chunk.toString(); });

async function stop() {
  if (child.exitCode !== null) return;
  if (process.platform === "win32") child.kill("SIGTERM");
  else process.kill(-child.pid, "SIGTERM");
}

const deadline = Date.now() + timeoutMs;
try {
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Next.js exited before serving the page (code ${child.exitCode})\n${output}`);
    }
    try {
      const response = await fetch(url);
      const body = await response.text();
      if (response.ok && !body.includes("__next_error__")) {
        console.log(`render smoke passed: HTTP ${response.status}, ${body.length} bytes`);
        process.exitCode = 0;
        break;
      }
      if (response.status >= 500) {
        throw new Error(`page returned HTTP ${response.status}\n${body.slice(0, 2000)}\n${output}`);
      }
    } catch (error) {
      if (String(error).includes("page returned HTTP")) throw error;
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  if (process.exitCode !== 0) {
    throw new Error(`timed out waiting for ${url}\n${output}`);
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
} finally {
  await stop();
}

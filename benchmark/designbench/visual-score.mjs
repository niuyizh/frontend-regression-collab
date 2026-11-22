import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { chromium } from "playwright";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) {
      throw new Error("arguments must be --workspace DIR --target FILE --output DIR [--port N]");
    }
    values[key.slice(2)] = value;
  }
  for (const required of ["workspace", "target", "output"]) {
    if (!values[required]) throw new Error(`missing --${required}`);
  }
  return values;
}

async function runTaskChecks(page, taskId) {
  if (!taskId) return null;
  return page.evaluate(id => {
    const rect = element => element?.getBoundingClientRect();
    const style = element => element ? window.getComputedStyle(element) : null;
    const close = (left, right, tolerance = 4) =>
      Number.isFinite(left) && Number.isFinite(right) && Math.abs(left - right) <= tolerance;
    const checks = {};

    if (id === "db-e01") {
      const first = document.querySelector('input[aria-label="Doctor\'s first name"]');
      const last = document.querySelector('input[aria-label="Doctor\'s last name"]');
      const full = document.querySelector('input[aria-label="Doctor\'s full name"]');
      const image = document.querySelector("img");
      const heading = document.querySelector("h2");
      checks.separate_name_fields = Boolean(first && last && !full);
      checks.name_fields_share_row = Boolean(first && last && close(rect(first).top, rect(last).top));
      checks.title_is_below_photo = Boolean(
        image && heading && rect(heading).top >= rect(image).bottom - 2,
      );
    } else if (id === "db-e11") {
      const legend = [...document.querySelectorAll("legend")]
        .find(element => element.textContent?.trim() === "Delivery Schedule");
      const immediate = document.querySelector('input[type="radio"][value="immediately"]');
      const specific = document.querySelector('input[type="radio"][value="specificTime"]');
      checks.image_field_present = Boolean(document.querySelector('input[type="file"]'));
      checks.delivery_group_present = Boolean(legend && legend.closest("fieldset"));
      checks.both_schedule_options_present = Boolean(immediate && specific);
      checks.datetime_field_present = Boolean(document.querySelector('input[type="datetime-local"]'));
    } else if (id === "db-e27" || id === "db-e30") {
      const right = document.querySelector(".col-span-2");
      const toolbar = right?.firstElementChild;
      const buttons = toolbar ? [...toolbar.querySelectorAll("button")] : [];
      const toolbarStyle = style(toolbar);
      checks.toolbar_is_sticky = toolbarStyle?.position === "sticky" && parseFloat(toolbarStyle.top) === 0;
      checks.toolbar_options_preserved = buttons.length === 5 && buttons.every(button => button.querySelector("svg"));

      if (id === "db-e27") {
        const sidebarRow = document.querySelector(".grid > div:first-child li");
        const sender = sidebarRow?.querySelector("h2");
        const date = sidebarRow?.querySelector("time");
        checks.toolbar_has_bottom_border = parseFloat(toolbarStyle?.borderBottomWidth || "0") > 0;
        checks.toolbar_is_icon_only = buttons.length === 5 && buttons.every(
          button => button.textContent?.trim() === "",
        );
        checks.search_is_last = Boolean(buttons.at(-1)?.querySelector("circle"));
        checks.date_is_right_of_sender = Boolean(
          sender && date && rect(date).left > rect(sender).right,
        );
      } else {
        const directButtons = toolbar ? [...toolbar.children].filter(
          element => element.tagName === "BUTTON",
        ) : [];
        const leading = directButtons.slice(0, 4).map(element => rect(element));
        checks.four_primary_buttons_are_direct_neighbors = directButtons.length === 4;
        checks.toolbar_buttons_have_no_border = buttons.length === 5 && buttons.every(
          button => parseFloat(style(button).borderTopWidth) === 0,
        );
        checks.primary_buttons_have_no_gap = leading.length === 4 && leading.slice(1).every(
          (box, index) => close(box.left, leading[index].right, 1),
        );
        const requiredText = ["Inbox", "Flagged", "All Sent", "Work", "Expenses", "Personal", "Meeting Tomorrow"];
        checks.unrelated_content_preserved = requiredText.every(text => document.body.innerText.includes(text));
      }
    }
    return checks;
  }, taskId);
}

async function stop(child) {
  if (child.exitCode !== null) return;
  if (process.platform === "win32") child.kill("SIGTERM");
  else process.kill(-child.pid, "SIGTERM");
}

async function waitForPage(url, child, getOutput, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Next.js exited before scoring (code ${child.exitCode})\n${getOutput()}`);
    }
    try {
      const response = await fetch(url);
      if (response.ok) return;
      if (response.status >= 500) {
        const body = await response.text();
        throw new Error(`page returned HTTP ${response.status}\n${body.slice(0, 2000)}`);
      }
    } catch (error) {
      if (String(error).includes("page returned HTTP")) throw error;
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error(`timed out waiting for ${url}\n${getOutput()}`);
}

function imageMetrics(reference, candidate, diff) {
  if (reference.width !== candidate.width || reference.height !== candidate.height) {
    throw new Error(
      `screenshot size mismatch: target=${reference.width}x${reference.height}, ` +
      `candidate=${candidate.width}x${candidate.height}`,
    );
  }
  const pixels = reference.width * reference.height;
  const changed = pixelmatch(
    reference.data,
    candidate.data,
    diff.data,
    reference.width,
    reference.height,
    { threshold: 0.1, includeAA: false },
  );
  let absoluteError = 0;
  for (let offset = 0; offset < reference.data.length; offset += 4) {
    absoluteError += Math.abs(reference.data[offset] - candidate.data[offset]);
    absoluteError += Math.abs(reference.data[offset + 1] - candidate.data[offset + 1]);
    absoluteError += Math.abs(reference.data[offset + 2] - candidate.data[offset + 2]);
  }
  return {
    width: reference.width,
    height: reference.height,
    changed_pixels: changed,
    pixel_similarity: 1 - changed / pixels,
    normalized_mae: absoluteError / (pixels * 3 * 255),
    mae_similarity: 1 - absoluteError / (pixels * 3 * 255),
  };
}

const args = parseArgs(process.argv.slice(2));
const workspace = path.resolve(args.workspace);
const targetPath = path.resolve(args.target);
const outputDir = path.resolve(args.output);
const port = Number(args.port || "4673");
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error("invalid --port");
await fs.mkdir(outputDir, { recursive: true });

let serverOutput = "";
const child = spawn(
  process.platform === "win32" ? "npm.cmd" : "npm",
  ["run", "dev", "--", "--hostname", "127.0.0.1", "--port", String(port)],
  {
    cwd: workspace,
    detached: process.platform !== "win32",
    env: {
      ...process.env,
      NEXT_TELEMETRY_DISABLED: "1",
      WATCHPACK_POLLING: "true",
    },
    stdio: ["ignore", "pipe", "pipe"],
  },
);
child.stdout.on("data", chunk => { serverOutput += chunk.toString(); });
child.stderr.on("data", chunk => { serverOutput += chunk.toString(); });

let browser;
try {
  const url = `http://127.0.0.1:${port}/`;
  await waitForPage(url, child, () => serverOutput);
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1792, height: 925 },
    deviceScaleFactor: 2,
    colorScheme: "light",
  });
  const page = await context.newPage();
  await page.goto(url, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  const checks = await runTaskChecks(page, args.task);
  const screenshotPath = path.join(outputDir, "candidate.png");
  await page.screenshot({ path: screenshotPath, fullPage: false, animations: "disabled" });
  await context.close();

  const reference = PNG.sync.read(await fs.readFile(targetPath));
  const candidate = PNG.sync.read(await fs.readFile(screenshotPath));
  const diff = new PNG({ width: reference.width, height: reference.height });
  const metrics = imageMetrics(reference, candidate, diff);
  await fs.writeFile(path.join(outputDir, "diff.png"), PNG.sync.write(diff));
  const result = {
    schema_version: 1,
    workspace,
    target: targetPath,
    screenshot: screenshotPath,
    diff: path.join(outputDir, "diff.png"),
    checks,
    structural_passed: checks ? Object.values(checks).every(Boolean) : null,
    ...metrics,
  };
  await fs.writeFile(
    path.join(outputDir, "visual-score.json"),
    `${JSON.stringify(result, null, 2)}\n`,
  );
  console.log(JSON.stringify(result));
} finally {
  if (browser) await browser.close();
  await stop(child);
  await fs.writeFile(path.join(outputDir, "next.log"), serverOutput);
}

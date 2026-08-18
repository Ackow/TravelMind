import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUTPUT_DIR = "f:/Project/TravelMind/frontend/tests";
const ARTIFACTS_DIR = "C:/Users/IceCola/.gemini/antigravity/brain/713259ef-35ed-4d4f-8e01-3992223871c8";

const PAGES_TO_TEST = [
  {
    name: "history",
    url: "http://localhost:3000/trips/history",
    refPath: "f:/Project/TravelMind/参考图/计划版本历史.png",
    actualFile: "actual-history.png",
    diffFile: "diff-history.png",
  },
  {
    name: "final",
    url: "http://localhost:3000/trips/final",
    refPath: "f:/Project/TravelMind/参考图/最终行程.png",
    actualFile: "actual-final.png",
    diffFile: "diff-final.png",
  },
];

async function compareImages(refPath, actualPath, diffPath) {
  if (!fs.existsSync(refPath)) {
    console.warn(`Reference image not found at ${refPath}`);
    return;
  }
  const refData = fs.readFileSync(refPath);
  const actData = fs.readFileSync(actualPath);

  const refPng = PNG.sync.read(refData);
  const actPng = PNG.sync.read(actData);

  const width = Math.min(refPng.width, actPng.width);
  const height = Math.min(refPng.height, actPng.height);

  const diffPng = new PNG({ width, height });
  const refCropped = new PNG({ width, height });
  const actCropped = new PNG({ width, height });

  PNG.bitblt(refPng, refCropped, 0, 0, width, height, 0, 0);
  PNG.bitblt(actPng, actCropped, 0, 0, width, height, 0, 0);

  const numDiffPixels = pixelmatch(
    refCropped.data,
    actCropped.data,
    diffPng.data,
    width,
    height,
    { threshold: 0.15 }
  );

  fs.writeFileSync(diffPath, PNG.sync.write(diffPng));

  const totalPixels = width * height;
  const diffPercent = ((numDiffPixels / totalPixels) * 100).toFixed(2);

  console.log(`\n=== Comparison: ${path.basename(actualPath)} ===`);
  console.log(`Reference size: ${refPng.width}x${refPng.height}, Actual size: ${actPng.width}x${actPng.height}`);
  console.log(`Total pixels: ${totalPixels}, Diff pixels: ${numDiffPixels}, Diff percentage: ${diffPercent}%`);
}

async function main() {
  if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  if (!fs.existsSync(ARTIFACTS_DIR)) fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });

  console.log("Launching Headless Chrome...");
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-gpu",
      "--hide-scrollbars",
      "--force-device-scale-factor=1",
      "--font-render-hinting=medium",
    ],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1586, height: 992, deviceScaleFactor: 1 });

    for (const item of PAGES_TO_TEST) {
      console.log(`\nTesting page: ${item.name} at ${item.url}...`);
      await page.goto(item.url, { waitUntil: "networkidle0", timeout: 30000 });

      // Hide Next.js dev overlays
      await page.addStyleTag({
        content: `
          nextjs-portal,
          [data-nextjs-toast],
          #nextjs-dev-overlay,
          #__next-build-watcher {
            display: none !important;
          }
        `,
      });

      await new Promise((r) => setTimeout(r, 800));

      const actualPath = path.join(OUTPUT_DIR, item.actualFile);
      const diffPath = path.join(OUTPUT_DIR, item.diffFile);

      await page.screenshot({ path: actualPath, fullPage: false });
      console.log(`Saved screenshot: ${actualPath}`);

      await compareImages(item.refPath, actualPath, diffPath);

      // Copy to artifacts dir
      fs.copyFileSync(actualPath, path.join(ARTIFACTS_DIR, item.actualFile));
      if (fs.existsSync(diffPath)) {
        fs.copyFileSync(diffPath, path.join(ARTIFACTS_DIR, item.diffFile));
      }
    }

    // Interactive tests for Version History
    console.log("\nTesting interactive features for Version History...");
    await page.goto("http://localhost:3000/trips/history", { waitUntil: "networkidle0" });
    await page.addStyleTag({ content: `nextjs-portal, [data-nextjs-toast] { display: none !important; }` });
    await new Promise((r) => setTimeout(r, 500));

    // Click unchanged activities accordion
    const unchangedBtn = await page.$('button[aria-expanded="false"]');
    if (unchangedBtn) {
      await unchangedBtn.click();
      await new Promise((r) => setTimeout(r, 300));
      const expPath = path.join(OUTPUT_DIR, "interactive-history-expanded.png");
      await page.screenshot({ path: expPath });
      fs.copyFileSync(expPath, path.join(ARTIFACTS_DIR, "interactive-history-expanded.png"));
      console.log("Saved interactive state: interactive-history-expanded.png");
    }

    // Interactive tests for Final Itinerary
    console.log("\nTesting interactive features for Final Itinerary...");
    await page.goto("http://localhost:3000/trips/final", { waitUntil: "networkidle0" });
    await page.addStyleTag({ content: `nextjs-portal, [data-nextjs-toast] { display: none !important; }` });
    await new Promise((r) => setTimeout(r, 500));

    // Click Day 2 to expand
    const dayHeaders = await page.$$('button[aria-expanded]');
    if (dayHeaders.length >= 2) {
      await dayHeaders[1].click();
      await new Promise((r) => setTimeout(r, 300));
      const day2Path = path.join(OUTPUT_DIR, "interactive-final-day2.png");
      await page.screenshot({ path: day2Path });
      fs.copyFileSync(day2Path, path.join(ARTIFACTS_DIR, "interactive-final-day2.png"));
      console.log("Saved interactive state: interactive-final-day2.png");
    }

    console.log("\nAll captures and tests completed successfully!");
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("Error in capture-all-targets:", err);
  process.exit(1);
});

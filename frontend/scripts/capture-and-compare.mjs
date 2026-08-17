import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const TARGET_URL = "http://localhost:3000/trips/conflict";
const REFERENCE_PATH = "f:/Project/TravelMind/参考图/规划失败 or 无可行方案.png";
const OUTPUT_DIR = "f:/Project/TravelMind/frontend/tests";

async function main() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

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
    // Reference image is 1586 x 992
    await page.setViewport({ width: 1586, height: 992, deviceScaleFactor: 1 });

    console.log(`Navigating to ${TARGET_URL}...`);
    await page.goto(TARGET_URL, { waitUntil: "networkidle0", timeout: 30000 });

    // Hide Next.js dev portal badge
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

    // Wait a bit for all CSS animations/fonts to settle
    await new Promise((r) => setTimeout(r, 800));

    const actualPath = path.join(OUTPUT_DIR, "actual-conflict.png");
    await page.screenshot({ path: actualPath, fullPage: false });
    console.log(`Captured screenshot: ${actualPath}`);

    // Read reference and actual images
    if (fs.existsSync(REFERENCE_PATH)) {
      const refData = fs.readFileSync(REFERENCE_PATH);
      const actData = fs.readFileSync(actualPath);

      const refPng = PNG.sync.read(refData);
      const actPng = PNG.sync.read(actData);

      const width = Math.min(refPng.width, actPng.width);
      const height = Math.min(refPng.height, actPng.height);

      console.log(`Reference size: ${refPng.width}x${refPng.height}, Actual size: ${actPng.width}x${actPng.height}`);

      // Create cropped buffers if needed for exact match
      const diffPng = new PNG({ width, height });

      // If dimensions match or need crop
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

      const diffPath = path.join(OUTPUT_DIR, "diff-conflict.png");
      fs.writeFileSync(diffPath, PNG.sync.write(diffPng));

      const totalPixels = width * height;
      const diffPercent = ((numDiffPixels / totalPixels) * 100).toFixed(2);

      console.log(`\n=== Comparison Results ===`);
      console.log(`Total pixels: ${totalPixels}`);
      console.log(`Diff pixels: ${numDiffPixels}`);
      console.log(`Diff percentage: ${diffPercent}%`);
      console.log(`Diff saved to: ${diffPath}`);
    } else {
      console.warn(`Reference image not found at ${REFERENCE_PATH}`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("Error in capture-and-compare:", err);
  process.exit(1);
});

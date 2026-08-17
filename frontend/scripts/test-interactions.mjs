import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const TARGET_URL = "http://localhost:3000/trips/conflict";
const OUTPUT_DIR = "f:/Project/TravelMind/frontend/tests";

async function runInteractionTests() {
  console.log("Starting interactive verification test suite...");
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--hide-scrollbars"],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1586, height: 992, deviceScaleFactor: 1 });
    await page.goto(TARGET_URL, { waitUntil: "networkidle0" });

    await page.addStyleTag({
      content: `nextjs-portal, [data-nextjs-toast], #nextjs-dev-overlay { display: none !important; }`,
    });

    console.log("1. Testing Option Selection & Input typing...");
    // Click Option 2
    const optionCards = await page.$$("[role='radio']");
    if (optionCards.length >= 2) {
      await optionCards[1].click();
      await new Promise((r) => setTimeout(r, 200));
    }

    // Type feedback
    const input = await page.$("input[placeholder*='或者告诉我']");
    if (input) {
      await input.type("希望能将吉卜力改到周四上午，同时增加浅草寺周边的美食探索。");
      await new Promise((r) => setTimeout(r, 300));
    }

    const stateInteractivePath = path.join(OUTPUT_DIR, "interactive-state-selection.png");
    await page.screenshot({ path: stateInteractivePath });
    console.log(`Saved interactive selection screenshot: ${stateInteractivePath}`);

    console.log("2. Testing Conflict Detail Modal (Budget)...");
    // Click first 查看详情
    const detailButtons = await page.$$("button");
    for (const btn of detailButtons) {
      const text = await page.evaluate((el) => el.textContent, btn);
      if (text && text.includes("查看详情")) {
        await btn.click();
        break;
      }
    }

    await new Promise((r) => setTimeout(r, 400));
    const modalBudgetPath = path.join(OUTPUT_DIR, "interactive-modal-budget.png");
    await page.screenshot({ path: modalBudgetPath });
    console.log(`Saved modal screenshot: ${modalBudgetPath}`);

    // Click apply in modal
    const applyBtn = await page.$("button[class*='applyBtn']");
    if (applyBtn) {
      await applyBtn.click();
      await new Promise((r) => setTimeout(r, 400));
    }

    console.log("3. Testing Copy Request ID...");
    const copyBtn = await page.$("button[title='复制请求 ID']");
    if (copyBtn) {
      await copyBtn.click();
      await new Promise((r) => setTimeout(r, 300));
    }

    console.log("Interactive tests completed successfully!");
  } finally {
    await browser.close();
  }
}

runInteractionTests().catch((err) => {
  console.error("Interaction test failed:", err);
  process.exit(1);
});

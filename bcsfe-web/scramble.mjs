// Scrambles the pages visitors download, while the repo keeps the readable code.
// Run by the Dockerfile while Render builds the site: node scramble.mjs static
// - the <script> code is obfuscated (renamed, encoded strings, reshuffled logic)
// - the <style> code and the page layout are squeezed, and comments are removed
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import JavaScriptObfuscator from "javascript-obfuscator";

const OPTIONS = {
  compact: true,
  identifierNamesGenerator: "hexadecimal",
  renameGlobals: false,            // keep names the page's HTML refers to
  stringArray: true,
  stringArrayEncoding: ["base64"],
  stringArrayThreshold: 0.75,
  stringArrayRotate: true,
  stringArrayShuffle: true,
  splitStrings: true,
  splitStringsChunkLength: 10,
  controlFlowFlattening: true,
  controlFlowFlatteningThreshold: 0.3,  // higher makes the page slower
  deadCodeInjection: true,
  deadCodeInjectionThreshold: 0.1,
  numbersToExpressions: true,
  simplify: true,
  transformObjectKeys: false,      // keys are sent to the server as-is
  selfDefending: false,            // these two can break pages or freeze browsers
  debugProtection: false,
  unicodeEscapeSequence: false,
};

const scrambleJs = (code) => JavaScriptObfuscator.obfuscate(code, OPTIONS).getObfuscatedCode();
const squeezeCss = (css) => css.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\s*\n\s*/g, " ").trim();
const squeezeHtml = (html) => html.replace(/<!--[\s\S]*?-->/g, "").replace(/\n\s+/g, "\n").replace(/\n{2,}/g, "\n");

export function scramble(html) {
  // Only markup between <script>/<style> blocks is squeezed, so text inside the code stays exact.
  return html.split(/(<script>[\s\S]*?<\/script>|<style>[\s\S]*?<\/style>)/).map((part, i) => {
    if (i % 2 === 0) return squeezeHtml(part);
    if (part.startsWith("<script>")) return `<script>${scrambleJs(part.slice(8, -9))}</script>`;
    return `<style>${squeezeCss(part.slice(7, -8))}</style>`;
  }).join("");
}

const dir = process.argv[2] || "static";
for (const name of readdirSync(dir).filter((n) => n.endsWith(".html"))) {
  const file = join(dir, name);
  const before = readFileSync(file, "utf8");
  const after = scramble(before);
  writeFileSync(file, after);
  console.log(`scrambled ${file}: ${Math.round(before.length / 1024)} KB -> ${Math.round(after.length / 1024)} KB`);
}

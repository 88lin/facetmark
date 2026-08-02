// Bundle the three entry points and copy the static files next to them.
// esbuild rather than a framework build: an MV3 service worker is a plain ES
// module and the popup is one HTML file, so a bundler config is all that is
// actually needed here.
import { build, context } from "esbuild";
import { cp, mkdir, rm } from "node:fs/promises";

const watch = process.argv.includes("--watch");
const outdir = "dist";

await rm(outdir, { recursive: true, force: true });
await mkdir(outdir, { recursive: true });

const options = {
  entryPoints: ["src/background.ts", "src/popup.ts", "src/options.ts"],
  outdir,
  bundle: true,
  format: "esm",
  target: "chrome110",
  sourcemap: watch ? "inline" : false,
  minify: !watch,
  logLevel: "info",
};

for (const f of ["manifest.json", "popup.html", "popup.css", "options.html"]) {
  await cp(`src/${f}`, `${outdir}/${f}`);
}
await cp("src/icons", `${outdir}/icons`, { recursive: true });

if (watch) {
  const ctx = await context(options);
  await ctx.watch();
  console.log("watching...");
} else {
  await build(options);
  console.log(`built -> ${outdir}/`);
}

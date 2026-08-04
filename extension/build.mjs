// Bundle the three entry points and copy the static files next to them.
// esbuild rather than a framework build: an MV3 service worker is a plain ES
// module and the popup is one HTML file, so a bundler config is all that is
// actually needed here.
import { build, context } from "esbuild";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";

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

for (const f of ["popup.html", "popup.css", "options.html"]) {
  await cp(`src/${f}`, `${outdir}/${f}`);
}

// The manifest is stamped rather than copied. It used to carry its own
// `version`, which sat at 1.0.0 while package.json climbed to 1.4.0 -- an
// extension that reported a release nobody had cut. package.json is the one
// source of truth; src/manifest.json deliberately has no version field.
const pkg = JSON.parse(await readFile("package.json", "utf8"));
const { manifest_version, name, ...rest } = JSON.parse(
  await readFile("src/manifest.json", "utf8"),
);
if (!pkg.version) throw new Error("package.json has no version to stamp");
await writeFile(
  `${outdir}/manifest.json`,
  JSON.stringify({ manifest_version, name, version: pkg.version, ...rest }, null, 2) + "\n",
);
await cp("src/icons", `${outdir}/icons`, { recursive: true });

if (watch) {
  const ctx = await context(options);
  await ctx.watch();
  console.log("watching...");
} else {
  await build(options);
  console.log(`built -> ${outdir}/`);
}

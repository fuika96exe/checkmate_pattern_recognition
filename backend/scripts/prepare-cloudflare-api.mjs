import { copyFileSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const backendDirectory = dirname(dirname(fileURLToPath(import.meta.url)));
const outputDirectory = join(backendDirectory, ".cloudflare-src");

function copyPythonTree(source, destination) {
  mkdirSync(destination, { recursive: true });
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    if (entry.name === "__pycache__") continue;

    const sourcePath = join(source, entry.name);
    const destinationPath = join(destination, entry.name);
    if (entry.isDirectory()) {
      copyPythonTree(sourcePath, destinationPath);
    } else if (entry.isFile() && entry.name.endsWith(".py")) {
      copyFileSync(sourcePath, destinationPath);
    }
  }
}

rmSync(outputDirectory, { recursive: true, force: true });
mkdirSync(outputDirectory, { recursive: true });
copyPythonTree(join(backendDirectory, "app"), join(outputDirectory, "app"));
copyFileSync(
  join(backendDirectory, "worker.py"),
  join(outputDirectory, "worker.py"),
);

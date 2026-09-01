const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");

const FRONTEND_PORT = 3001;
const BACKEND_PORT = 8000;
let backendProcess;
let frontendProcess;

function waitFor(url, timeoutMs = 30000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const request = http.get(url, (response) => {
        response.resume();
        if (response.statusCode && response.statusCode < 500) {
          resolve();
        } else {
          retry();
        }
      });
      request.on("error", retry);
      request.setTimeout(1000, () => request.destroy());
    };
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error(`服务启动超时：${url}`));
        return;
      }
      setTimeout(check, 250);
    };
    check();
  });
}

function startServices() {
  const resources = process.resourcesPath;
  const runtime = path.join(resources, "app-runtime");
  const backendExe = path.join(resources, "backend", "xiangqi-backend.exe");
  const dataDir = path.join(resources, "backend-data");
  const vinextCli = path.join(runtime, "node_modules", "vinext", "dist", "cli.js");

  backendProcess = spawn(backendExe, [], {
    cwd: dataDir,
    windowsHide: true,
    stdio: "ignore",
    env: { ...process.env, XIANGQI_DATA_DIR: dataDir },
  });
  frontendProcess = spawn(
    process.execPath,
    ["--run-as-node", vinextCli, "start", "--hostname", "127.0.0.1", "--port", String(FRONTEND_PORT)],
    {
      cwd: runtime,
      windowsHide: true,
      stdio: "ignore",
      env: { ...process.env, NODE_ENV: "production" },
    },
  );
}

async function createWindow() {
  startServices();
  await waitFor(`http://127.0.0.1:${BACKEND_PORT}/api/health`);
  await waitFor(`http://127.0.0.1:${FRONTEND_PORT}/`);

  const window = new BrowserWindow({
    width: 1440,
    height: 980,
    minWidth: 1080,
    minHeight: 720,
    autoHideMenuBar: true,
    backgroundColor: "#f5f2ea",
    webPreferences: { contextIsolation: true, sandbox: true },
  });
  await window.loadURL(`http://127.0.0.1:${FRONTEND_PORT}/`);
}

function stopServices() {
  for (const child of [frontendProcess, backendProcess]) {
    if (child && !child.killed) child.kill();
  }
}

app.whenReady().then(() => {
  createWindow().catch((error) => {
    dialog.showErrorBox("象棋杀法识别启动失败", error.message);
    stopServices();
    app.quit();
  });
});

app.on("window-all-closed", () => {
  stopServices();
  app.quit();
});

app.on("before-quit", stopServices);

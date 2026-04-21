import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawn } from 'node:child_process'

const args = process.argv.slice(2)
if (args.length === 0) {
  console.error('Usage: node scripts/run-with-esbuild-temp.mjs <cmd> [...args]')
  process.exit(2)
}

const isWindows = process.platform === 'win32'

function resolveEsbuildBinary() {
  // esbuild publishes platform-specific packages under @esbuild/*
  // On Windows (Node x64), the package is @esbuild/win32-x64.
  // We intentionally keep this conservative for this repo’s supported env.
  if (!isWindows) return null
  try {
    const exe = require.resolve('@esbuild/win32-x64/esbuild.exe', { paths: [process.cwd()] })
    return exe
  } catch {
    return null
  }
}

function ensureTempEsbuildBinary() {
  const resolved = resolveEsbuildBinary()
  if (!resolved) return null

  // Node cannot spawn executables under some OneDrive/controlled-folder setups (EPERM).
  // Copy the binary into the OS temp dir and point ESBUILD_BINARY_PATH there.
  const target = path.join(os.tmpdir(), 'language-coach-esbuild.exe')
  try {
    if (!fs.existsSync(target)) {
      fs.copyFileSync(resolved, target)
    }
    return target
  } catch {
    return null
  }
}

const tempEsbuild = ensureTempEsbuildBinary()
const env = { ...process.env }
if (tempEsbuild) {
  env.ESBUILD_BINARY_PATH = tempEsbuild
}

const cmd = args[0]
const cmdArgs = args.slice(1)

const child = spawn(cmd, cmdArgs, {
  stdio: 'inherit',
  shell: true,
  env,
})

child.on('exit', (code) => {
  process.exit(code ?? 1)
})


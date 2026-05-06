import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const args = process.argv.slice(2)
if (args.length === 0) {
  console.error('Usage: node scripts/run-with-esbuild-temp.mjs <cmd> [...args]')
  process.exit(2)
}

const isWindows = process.platform === 'win32'
const nodeModulesBin = path.join(process.cwd(), 'node_modules', '.bin')

function resolveEsbuildBinary() {
  if (!isWindows) return null
  try {
    return require.resolve('@esbuild/win32-x64/esbuild.exe', { paths: [process.cwd()] })
  } catch {
    return null
  }
}

function ensureTempEsbuildBinary() {
  const resolved = resolveEsbuildBinary()
  if (!resolved) return null

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

function enrichPath(env) {
  const currentPath = env.PATH || env.Path || ''
  return {
    ...env,
    PATH: [nodeModulesBin, currentPath].filter(Boolean).join(path.delimiter),
  }
}

function resolveCommand(command) {
  if (path.isAbsolute(command) || command.includes('/') || command.includes('\\')) {
    return command
  }

  const candidates = isWindows
    ? [path.join(nodeModulesBin, `${command}.cmd`), path.join(nodeModulesBin, `${command}.exe`)]
    : [path.join(nodeModulesBin, command)]

  return candidates.find((candidate) => fs.existsSync(candidate)) || command
}

function escapeCmdArg(arg) {
  if (arg.length === 0) return '""'
  if (!/[ \t"&()<>^|]/.test(arg)) return arg
  return `"${arg.replace(/"/g, '\\"')}"`
}

const tempEsbuild = ensureTempEsbuildBinary()
const env = enrichPath({ ...process.env })
if (tempEsbuild) {
  env.ESBUILD_BINARY_PATH = tempEsbuild
}

const cmd = resolveCommand(args[0])
const cmdArgs = args.slice(1)

const child = isWindows && /\.(cmd|bat)$/i.test(cmd)
  ? spawn(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', [cmd, ...cmdArgs].map(escapeCmdArg).join(' ')], {
      stdio: 'inherit',
      env,
    })
  : spawn(cmd, cmdArgs, {
      stdio: 'inherit',
      env,
    })

child.on('exit', (code) => {
  process.exit(code ?? 1)
})

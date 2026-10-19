// guard-legacy: the sibling project `meeting-text` is a read-only reference.
// Reads are fine; edits and destructive shell commands aimed at it are refused.
import fs from "node:fs"
import path from "node:path"

const LOCKED_PROJECT = "meeting-text"
const MUTATING_TOOLS = new Set(["edit", "write", "patch"])
const DESTRUCTIVE =
  /(^|[\s;&|])(rm|rmdir|del|erase|mv|Move-Item|Remove-Item|Set-Content|Out-File|truncate)([\s;&|]|$)|>\s*\S|git\s+(-C\s+\S+\s+)?(clean|checkout|reset|restore)/i

function lockedRoots(starts) {
  const roots = new Set()
  for (const start of starts) {
    if (!start) continue
    let current
    try {
      current = path.resolve(String(start))
    } catch {
      continue
    }
    for (let depth = 0; depth < 5 && current; depth += 1) {
      const candidate = path.join(path.dirname(current), LOCKED_PROJECT)
      try {
        if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) roots.add(candidate)
      } catch {
        // ignore unreadable candidates
      }
      const parent = path.dirname(current)
      if (parent === current) break
      current = parent
    }
  }
  return [...roots]
}

export const GuardLegacyProject = async ({ worktree, directory }) => {
  const roots = lockedRoots([worktree, directory, process.cwd()])

  const contains = (target) => {
    if (typeof target !== "string" || target.length === 0) return false
    let resolved
    try {
      resolved = path.resolve(target)
    } catch {
      return false
    }
    return roots.some((root) => {
      const rel = path.relative(root, resolved)
      return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel))
    })
  }

  const mention = (command) => {
    const normalized = command.replace(/\//g, "\\").toLowerCase()
    return roots.find((root) => normalized.includes(root.toLowerCase()))
  }

  return {
    "tool.execute.before": async (input, output) => {
      const args = output?.args ?? {}

      if (MUTATING_TOOLS.has(input.tool)) {
        const target = args.filePath ?? args.path ?? args.file
        if (contains(target)) {
          throw new Error(
            `GuardLegacyProject: "${target}" lives in the locked reference project (${LOCKED_PROJECT}). ` +
              `Read from it if you must, but make every change inside Minute-mate.`,
          )
        }
        return
      }

      if (input.tool === "bash") {
        const command = String(args.command ?? "")
        if (!command || !DESTRUCTIVE.test(command)) return
        const hit = mention(command)
        if (hit) {
          throw new Error(
            `GuardLegacyProject: refusing this command because it looks destructive and touches ${hit}.\n` +
              `Rebuild/copy inside Minute-mate instead, or ask the user first.`,
          )
        }
      }
    },
  }
}

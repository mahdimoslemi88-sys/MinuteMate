// dotnet-after-edit: after a C# edit under desktop/, build the solution and append
// the compiler errors to the tool result so they are impossible to miss.
// Disable with MINUTEMATE_DOTNET=0.
import fs from "node:fs"
import path from "node:path"

const TIMEOUT_MS = Number(process.env.MINUTEMATE_DOTNET_TIMEOUT_MS ?? 240000)

const append = (output, note) => {
  const current = typeof output.output === "string" ? output.output : ""
  const separator = current === "" || current.endsWith("\n") ? "" : "\n"
  output.output = current + separator + note
}

export const DotnetAfterEdit = async ({ $, directory, worktree, client }) => {
  const root = path.resolve(String(worktree || directory || process.cwd()))
  const desktop = path.join(root, "desktop")
  const solution = path.join(desktop, "MinuteMate.Desktop.sln")

  return {
    "tool.execute.after": async (input, output) => {
      if (process.env.MINUTEMATE_DOTNET === "0") return
      if (input.tool !== "edit" && input.tool !== "write") return

      const file = String(output?.args?.filePath ?? "")
      if (!/\.cs$/i.test(file)) return
      if (/[\\/](bin|obj)[\\/]/i.test(file)) return
      if (!fs.existsSync(solution)) return

      const build = (async () =>
        await $`cd ${desktop} && dotnet build ${solution} --nologo -v quiet`.quiet().nothrow())()

      let timer
      const timeout = new Promise((resolve) => {
        timer = setTimeout(() => resolve(null), TIMEOUT_MS)
      })

      let result = null
      try {
        result = await Promise.race([build, timeout])
      } catch (error) {
        append(output, `[dotnet-after-edit] could not run dotnet build (${error?.message ?? error}).`)
        return
      } finally {
        clearTimeout(timer)
      }

      if (result === null) {
        append(output, "[dotnet-after-edit] dotnet build timed out; run `dotnet build desktop/MinuteMate.Desktop.sln` manually.")
        return
      }

      if (result.exitCode === 0) {
        append(output, "[dotnet-after-edit] desktop build OK (0 warnings, 0 errors expected).")
        return
      }

      const text = `${result.stdout ?? ""}${result.stderr ?? ""}`
        .split(/\r?\n/)
        .filter(Boolean)
        .slice(-30)
        .join("\n")
      append(output, `[dotnet-after-edit] dotnet build FAILED (exit ${result.exitCode}):\n${text}`)
      try {
        const logged = client?.app?.log?.({
          body: { service: "dotnet-after-edit", level: "error", message: `desktop build failed after edit of ${file}` },
        })
        if (logged && typeof logged.catch === "function") logged.catch(() => {})
      } catch {
        // best effort
      }
    },
  }
}

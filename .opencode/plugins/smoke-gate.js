// smoke-gate: after edits inside the engine package, re-run the NDJSON smoke test
// in the background (scripts/smoke_job.py) and report the outcome.
// Disable with MINUTEMATE_SMOKE=0. Tune the debounce with MINUTEMATE_SMOKE_COOLDOWN_MS.
import fs from "node:fs"
import path from "node:path"

const TRIGGER =
  /engine\/minutemate\/(cli|pipeline|job|config|events)\.py$|engine\/minutemate\/(asr|audio|diarization|merge|text|models)\/[a-z_]+\.py$/i

export const SmokeGate = async ({ $, directory, worktree, client }) => {
  const root = path.resolve(String(worktree || directory || process.cwd()))
  const script = path.join(root, "scripts", "smoke_job.py")
  const audio = path.join(root, "scratch", "sample30.wav")
  const cooldown = Number(process.env.MINUTEMATE_SMOKE_COOLDOWN_MS ?? 120000)

  const state = { running: false, queued: false, lastStarted: 0 }

  const notify = (message) => {
    try {
      const logged = client?.app?.log?.({ body: { service: "smoke-gate", level: "info", message } })
      if (logged && typeof logged.catch === "function") logged.catch(() => {})
    } catch {
      // best effort
    }
    try {
      const toasted = client?.tui?.showToast?.({ body: { message, variant: "info" } })
      if (toasted && typeof toasted.catch === "function") toasted.catch(() => {})
    } catch {
      // best effort
    }
  }

  const tail = (text, lines) => text.split(/\r?\n/).filter(Boolean).slice(-lines).join("\n")

  const run = async () => {
    state.running = true
    state.queued = false
    state.lastStarted = Date.now()
    try {
      const result = await $`cd ${root} && python ${script} ${audio} --num-speakers 2`
        .quiet()
        .nothrow()
      const output = `${result?.stdout ?? ""}${result?.stderr ?? ""}`
      if (result?.exitCode === 0) {
        notify("smoke-gate: engine smoke test passed (NDJSON end-to-end)")
      } else {
        notify(`smoke-gate: engine smoke test FAILED (exit ${result?.exitCode})`)
        const logged = client?.app?.log?.({
          body: {
            service: "smoke-gate",
            level: "error",
            message: `smoke test failed:\n${tail(output, 25)}`,
          },
        })
        if (logged && typeof logged.catch === "function") logged.catch(() => {})
      }
    } catch (error) {
      notify(`smoke-gate: could not run scripts/smoke_job.py (${error?.message ?? error})`)
    } finally {
      state.running = false
      if (state.queued) run()
    }
  }

  const schedule = () => {
    if (state.running) {
      state.queued = true
      return
    }
    if (Date.now() - state.lastStarted < cooldown) return
    void run()
  }

  return {
    "tool.execute.after": async (input, output) => {
      if (process.env.MINUTEMATE_SMOKE === "0") return
      if (input.tool !== "edit" && input.tool !== "write") return
      const file = String(output?.args?.filePath ?? "").replace(/\\/g, "/")
      if (!TRIGGER.test(file)) return
      if (!fs.existsSync(script) || !fs.existsSync(audio)) return
      schedule()
      const note = `\n[smoke-gate] smoke test scheduled in the background (scripts/smoke_job.py).`
      const current = typeof output.output === "string" ? output.output : ""
      output.output = current + note
    },
  }
}

// contract-sync: the engine (Python) and the desktop (C#) share one wire contract.
// Touching either side of the contract warns about the other side.
const RULES = [
  {
    test: /engine\/minutemate\/(events|config)\.py$/i,
    message:
      "contract-sync: engine event/job contract changed. Keep the desktop in sync: " +
      "desktop/src/MinuteMate.Core/Contracts/{EngineEvent.cs,EngineEventType.cs,EngineStage.cs,EngineJobRequest.cs,EngineClientOptions.cs} " +
      "and desktop/src/MinuteMate.EngineClient/EngineProcessRunner.cs",
  },
  {
    test: /minutemate\.core\/contracts\/(engineevent|engineeventtype|enginestage|enginejobrequest|engineclientoptions)\.cs$/i,
    message:
      "contract-sync: desktop contract changed. Keep the engine in sync: " +
      "engine/minutemate/events.py (EventType/Stage/Status + camelCase field names) and " +
      "engine/minutemate/config.py (EngineConfig.from_payload keys)",
  },
]

export const ContractSync = async ({ client }) => {
  const notify = (message) => {
    try {
      const logged = client?.app?.log?.({
        body: { service: "contract-sync", level: "warn", message },
      })
      if (logged && typeof logged.catch === "function") logged.catch(() => {})
    } catch {
      // logging is best effort
    }
    try {
      const toasted = client?.tui?.showToast?.({
        body: { message, variant: "warning" },
      })
      if (toasted && typeof toasted.catch === "function") toasted.catch(() => {})
    } catch {
      // toasting is best effort
    }
  }

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "edit" && input.tool !== "write") return
      const file = String(output?.args?.filePath ?? "").replace(/\\/g, "/")
      if (!file) return
      for (const rule of RULES) {
        if (rule.test.test(file)) notify(rule.message)
      }
    },
  }
}

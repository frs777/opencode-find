import { Plugin } from "@opencode/plugin"
import { spawn } from "node:child_process"
import { join } from "node:path"
import { existsSync, readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const REPO = fileURLToPath(new URL("..", import.meta.url)).replace(/\/$/, "")
const SCRIPTS = join(REPO, "scripts")
const PYTHON = process.env.PYTHON_BIN || "python3"

function runFind(args: string[]): Promise<string> {
  return new Promise((resolve) => {
    const proc = spawn(PYTHON, [join(SCRIPTS, "find.py"), ...args], { timeout: 30000 })
    let stdout = ""
    let stderr = ""
    proc.stdout.on("data", (d) => (stdout += d.toString()))
    proc.stderr.on("data", (d) => (stderr += d.toString()))
    proc.on("close", (code) => {
      if (code !== 0) resolve(`find error (exit ${code}): ${stderr.trim() || stdout.trim()}`)
      else resolve(stdout.trim() || "(brak wyniku)")
    })
    proc.on("error", (err) => resolve(`find error: ${err.message}`))
  })
}

export default Plugin.define({
  id: "find",
  name: "find",
  version: "0.2.0",
  description: "Meta-plugin do wyszukiwania zainstalowanych skilli i wtyczek na podstawie naturalnego opisu zadania.",
  async setup(ctx) {
    const skillMd = join(REPO, "skills", "find", "SKILL.md")
    if (existsSync(skillMd)) {
      await ctx.skill.transform((editor: any) => {
        editor.add({
          id: "find",
          name: "find",
          description: "Meta-plugin do wyszukiwania i dobierania zainstalowanych skilli oraz wtyczek na podstawie naturalnego opisu zadania.",
          path: skillMd,
          content: readFileSync(skillMd, "utf-8"),
        })
      })
    }

    await ctx.tool.transform((editor: any) => {
      editor.namespace({ name: "find", description: "Discovery nad zainstalowanymi skillami i wtyczkami." })

      editor.add({
        name: "search",
        description: "Wyszukuje skille pasujące do opisu zadania (lokalny indeks).",
        input: {
          type: "object",
          properties: {
            query: { type: "string", description: "Opis zadania lub temat" },
            limit: { type: "number", description: "Maks. liczba wyników (domyślnie 10)" },
          },
          required: ["query"],
          additionalProperties: false,
        },
        options: { namespace: "find", codemode: true },
        execute: async (input: { query: string; limit?: number }) => {
          const out = await runFind(["szukaj", input.query])
          return { content: out }
        },
      })

      editor.add({
        name: "rescan",
        description: "Przeskanuj źródła i zaktualizuj indeks (added/changed/removed/invalid).",
        input: {
          type: "object",
          properties: {
            roots: { type: "array", items: { type: "string" }, description: "Katalogi źródłowe (domyślnie: wszystkie źródła OpenCode)" },
          },
          additionalProperties: false,
        },
        options: { namespace: "find", codemode: true },
        execute: async (input: { roots?: string[] }) => {
          const args = ["rescan"]
          if (input.roots && input.roots.length) {
            args.push("--root", ...input.roots)
          }
          const out = await runFind(args)
          return { content: out }
        },
      })

      editor.add({
        name: "status",
        description: "Stan indeksu: liczba skilli, źródła, mtime.",
        input: { type: "object", properties: {}, additionalProperties: false },
        options: { namespace: "find", codemode: true },
        execute: async () => {
          const out = await runFind(["status"])
          return { content: out }
        },
      })

      editor.add({
        name: "use",
        description: "Wskaż konkretny skill/wtyczkę po nazwie (dokładne lub częściowe dopasowanie).",
        input: {
          type: "object",
          properties: {
            name: { type: "string", description: "Nazwa skillu" },
          },
          required: ["name"],
          additionalProperties: false,
        },
        options: { namespace: "find", codemode: true },
        execute: async (input: { name: string }) => {
          const out = await runFind(["użyj", input.name])
          return { content: out }
        },
      })
    })

    return () => console.log("[find] Plugin unloaded")
  },
})
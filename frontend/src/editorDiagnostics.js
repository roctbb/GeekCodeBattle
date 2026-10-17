// Only recognized compiler locations become editor markers. Program stdout and
// test mismatches must never be mistaken for source locations.
export function checkerDiagnostics(message, sourceCode, language) {
  if (typeof message !== 'string' || !message.trim()) return []
  const lines = sourceCode.split('\n')
  const validLine = number => Number.isInteger(number) && number >= 1 && number <= lines.length
  if (language === 'python') {
    const error = message.match(/^(?:[\w.]*Error|[\w.]*Exception|KeyboardInterrupt|SystemExit):?.*$/gm)?.at(-1)
    if (!error) return []
    const locations = [...message.matchAll(/File\s+"([^"]+)",\s+line\s+(\d+)/g)]
      .filter(match => !/\/(?:usr|lib|site-packages)\//.test(match[1]) && validLine(Number(match[2])))
    const location = locations.at(-1)
    return location ? [{ line: Number(location[2]), column: 1, severity: 'error', message: error.slice(0, 1000) }] : []
  }
  if (language === 'cpp') {
    const seen = new Set()
    return [...message.matchAll(/^(.+\.(?:cpp|cc|cxx)):(\d+):(?:(\d+):)?\s*(fatal error|error|warning):\s*(.+)$/gm)]
      .filter(match => validLine(Number(match[2])) && !/\/(?:usr|include)\//.test(match[1]))
      .flatMap(match => {
        const key = `${match[2]}:${match[3]}:${match[5]}`
        if (seen.has(key)) return []
        seen.add(key)
        return [{ line: Number(match[2]), column: Number(match[3] || 1), severity: match[4] === 'warning' ? 'warning' : 'error', message: match[5].slice(0, 1000) }]
      }).slice(0, 30)
  }
  return []
}

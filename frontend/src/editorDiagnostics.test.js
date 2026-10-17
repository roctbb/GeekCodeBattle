import { expect, it } from 'vitest'
import { checkerDiagnostics } from './editorDiagnostics'

it('finds the user frame of a Python traceback and ignores interpreter files', () => {
  const message = 'File "main.py", line 2, in <module>\n  parse()\nFile "/usr/lib/python3/parser.py", line 1\nValueError: invalid value'
  expect(checkerDiagnostics(message, 'x = 1\nparse()', 'python')).toEqual([
    { line: 2, column: 1, severity: 'error', message: 'ValueError: invalid value' },
  ])
})
it('parses C++ errors and warnings without pointing into headers', () => {
  const message = '/usr/include/a.cpp:1:2: error: header error\nmain.cpp:2:4: error: expected ;\nmain.cpp:2:4: error: expected ;\nmain.cpp:3: warning: unused variable'
  expect(checkerDiagnostics(message, 'int main() {\n int x\n}', 'cpp')).toEqual([
    { line: 2, column: 4, severity: 'error', message: 'expected ;' },
    { line: 3, column: 1, severity: 'warning', message: 'unused variable' },
  ])
})
it('ignores stdout-like text, unlocated errors and out-of-range locations', () => {
  expect(checkerDiagnostics('line 1: hello', 'print(1)', 'python')).toEqual([])
  expect(checkerDiagnostics('ZeroDivisionError: division by zero', 'print(1)', 'python')).toEqual([])
  expect(checkerDiagnostics('File "main.py", line 20\nSyntaxError: invalid syntax', 'print(1)', 'python')).toEqual([])
  expect(checkerDiagnostics('main.cpp:20:3: error: invalid', 'int main(){}', 'cpp')).toEqual([])
})

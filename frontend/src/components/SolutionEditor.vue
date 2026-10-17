<template>
  <div ref="host" class="solution-editor" aria-label="Код решения"></div>
</template>
<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { basicSetup } from 'codemirror'
import { EditorState, Compartment, Prec } from '@codemirror/state'
import { EditorView, keymap } from '@codemirror/view'
import { indentWithTab, undo, redo } from '@codemirror/commands'
import { openSearchPanel } from '@codemirror/search'
import { indentUnit, syntaxTree } from '@codemirror/language'
import { snippetCompletion } from '@codemirror/autocomplete'
import { lintGutter, setDiagnostics, setDiagnosticsEffect } from '@codemirror/lint'
import { python, pythonLanguage } from '@codemirror/lang-python'
import { cpp, cppLanguage } from '@codemirror/lang-cpp'
import { oneDark } from '@codemirror/theme-one-dark'

const props = defineProps({
  modelValue: String,
  identity: String,
  language: String,
  fontSize: Number,
  theme: String,
  tabSize: Number,
  wrap: Boolean,
  diagnostics: Object,
})
const emit = defineEmits(['update:modelValue', 'run', 'submit', 'cursor'])
const host = ref(null),
  config = new Compartment(),
  cache = new Map()
let view, currentIdentity
function emitCursor() {
  const pos = view.state.selection.main.head,
    line = view.state.doc.lineAt(pos)
  emit('cursor', { line: line.number, column: pos - line.from + 1 })
}
function syncDocument(code) {
  const text = code || ''
  if (view.state.doc.toString() !== text)
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: text },
    })
}
function applyDiagnostics() {
  if (!view) return
  const snapshot = props.diagnostics
  const items = snapshot?.source_code === view.state.doc.toString() && snapshot?.language === props.language
    ? snapshot.items || [] : []
  const diagnostics = items.filter(item => item.line >= 1 && item.line <= view.state.doc.lines).map(item => {
    const line = view.state.doc.line(item.line)
    const from = Math.min(line.to, line.from + Math.max(0, (item.column || 1) - 1))
    return { from, to: item.column > 1 ? Math.min(line.to, from + 1) : line.to, severity: item.severity || 'error', message: item.message }
  })
  view.dispatch(setDiagnostics(view.state, diagnostics))
}
const snippets = [
  snippetCompletion('for ${item} in ${items}:\n    ${pass}', {
    label: 'for',
    detail: 'цикл Python',
  }),
  snippetCompletion('def ${name}(${args}):\n    ${pass}', {
    label: 'def',
    detail: 'функция Python',
  }),
  ...[
    'input',
    'print',
    'range',
    'len',
    'int',
    'str',
    'list',
    'map',
    'sorted',
    'enumerate',
    'zip',
    'sum',
    'min',
    'max',
    'set',
    'dict',
  ].map((label) => ({ label, type: 'function' })),
]
const cppSnippets = [
  snippetCompletion('for (int ${i} = 0; ${i} < ${n}; ++${i}) {\n    ${}\n}', {
    label: 'for',
    detail: 'цикл C++',
  }),
  snippetCompletion(
    '#include <iostream>\nusing namespace std;\n\nint main() {\n    ${}\n    return 0;\n}',
    { label: 'main', detail: 'точка входа C++' },
  ),
  ...[
    'std',
    'cin',
    'cout',
    'vector',
    'string',
    'sort',
    'lower_bound',
    'upper_bound',
    'map',
    'set',
    'pair',
    'long long',
    'size_t',
    'push_back',
    'begin',
    'end',
  ].map((label) => ({ label, type: 'keyword' })),
]
function completionSource(options) {
  return (context) => {
    if (
      /String|Comment/.test(
        syntaxTree(context.state).resolveInner(context.pos, -1).name,
      )
    )
      return null
    const word = context.matchBefore(/\w+/)
    if (!word && !context.explicit) return null
    return { from: word?.from ?? context.pos, options, validFor: /\w*/ }
  }
}
function extensions() {
  return [
    props.language === 'cpp' ? cpp() : python(),
    props.language === 'cpp'
      ? cppLanguage.data.of({ autocomplete: completionSource(cppSnippets) })
      : pythonLanguage.data.of({ autocomplete: completionSource(snippets) }),
    ...(props.theme === 'light' ? [] : [oneDark]),
    EditorState.tabSize.of(props.tabSize || 4),
    indentUnit.of(' '.repeat(props.tabSize || 4)),
    ...(props.wrap ? [EditorView.lineWrapping] : []),
    EditorView.theme({
      '&': {
        height: '100%',
        fontSize: `${props.fontSize || 15}px`,
        backgroundColor: props.theme === 'light' ? '#f9fafb' : '#191d23',
        color: props.theme === 'light' ? '#17212c' : '#dbe2e9',
      },
      '.cm-scroller': {
        fontFamily: 'ui-monospace, SFMono-Regular, Consolas, monospace',
        lineHeight: '1.65',
        overflow: 'auto',
      },
      '.cm-content': { padding: '16px 0' },
      '.cm-gutters': { paddingLeft: '8px' },
      '&.cm-focused': { outline: 'none' },
    }),
  ]
}
function createState(doc) {
  return EditorState.create({
    doc: doc || '',
    extensions: [
      basicSetup,
      lintGutter({ hoverTime: 150 }),
      EditorState.transactionExtender.of(transaction => transaction.docChanged
        ? { effects: setDiagnosticsEffect.of([]) } : null),
      config.of(extensions()),
      EditorView.contentAttributes.of({
        'aria-label': 'Код решения',
        spellcheck: 'false',
      }),
      Prec.highest(keymap.of([
        {
          key: 'Mod-Enter',
          run: () => {
            emit('run')
            return true
          },
        },
        {
          key: 'Mod-Shift-Enter',
          run: () => {
            emit('submit')
            return true
          },
        },
        indentWithTab,
      ])),
      EditorView.updateListener.of((update) => {
        if (update.docChanged)
          emit('update:modelValue', update.state.doc.toString())
        if (update.docChanged || update.selectionSet) emitCursor()
      }),
    ],
  })
}
onMounted(() => {
  currentIdentity = props.identity
  view = new EditorView({
    state: createState(props.modelValue),
    parent: host.value,
  })
  emitCursor()
  applyDiagnostics()
})
watch(
  () => props.identity,
  (next) => {
    if (!view || next === currentIdentity) return
    cache.set(currentIdentity, view.state)
    if (cache.size > 10) cache.delete(cache.keys().next().value)
    currentIdentity = next
    view.setState(cache.get(next) || createState(props.modelValue))
    // A restore can change identities without changing modelValue. Always
    // reconcile cached documents, even when the model watcher does not run.
    syncDocument(props.modelValue)
    view.dispatch({ effects: config.reconfigure(extensions()) })
    emitCursor()
  },
)
watch(() => [props.diagnostics, props.identity, props.modelValue, props.language], applyDiagnostics, { flush: 'post' })
watch(
  () => props.modelValue,
  (code) => {
    if (view) syncDocument(code)
  },
  { flush: 'post' },
)
watch(
  () => [
    props.language,
    props.fontSize,
    props.theme,
    props.tabSize,
    props.wrap,
  ],
  () => {
    if (view) view.dispatch({ effects: config.reconfigure(extensions()) })
  },
)
onUnmounted(() => {
  view?.destroy()
  cache.clear()
})
defineExpose({
  find: () => view && openSearchPanel(view),
  undo: () => view && undo(view),
  redo: () => view && redo(view),
  focus: () => view?.focus(),
  focusLine: (number) => {
    if (!view) return
    const line = view.state.doc.line(
      Math.min(view.state.doc.lines, Math.max(1, number)),
    )
    view.dispatch({ selection: { anchor: line.from }, scrollIntoView: true })
    view.focus()
  },
})
</script>
<style scoped>
.solution-editor {
  flex: 1;
  min-height: 180px;
  overflow: hidden;
}
</style>

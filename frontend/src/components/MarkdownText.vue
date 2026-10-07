<template>
  <div class="markdown-text" v-html="renderMarkdown(source)"></div>
</template>
<script setup>
import { renderMarkdown } from '../markdown'
defineProps({ source: { type: String, default: '' } })
</script>

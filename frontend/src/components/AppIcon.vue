<template>
  <FontAwesomeIcon :icon="icons[name]" class="app-icon" aria-hidden="true" focusable="false" />
</template>

<script setup>
import { config } from '@fortawesome/fontawesome-svg-core'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
  faArrowLeft, faArrowRight, faArrowRightFromBracket, faBolt,
  faChartColumn, faCheck, faChevronDown, faChevronRight, faClockRotateLeft,
  faCopy, faDoorOpen, faDownload, faFileLines, faFloppyDisk,
  faMinus, faPaperPlane, faPause, faPlus, faRotate, faStop,
  faTableColumns, faTrashCan, faUsers, faVolumeHigh, faVolumeXmark, faXmark,
  faPlay,
} from '@fortawesome/free-solid-svg-icons'

// The stylesheet is bundled by main.js; no runtime styles or remote assets.
config.autoAddCss = false

const icons = {
  'arrow-left': faArrowLeft,
  'arrow-right': faArrowRight,
  leave: faArrowRightFromBracket,
  bolt: faBolt,
  chart: faChartColumn,
  check: faCheck,
  'chevron-down': faChevronDown,
  'chevron-right': faChevronRight,
  history: faClockRotateLeft,
  copy: faCopy,
  door: faDoorOpen,
  download: faDownload,
  file: faFileLines,
  save: faFloppyDisk,
  minus: faMinus,
  send: faPaperPlane,
  pause: faPause,
  plus: faPlus,
  refresh: faRotate,
  stop: faStop,
  columns: faTableColumns,
  trash: faTrashCan,
  users: faUsers,
  'volume-on': faVolumeHigh,
  'volume-off': faVolumeXmark,
  close: faXmark,
  play: faPlay,
}

defineProps({ name: { type: String, required: true } })
</script>

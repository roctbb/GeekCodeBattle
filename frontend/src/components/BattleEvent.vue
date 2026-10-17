<template>
  <section
    v-if="event.visible"
    class="battle-event"
    :class="[event.kind, { 'is-compact': compact, 'has-motion': motion }]"
    role="status"
    aria-live="polite"
    :key="event.stamp"
  >
    <div class="event-slash" aria-hidden="true"></div>
    <div class="event-content">
      <CodeBattleMark class="event-medal" />
      <p class="event-kicker">
        CodeBattle ·
        {{ event.kind === 'first' ? 'Первое решение' : 'Событие раунда' }}
      </p>
      <h2>{{ event.title }}</h2>
      <p>{{ event.subtitle }}</p>
      <p v-if="event.positionText" class="event-position">
        {{ event.positionText }}
      </p>
      <strong v-if="event.points != null" class="event-score" aria-hidden="true"
        >+{{ displayPoints }} <small>очков за раунд</small></strong
      >
      <span v-if="event.points != null" class="visually-hidden"
        >{{ event.points }} очков за раунд</span
      >
      <p v-if="event.deltaText">{{ event.deltaText }}</p>
      <p v-if="event.streakText" class="event-streak">{{ event.streakText }}</p>
      <button
        type="button"
        class="btn btn-sm btn-outline-secondary"
        @click="$emit('dismiss')"
      >
        Продолжить
      </button>
    </div>
  </section>
</template>
<script setup>
import { ref, watch, onUnmounted } from 'vue'
import CodeBattleMark from './CodeBattleMark.vue'
const props = defineProps({
  event: { type: Object, required: true },
  motion: Boolean,
  compact: Boolean,
})
defineEmits(['dismiss'])
const displayPoints = ref(0)
let frame
watch(
  () => [props.event.stamp, props.event.visible, props.event.points, props.motion],
  () => {
    cancelAnimationFrame(frame)
    const target = Number(props.event.points || 0)
    if (!props.motion || !props.event.visible || target === 0) {
      displayPoints.value = target
      return
    }
    const started = performance.now()
    function tick(time) {
      const t = Math.min(1, (time - started) / 700)
      displayPoints.value = Math.round(target * (1 - (1 - t) ** 3))
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
  },
  { immediate: true },
)
onUnmounted(() => cancelAnimationFrame(frame))
</script>
<style scoped>
.battle-event {
  position: fixed;
  inset: 0;
  z-index: 1120;
  background:
    radial-gradient(ellipse at center, #93662d44, transparent 65%), #101215f5;
  display: grid;
  place-items: center;
  padding: 30px 20px;
  overflow: hidden;
}
.event-content {
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 900px;
}
.event-medal {
  width: 90px;
  height: 90px;
  margin: 0 auto 18px;
}
.event-kicker {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--app-brand);
}
.event-content h2 {
  font:
    700 clamp(42px, 7vw, 90px)/1.1 var(--app-font-heading);
  text-transform: uppercase;
  color: var(--app-brand);
  margin: 15px 0;
}
.event-content > p:not(.event-kicker) {
  color: #d5dce1;
  font-size: 14px;
}
.event-score {
  display: block;
  font:
    700 48px var(--app-font-heading);
  color: var(--app-brand);
  margin: 20px 0;
}
.event-score small {
  display: block;
  font:
    400 12px 'Manrope',
    sans-serif;
  color: var(--app-muted);
  margin-top: 5px;
}
.event-position {
  font:
    700 27px var(--app-font-heading) !important;
}
.event-content .btn {
  margin-top: 14px;
}
.event-slash {
  position: absolute;
  inset: -40%;
  background: repeating-linear-gradient(
    133deg,
    transparent 0,
    transparent 95px,
    #d9b6780c 96px,
    #d9b6780c 98px,
    transparent 99px,
    transparent 200px
  );
}
.has-motion .event-content {
  animation: event-appear 450ms cubic-bezier(0.2, 0.9, 0.2, 1.1);
}
.has-motion .event-slash {
  animation: slash-enter 600ms ease-out;
}
.has-motion .event-medal {
  animation: seal-turn 650ms ease-out;
}
.is-compact {
  inset: auto 18px 70px auto;
  max-width: min(440px, calc(100vw - 36px));
  padding: 23px 26px;
  border: 1px solid #ae8d54;
  box-shadow: 0 10px 40px #0008;
  background: #24251df5;
  pointer-events: none;
}
.is-compact .event-medal {
  width: 38px;
  height: 38px;
  margin-bottom: 8px;
}
.is-compact .event-content h2 {
  font-size: 30px;
  letter-spacing: 0;
  margin: 8px 0;
}
.is-compact .event-content p {
  font-size: 12px;
}
.is-compact .event-score {
  font-size: 30px;
  margin: 10px 0;
}
.is-compact button {
  pointer-events: auto;
}
.is-compact .event-kicker {
  font-size: 10px;
}
.is-compact .event-content .btn {
  font-size: 11px;
  margin-top: 8px;
}
@keyframes event-appear {
  from {
    opacity: 0;
    transform: translateY(36px) scale(0.87);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes slash-enter {
  from {
    transform: translateX(-25%);
  }
  to {
    transform: none;
  }
}
@keyframes seal-turn {
  from {
    transform: rotateY(100deg) scale(0.5);
  }
  to {
    transform: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
  }
}
@media (max-width: 540px) {
  .event-content h2 {
    font-size: 44px;
  }
  .event-medal {
    width: 64px;
    height: 64px;
  }
  .is-compact {
    padding: 18px;
    inset: auto 10px 62px auto;
    max-width: calc(100vw - 20px);
  }
}
</style>

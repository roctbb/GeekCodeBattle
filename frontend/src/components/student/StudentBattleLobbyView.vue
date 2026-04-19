<template>
  <section class="card shadow-sm border-0">
    <div class="card-body">
      <h2 class="h5 mb-3">Доступные сражения</h2>

      <div class="list-group" v-if="battles.length">
        <div
          v-for="b in battles"
          :key="b.id"
          class="list-group-item d-flex justify-content-between align-items-center gap-3"
        >
          <span>
            <strong class="d-block">{{ b.title }}</strong>
            <small class="text-muted">{{ b.status }}</small>
          </span>
          <button class="btn btn-primary btn-sm" @click="$emit('join-battle', b.id)">Вступить</button>
        </div>
      </div>

      <p class="text-muted mb-0" v-else>Сражений пока нет.</p>
    </div>
  </section>
</template>

<script setup>
defineProps({
  battles: { type: Array, default: () => [] }
})

defineEmits(['join-battle'])
</script>

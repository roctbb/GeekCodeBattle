<template>
  <section class="card shadow-sm border-0">
    <div class="card-body">
      <header class="lobby-head mb-4">
        <p class="lobby-eyebrow mb-1">Найди баттл</p>
        <h2 class="h4 mb-1">Доступные сражения</h2>
        <p class="text-muted mb-0">Выберите активный баттл и встаньте в очередь на раунд.</p>
      </header>

      <div class="lobby-grid" v-if="battles.length">
        <article v-for="b in battles" :key="b.id" class="lobby-card">
          <div>
            <strong class="d-block mb-1">{{ b.title }}</strong>
            <small class="status-pill">{{ b.status }}</small>
          </div>
          <button class="btn btn-primary btn-sm" @click="$emit('join-battle', b.id)">
            <i class="bi bi-box-arrow-in-right" aria-hidden="true"></i>
            Вступить
          </button>
        </article>
      </div>

      <p class="empty-text mb-0" v-else>Сражений пока нет.</p>
    </div>
  </section>
</template>

<script setup>
defineProps({
  battles: { type: Array, default: () => [] }
})

defineEmits(['join-battle'])
</script>

<style scoped>
.lobby-head {
  border: 1px solid #dbe5fa;
  border-radius: 14px;
  background: linear-gradient(145deg, #f9fbff 0%, #f3f8ff 100%);
  padding: 0.9rem;
}

.lobby-eyebrow {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #4d6190;
}

.lobby-grid {
  display: grid;
  gap: 0.7rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.lobby-card {
  border: 1px solid #dbe5fa;
  border-radius: 12px;
  background: #fbfdff;
  padding: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}

.lobby-card .btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 700;
  border: 1px solid #d6e2fc;
  background: #edf3ff;
  color: #234794;
}

.empty-text {
  padding: 0.9rem;
  border: 1px dashed #cad9f5;
  border-radius: 12px;
  color: #5f6d89;
  background: #f8fbff;
}

@media (max-width: 992px) {
  .lobby-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 576px) {
  .lobby-card {
    flex-direction: column;
    align-items: stretch;
  }

  .lobby-card .btn {
    justify-content: center;
  }
}
</style>

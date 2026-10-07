export const battleStatus = (value) =>
  ({
    draft: 'Черновик',
    lobby_open: 'Лобби открыто',
    running: 'Идёт игра',
    stopped: 'Остановлен',
    finished: 'Завершён',
  })[value] || 'Ожидание'
export const difficultyLabel = (value) =>
  ({ easy: 'Лёгкая', medium: 'Средняя', hard: 'Сложная' })[value] ||
  'Без уровня'
export const verdictLabel = (value) =>
  ({
    queued: 'Проверяется',
    accepted: 'Решение принято',
    wrong_answer: 'Есть ошибки',
    internal_error: 'Ошибка проверки',
    surrendered: 'Раунд пропущен',
  })[value] || 'Нет результата'
export const resultLabel = (value) =>
  ({
    win: 'Победа',
    loss: 'Раунд завершён',
    draw: 'Ничья',
    no_result: 'Без результата',
  })[value] || 'Решает'

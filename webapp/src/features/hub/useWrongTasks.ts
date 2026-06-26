// Единый источник — хук из lib/api (правильный путь /api/trainer/wrong-tasks,
// Bearer-токен, разворачивание {tasks}, dev-mock fallback). Локальный дубль удалён,
// чтобы не было рассинхрона пути/авторизации (была причина 404 /api/srez/...).
export { useWrongTasks } from '../../lib/api'

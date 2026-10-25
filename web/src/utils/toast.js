import { ref } from 'vue'

export const toastText = ref('')
let timer = null

export function toast(message) {
  toastText.value = message
  clearTimeout(timer)
  timer = setTimeout(() => {
    toastText.value = ''
  }, 1800)
}

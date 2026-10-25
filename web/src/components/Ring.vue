<script setup>
import { computed } from 'vue'

const props = defineProps({
  done: { type: Number, default: 0 },
  total: { type: Number, default: 20 },
  size: { type: Number, default: 76 }
})

const ticks = computed(() => {
  const n = props.total || 20
  const out = []
  for (let i = 0; i < n; i += 1) {
    const angle = ((-90 + i * (360 / n)) * Math.PI) / 180
    const on = i < props.done
    const ro = 46.5
    const ri = on ? 37.5 : 41.5
    out.push({
      x1: (50 + Math.cos(angle) * ri).toFixed(2),
      y1: (50 + Math.sin(angle) * ri).toFixed(2),
      x2: (50 + Math.cos(angle) * ro).toFixed(2),
      y2: (50 + Math.sin(angle) * ro).toFixed(2),
      on
    })
  }
  return out
})
</script>

<template>
  <svg
    viewBox="0 0 100 100"
    :width="size"
    :height="size"
    role="img"
    :aria-label="`进度 ${done}/${total}`"
  >
    <line
      v-for="(tick, index) in ticks"
      :key="index"
      :x1="tick.x1"
      :y1="tick.y1"
      :x2="tick.x2"
      :y2="tick.y2"
      :stroke="tick.on ? '#1F8A6B' : '#A9C4B8'"
      :stroke-width="tick.on ? 3.2 : 2"
      stroke-linecap="round"
    />
    <text
      x="50"
      y="50"
      text-anchor="middle"
      dominant-baseline="central"
      font-size="21"
      font-weight="600"
      fill="#0E5C46"
      font-family="-apple-system,PingFang SC,sans-serif"
    >
      {{ done }}
    </text>
    <text
      x="50"
      y="66"
      text-anchor="middle"
      font-size="8.5"
      fill="#7C8F87"
      font-family="-apple-system,PingFang SC,sans-serif"
    >
      / {{ total }}
    </text>
  </svg>
</template>

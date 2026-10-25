<script setup>
defineProps({
  name: { type: String, required: true },
  cls: { type: String, default: '' }
})
</script>

<template>
  <svg class="ico" :class="cls" aria-hidden="true">
    <use :href="`#${name}`" />
  </svg>
</template>

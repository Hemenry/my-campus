<script setup>
import { useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'

const router = useRouter()
</script>

<template>
  <header class="navbar">
    <button class="iconbtn" aria-label="返回" @click="router.push('/plaza')">
      <Icon name="i-back" />
    </button>
    <div class="navbar__t">页面不存在</div>
  </header>

  <div class="pad">
    <div class="empty" style="padding-top: 72px">
      <Icon name="i-file" />
      <div class="empty__t">这条路径没有内容</div>
      <div class="empty__s">可能链接过期了，也可能内容已被下架</div>
      <button class="btn btn--primary btn--sm empty__a" @click="router.push('/plaza')">回到广场</button>
    </div>
  </div>
</template>

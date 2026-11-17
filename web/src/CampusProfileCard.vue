<script setup lang="ts">
import ArdyPortrait from './ArdyPortrait.vue'
import type { CampusProfile } from './ardy'

defineProps<{ profile: CampusProfile }>()
</script>

<template>
  <div class="campus-profile-card">
    <div class="campus-profile-portrait">
      <ArdyPortrait :avatar="profile.avatar" />
    </div>
    <h3>{{ profile.display_name }}</h3>
    <p v-if="profile.career" class="campus-profile-career">{{ profile.career }}</p>
    <p v-if="profile.bio" class="campus-profile-bio">{{ profile.bio }}</p>
  </div>
</template>

<style scoped>
.campus-profile-card { display: grid; justify-items: center; text-align: center; gap: .5rem; padding: 1rem; overflow-wrap: anywhere; }
.campus-profile-card h3 { font-size: 1.25rem; }
.campus-profile-portrait { width: min(100%, 12rem); border-radius: 1rem; background: #eaf2ff; }
.campus-profile-career { color: var(--blue); font-weight: 650; }
.campus-profile-bio { white-space: pre-wrap; }
</style>

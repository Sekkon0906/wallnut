<script setup lang="ts">
import type { Rarity } from './ardy'

defineProps<{ step: number; rarity?: Rarity | null }>()
</script>

<template>
  <div class="nut-stage" :data-rarity="rarity" :data-step="step" aria-hidden="true">
    <span class="nut-halo"></span>
    <span v-if="step" :key="step" class="nut-burst">
      <i v-for="n in 12" :key="n" :style="{ '--angle': `${n * 30}deg`, '--spread': `${6.4 + (n % 3) * 0.8}rem` }"></i>
    </span>
    <span class="nut-shadow"></span>
    <span class="nut-body">
      <i class="nut-half nut-left"></i>
      <i class="nut-half nut-right"></i>
      <i class="nut-crack"></i>
    </span>
  </div>
</template>

<style scoped>
.nut-stage {
  --shine: #eff1ff;
  --glow: #bfdafb;
  --light-strength: .55;
  position: relative;
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  isolation: isolate;
  pointer-events: none;
}
.nut-stage[data-rarity="special"] { --shine: #b2ffe9; --glow: #48e1c3; --light-strength: .75; }
.nut-stage[data-rarity="epic"] { --shine: #f2caff; --glow: #cb7afa; --light-strength: .87; }
.nut-stage[data-rarity="legendary"] { --shine: #fff8cb; --glow: #ffba49; --light-strength: 1; }
.nut-halo {
  position: absolute;
  width: min(92%, 23rem);
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(circle, var(--shine), var(--glow) 26%, transparent 65%);
  opacity: .12;
  transform: scale(.65);
  transition: transform 420ms ease-out, opacity 320ms ease-out;
}
[data-step="1"] .nut-halo { opacity: calc(var(--light-strength) * .65); transform: scale(.81); }
[data-step="2"] .nut-halo { opacity: var(--light-strength); transform: scale(.98); }
[data-step="3"] .nut-halo { opacity: var(--light-strength); transform: scale(1.15); }
.nut-shadow {
  position: absolute;
  width: 10rem;
  height: 1.3rem;
  margin-top: 9.9rem;
  border-radius: 50%;
  background: #101127a6;
  filter: blur(9px);
}
.nut-body {
  width: 9.4rem;
  height: 8.5rem;
  position: relative;
  transform: rotate(-12deg);
  filter: drop-shadow(0 6px 8px #160c089c);
  transition: transform 300ms ease-out;
}
.nut-half {
  position: absolute;
  inset: 0;
  border-radius: 48% 52% 55% 45% / 56% 52% 48% 44%;
  background:
    repeating-radial-gradient(ellipse at 45% 104%, #71371300 0 8px, #66330c69 11px, #f2c07e36 14px, #71371300 17px),
    repeating-radial-gradient(ellipse at 54% -14%, transparent 0 8px, #6b330a57 11px, #f8d29833 13px, transparent 18px),
    radial-gradient(ellipse at 39% 24%, #f0c28e, #be7a40 44%, #965328 70%, #4d281b 100%);
  box-shadow: inset 0 4px 8px #ffe1b280, inset 0 -9px 13px #512713a8;
  transition: transform 380ms cubic-bezier(.16,.75,.26,1), opacity 380ms ease-in;
}
.nut-left { clip-path: polygon(0 0, 53% 0, 49% 17%, 58% 30%, 47% 43%, 55% 58%, 46% 72%, 52% 85%, 47% 100%, 0 100%); }
.nut-right { clip-path: polygon(53% 0, 100% 0, 100% 100%, 46.7% 100%, 51.7% 85%, 45.7% 72%, 54.7% 58%, 46.7% 43%, 57.7% 30%, 48.7% 17%); }
.nut-crack {
  position: absolute;
  inset: 0;
  background: var(--shine);
  clip-path: polygon(53% 0, 51% 17%, 61% 30%, 50% 43%, 58% 58%, 56% 59%, 46% 44%, 56% 30%, 47% 17%);
  opacity: 0;
  transition: opacity 250ms;
}
[data-step="1"] .nut-body { transform: rotate(-6deg) scale(1.025); }
[data-step="1"] .nut-crack { opacity: .85; }
[data-step="2"] .nut-body { transform: rotate(-14deg) scale(1.07); }
[data-step="2"] .nut-left { transform: translate(-4%, -1%) rotate(-4deg); }
[data-step="2"] .nut-right { transform: translate(4%, 2%) rotate(4deg); }
[data-step="3"] .nut-left { transform: translate(-105%, 54%) rotate(-55deg); opacity: 0; }
[data-step="3"] .nut-right { transform: translate(105%, 54%) rotate(58deg); opacity: 0; }
.nut-burst {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}
.nut-burst i {
  position: absolute;
  width: .7rem;
  aspect-ratio: 1;
  border-radius: 100%;
  background: var(--shine);
  box-shadow: 0 0 11px 3px var(--glow);
  animation: nut-spark 660ms ease-out both;
}
.nut-burst i:nth-child(3n) {
  width: .96rem;
  border-radius: 0;
  clip-path: polygon(50% 0, 61% 39%, 100% 50%, 61% 61%, 50% 100%, 39% 61%, 0 50%, 39% 39%);
}
@keyframes nut-spark {
  from { transform: rotate(var(--angle)) translateY(1.2rem) scale(.4); opacity: 0; }
  22% { opacity: 1; }
  to { transform: rotate(var(--angle)) translateY(var(--spread)) scale(.58); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .nut-stage *, .nut-burst i { animation: none; transition: none; }
  .nut-burst i { display: none; }
}
</style>

# Frontend Guidelines — labomatics Vue.js + Tailwind CSS

**Design System unifié pour Frontend + CLI. Inter pour l'app, Montserrat pour le branding uniquement.**

---

## Vue d'ensemble

- **Framework:** Vue.js 3 + Vue Router
- **Styling:** Tailwind CSS + custom tokens
- **State:** Pinia
- **Composants:** Réutilisables, accessibles (WCAG AA)
- **Dyslexie:** Mode optionnel via `data-font-mode="dyslexia"`

**Trois rôles utilisateurs, trois interfaces:**
1. **Élèves** — self-service, lecture quota (cartes, progress bars)
2. **Profs** — lancer TPs rapidement (héros section, listes, actions)
3. **Admins** — gestion promos, quotas (tables, dashboards, drill-down)

---

## Palette Tailwind

### Installation

Ajoute ces couleurs à `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    colors: {
      // Primaires
      primary: '#FF6B00',      // orange
      secondary: '#1F1F1F',    // acier (text/authority)

      // Sémantiques
      success: '#10B981',      // vert (succès)
      warning: '#F59E0B',      // ambre (attention)
      critical: '#EF4444',     // rouge (erreur)
      info: '#3B82F6',         // bleu (info)

      // Neutres
      cream: '#F8F4EB',        // fond clair/respiration
      light: '#F3F4F6',        // gris très léger
      border: '#D1D5DB',       // séparations
      text: {
        primary: '#1F1F1F',    // noir (jour)
        secondary: '#6B7280',  // gris (labels)
        light: '#9CA3AF',      // très léger (disabled)
      },
      bg: {
        primary: '#FFFFFF',    // blanc (jour)
        secondary: '#F8F4EB',  // crème
        tertiary: '#F3F4F6',   // gris léger
      },

      // Dark mode
      dark: {
        bg: {
          primary: '#1F1F1F',
          secondary: '#2A2A2A',
          tertiary: '#3F3F3F',
        },
        text: {
          primary: '#F8F4EB',
          secondary: '#B0B0B0',
        },
      },
    },
    fontFamily: {
      display: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
      body: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
      mono: ['"JetBrains Mono"', '"Courier New"', 'monospace'],
    },
  },
  plugins: [
    // Mode dyslexie-friendly
    ({ addVariant, matchVariant }) => {
      addVariant('dyslexia', '[data-font-mode="dyslexia"] &');
    },
  ],
};
```

---

## Typographie

### Scale & Usage

| Classe | Font | Size | Weight | Line-Height | Usage |
|--------|------|------|--------|-------------|-------|
| `text-h1` | Inter | 2rem | 700 | 1.2 | Page title (admin) |
| `text-h2` | Inter | 1.5rem | 700 | 1.3 | Section heading |
| `text-h3` | Inter | 1.25rem | 600 | 1.4 | Subsection |
| `text-lg` | Inter | 1.125rem | 400 | 1.6 | Descriptive text |
| `text-base` | Inter | 1rem | 400 | 1.6 | UI text (default) |
| `text-sm` | Inter | 0.875rem | 400 | 1.5 | Labels, hints, captions |
| `text-xs` | Inter | 0.75rem | 400 | 1.5 | Very small (timestamps) |
| `font-mono` | JetBrains Mono | 0.875rem | 400 | 1.4 | Code, quotas, numbers |

### Dyslexia-Friendly Adjustments

```css
[data-font-mode="dyslexia"] {
  letter-spacing: 0.05em;
  line-height: 1.8 !important;  /* up from 1.6 */
  word-spacing: 0.1em;
}

[data-font-mode="dyslexia"] .text-h1 {
  line-height: 1.4 !important;  /* headings tighter */
}
```

Implémentation dans `tailwind.config.js`:

```javascript
theme: {
  letterSpacing: {
    tighter: '-0.05em',
    tight: '-0.025em',
    normal: '0em',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',  // dyslexia
  },
  lineHeight: {
    normal: '1.6',
    dyslexia: '1.8',
    heading: '1.2',
  },
}
```

---

## Composants Vue Réutilisables

### Button

```vue
<template>
  <button 
    :class="[
      'px-4 py-2 rounded font-medium transition-all',
      'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
      variantClasses,
      sizeClasses,
    ]"
  >
    <slot />
  </button>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'primary' },
  size: { type: String, default: 'md' },
  disabled: Boolean,
})

const variantClasses = computed(() => ({
  primary: 'bg-primary text-white hover:bg-orange-700 disabled:bg-gray-300',
  secondary: 'border-2 border-primary text-primary hover:bg-primary hover:text-white',
  danger: 'bg-critical text-white hover:bg-red-600',
  ghost: 'text-primary hover:bg-cream',
}[variant]))

const sizeClasses = computed(() => ({
  sm: 'px-3 py-1 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
}[size]))
</script>
```

### Input

```vue
<template>
  <div class="relative">
    <label 
      v-if="label"
      :for="`input-${id}`"
      class="block text-sm font-medium text-text-primary mb-1"
    >
      {{ label }}
    </label>
    <input 
      :id="`input-${id}`"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-invalid="error ? 'true' : 'false'"
      :aria-describedby="error ? `error-${id}` : null"
      @input="$emit('update:modelValue', $event.target.value)"
      class="w-full px-3 py-2 border border-border rounded"
      :class="[
        error && 'border-critical bg-red-50',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-0',
        disabled && 'bg-light text-text-light cursor-not-allowed',
      ]"
    />
    <p 
      v-if="error"
      :id="`error-${id}`"
      class="mt-1 text-sm text-critical"
    >
      {{ error }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useId } from '@vueuse/core'

defineProps({
  modelValue: String,
  label: String,
  placeholder: String,
  error: String,
  disabled: Boolean,
})

defineEmits(['update:modelValue'])

const id = useId()
</script>
```

### Table (Admin)

```vue
<template>
  <div class="overflow-x-auto border border-border rounded">
    <table class="w-full text-sm text-text-primary">
      <thead class="bg-secondary text-white font-semibold">
        <tr>
          <th 
            v-for="col in columns"
            :key="col"
            class="px-4 py-3 text-left"
          >
            {{ col }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr 
          v-for="(row, idx) in rows"
          :key="idx"
          :class="[
            'border-t border-border hover:bg-cream transition-colors',
            idx % 2 === 0 && 'bg-bg-primary',
            idx % 2 === 1 && 'bg-bg-secondary',
          ]"
        >
          <td 
            v-for="(value, col) in row"
            :key="`${idx}-${col}`"
            class="px-4 py-3"
          >
            <slot 
              :name="`cell-${col}`"
              :value="value"
              :row="row"
            >
              {{ value }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  columns: Array,
  rows: Array,
})
</script>
```

### Status Badge

```vue
<template>
  <span 
    :class="[
      'inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium',
      statusClasses,
    ]"
    :aria-label="status"
  >
    <span :class="`w-2 h-2 rounded-full ${dotClasses}`" />
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true }, // 'running', 'stopped', 'error', etc.
  label: String,
})

const statusClasses = computed(() => ({
  running: 'bg-success/10 text-success',
  stopped: 'bg-warning/10 text-warning',
  error: 'bg-critical/10 text-critical',
  pending: 'bg-info/10 text-info',
}[props.status]))

const dotClasses = computed(() => ({
  running: 'bg-success',
  stopped: 'bg-warning',
  error: 'bg-critical',
  pending: 'bg-info',
}[props.status]))
</script>
```

### Quota Card (Élève)

```vue
<template>
  <div class="p-6 bg-bg-secondary rounded-lg border border-border">
    <div class="flex justify-between items-start mb-4">
      <h3 class="text-h3 text-text-primary">{{ title }}</h3>
      <span class="text-xs font-mono text-text-secondary">{{ used }} / {{ max }}</span>
    </div>
    
    <!-- Progress Bar -->
    <div class="w-full h-3 bg-light rounded-full overflow-hidden mb-2">
      <div 
        :style="{ width: `${percentage}%` }"
        :class="[
          'h-full transition-all',
          percentage < 75 && 'bg-success',
          percentage >= 75 && percentage < 90 && 'bg-warning',
          percentage >= 90 && 'bg-critical',
        ]"
      />
    </div>
    
    <!-- Percentage Label -->
    <p 
      :class="[
        'text-sm font-medium',
        percentage < 75 && 'text-success',
        percentage >= 75 && percentage < 90 && 'text-warning',
        percentage >= 90 && 'text-critical',
      ]"
    >
      {{ percentage }}% utilisé
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  used: Number,
  max: Number,
})

const percentage = computed(() => Math.round((props.used / props.max) * 100))
</script>
```

---

## Accessibilité (WCAG AA)

### Focus States
- **Tous les éléments interactifs:** Ring orange `2px`, offset `2px`
- **Keyboard navigation:** Ordre logique via `tabindex`, jamais `tabindex > 0`
- **Labels:** Chaque input associé via `<label for>` ou `aria-label`

```vue
<!-- ✅ Bon -->
<label for="email">Email:</label>
<input id="email" type="email" />

<!-- ✅ Bon (aria-label) -->
<button aria-label="Fermer modal">×</button>

<!-- ❌ Mauvais -->
<input type="email" placeholder="Email" />
```

### Color Contrast
- Texte/fond: **min 4.5:1** (WCAG AA)
- Graphiques: **min 3:1**
- Vérifier avec [Contrast Checker](https://webaim.org/resources/contrastchecker/)

### Alt Text & ARIA
```vue
<img 
  src="/diagramme.svg" 
  alt="Architecture réseau: élèves connectés via OpenWrt"
/>

<div role="status" aria-live="polite">
  {{ message }}
</div>
```

### Dark Mode
```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg-primary: #1F1F1F;
    --color-text-primary: #F8F4EB;
    /* etc. */
  }
}
```

---

## Dark Mode

Tailwind gère ça nativement. Dans `tailwind.config.js`:

```javascript
module.exports = {
  darkMode: 'media', // ou 'class' pour toggle manuel
  // ...
}
```

Utilisation:

```vue
<div class="bg-bg-primary dark:bg-dark-bg-primary text-text-primary dark:text-dark-text-primary">
  Content
</div>
```

**Note:** Si tu veux un toggle dark mode, ajoute une classe au `<html>`:

```vue
<html :class="{ dark: isDarkMode }">
```

---

## Dyslexie-Friendly Mode

### Activation

Dans `App.vue`:

```vue
<template>
  <div :data-font-mode="isDyslexiaMode ? 'dyslexia' : undefined">
    <header>
      <button 
        @click="isDyslexiaMode = !isDyslexiaMode"
        class="text-sm"
      >
        {{ isDyslexiaMode ? '🔤 Mode Normal' : '🔤 Mode Dyslexie' }}
      </button>
    </header>
    <router-view />
  </div>
</template>

<script setup>
import { ref } from 'vue'

const isDyslexiaMode = ref(localStorage.getItem('dyslexia-mode') === 'true')

watch(isDyslexiaMode, (val) => {
  localStorage.setItem('dyslexia-mode', val)
})
</script>
```

### CSS Variant en Tailwind

```javascript
// tailwind.config.js
plugins: [
  ({ addVariant }) => {
    addVariant('dyslexia', '[data-font-mode="dyslexia"] &');
  },
],
```

Utilisation:

```vue
<p class="text-base dyslexia:text-[102%] dyslexia:leading-[1.8] dyslexia:tracking-wider">
  Ceci s'agrandit et s'espacit en mode dyslexie.
</p>
```

---

## Structure Projet Recommandée

```
frontend/
├── src/
│   ├── components/
│   │   ├── Button.vue
│   │   ├── Input.vue
│   │   ├── Table.vue
│   │   ├── Badge.vue
│   │   ├── QuotaCard.vue
│   │   └── ...
│   ├── pages/
│   │   ├── admin/
│   │   │   ├── AdminLayout.vue
│   │   │   ├── StudentsList.vue       👈 START HERE
│   │   │   ├── StudentDetail.vue
│   │   │   └── QuotaManagement.vue
│   │   ├── teacher/
│   │   └── student/
│   ├── stores/
│   │   ├── students.js               (Pinia)
│   │   ├── quotas.js
│   │   └── ...
│   ├── styles/
│   │   ├── tailwind.css              (directives Tailwind)
│   │   └── dyslexia.css              (fallback)
│   ├── App.vue
│   ├── main.js
│   └── router.js                     (Vue Router)
├── tailwind.config.js                👈 Utilise palette ci-dessus
├── package.json
└── ...
```

---

## CLI Alignment

### Coloring avec Python

Pour que la CLI affiche les mêmes couleurs, utilise une palette partagée:

```python
# cli/src/display/colors.py
COLORS = {
    'primary': '#FF6B00',
    'secondary': '#1F1F1F',
    'success': '#10B981',
    'warning': '#F59E0B',
    'critical': '#EF4444',
    'info': '#3B82F6',
}

# Utile pour rich.table, rich.console
from rich.console import Console
from rich.table import Table
from rich.style import Style

console = Console()
table = Table(title='Students', style=Style(color=COLORS['secondary']))

# Ajout de lignes avec couleur status
table.add_row(
    '18',
    'Jean D.',
    '[green]✓ Running[/green]',  # rich markup
    '50%',
)
```

---

## Checklist pour Développeurs

- [ ] Tailwind config avec palette
- [ ] Composants Vue basiques (Button, Input, Table)
- [ ] Focus states sur tout interactif
- [ ] Tests contrast (WCAG AA min)
- [ ] Dark mode testé
- [ ] Dyslexie-friendly variant prêt
- [ ] Labels ARIA sur inputs
- [ ] Alt text sur images/diagrammes
- [ ] Keyboard navigation complète
- [ ] CLI couleurs synchronisées

---

**Dernière mise à jour:** 2026-07-26  
**Statut:** Actif

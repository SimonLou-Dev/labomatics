# labomatics — Guide d'Identité Visuelle

**Automation industrielle, précision de laboratoire, culture expérimentale.**

---

## Palette de Couleurs

| Couleur | Hex | Usage | Notes |
|---------|-----|-------|-------|
| **Orange Primaire** | `#FF6B00` | Accent principal, logos, CTA | Énergie industrielle, audacieux |
| **Orange Chaud** | `#FFA500` | Variations, texte sur fond sombre | Accessible, secondaire |
| **Rouille** | `#B8561F` | Détails, accents | Matérialité, authenticité |
| **Acier Sombre** | `#1F1F1F` | Texte, arrière-plans | Technique, précis |
| **Crème** | `#F8F4EB` | Arrière-plans clairs | Respiration visuelle |

**Mode Sombre:**
- Orange Primaire → `#FF8C00` (plus clair sur fonds sombres)
- Arrière-plans → `#2A2A2A` (pas du noir pur)

---

## Typographie

### Display / Logo
- **Police:** Montserrat
- **Poids:** Gras (700)
- **Google Fonts:** Oui
- **Stack fallback:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **Usage:** Titres, logos, branding

### Corps de Texte
- **Police:** Inter
- **Poids:** Régulier (400)
- **Google Fonts:** Oui
- **Stack fallback:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`
- **Usage:** Articles, documentation, texte UI
- **Hauteur de ligne:** 1.6
- **Largeur max:** 65 caractères pour lisibilité

### Code / Terminal
- **Police:** JetBrains Mono
- **Poids:** Régulier (400) / Gras (600)
- **Google Fonts:** Oui
- **Stack fallback:** `'Courier New', monospace`
- **Usage:** Blocs de code, exemples CLI, snippets techniques

---

## Système de Logo

### Logo Principal
**Fichier:** `labomatics-logo-primary.svg`

**Composition:**
- "lab" en gris acier (#4A4A4A)
- O remplacé par un engrenage mécanique
- "matics" en gris acier (#4A4A4A)
- Fiole (Erlenmeyer) + bras robot en orange (#FF6B00)

**Dimensions:** 800×200 (ratio 16:4)

**Usage:**
- Sections héros
- Communications officielles
- Grand format (en-têtes web, documents)
- Toujours maintenir minimum 20px de padding autour du logo

**Couleurs dans le SVG:**
- Texte: `#4A4A4A` (acier)
- Engrenage: `#FF6B00` (orange primaire)
- Contours engrenage: `#FF6B00`
- Fiole/bras: `#FF6B00`

### Icon / Favicon
**Fichier:** `labomatics-logo-icon.svg`

**Composition:**
- Engrenage (O) comme élément central
- Fiole Erlenmeyer intégrée
- Détails du bras robot

**Dimensions:** 200×200 (carré, 1:1)

**Usage:**
- Favicon (32×32, 16×16)
- Icônes d'application
- Avatars réseaux sociaux
- Petites marques contextuelles
- Verrouillage de logo quand l'espace est limité

**Reconnaissable:** Identité de marque maintenue à 32px et plus petit

---

## Directives d'Utilisation du Logo

### Espacement & Respiration
- Minimum 20px de padding sur tous les côtés
- Ne pas rogner ou modifier les proportions
- Ne pas pivoter, incliner ou distordre
- Ne pas appliquer d'effets (ombres, lueurs) sauf approbation explicite

### Variations de Couleur
- **Primaire:** Couleur complète (orange #FF6B00 + acier #4A4A4A)
- **Monochrome:** Orange uniquement (contraintes monocouleur)
- **Inversé:** Blanc/crème sur fonds sombres
- Ne jamais inverser les couleurs arbitrairement

### Dimensionnement
- **Minimum:** 100px de largeur pour logo principal (lisibilité du texte)
- **Icône:** 32px minimum (taille favicon)
- **Web:** Redimensionner au besoin avec SVG moderne (pas de rastérisation)

### Arrière-plans
- **Arrière-plans clairs:** Utiliser couleur primaire telle quelle
- **Arrière-plans sombres:** Utiliser `#FF8C00` pour meilleur contraste
- **Arrière-plans texturés:** Assurer ratio de contraste 4.5:1

---

## Exemples d'Utilisation

### Web
```html
<!-- Bannière héros -->
<img src="/branding/labomatics-logo-primary.svg" alt="labomatics" width="400" />

<!-- Favicon -->
<link rel="icon" type="image/svg+xml" href="/branding/labomatics-logo-icon.svg" />

<!-- Logo de navigation -->
<img src="/branding/labomatics-logo-icon.svg" alt="labomatics" width="48" />
```

### Documentation
- Utiliser logo principal en haut du README
- Utiliser icône en navigation/breadcrumbs
- Garder minimum 20px de padding

### Réseaux Sociaux
- Avatar: Utiliser icône (200×200)
- Couverture: Utiliser logo principal centré
- Posts: S'assurer que orange #FF6B00 ressort sur miniatures

### Impression
- Utiliser exports SVG haute résolution (PDF via Illustrator/Inkscape)
- Pour raster: Exporter à minimum 300 DPI
- Maintenir exactitude couleur #FF6B00 (match Pantone si possible)

---

## Quand Utiliser Quel Logo

| Contexte | Logo | Raison |
|----------|------|--------|
| Héros site web | Principal | Message de marque complet |
| Favicon/icône | Icône | Reconnaissable à petite taille |
| Avatar réseaux | Icône | Carré, clair à 200×200 |
| En-tête documentation | Principal | Professionnel, officiel |
| Barre de navigation | Icône | Compact, lisibilité |
| Carte de visite | Icône ou petit principal | Espace limité |
| Signature email | Icône | Intégré, professionnel |
| Branding outil CLI | Icône | Propre, minimal |

---

## Mode Sombre

### Couleurs en Mode Sombre
- Orange Primaire: Utiliser `#FF8C00` au lieu de `#FF6B00` (meilleur contraste)
- Acier Sombre: `#1F1F1F` pour texte sur clair, `#F8F4EB` pour texte sur sombre
- Rouille: `#B8561F` reste stable

### Logo en Mode Sombre
- Icône: Orange ressort bien, pas de changement nécessaire
- Principal: Texte acier peut nécessiter version plus claire (`#B0B0B0`) sur arrière-plans sombres

---

## Stratégie des Fallback Fonts

**Pourquoi les fallbacks sont importants:**
- Utilisateurs n'ont pas Google Fonts en cache
- Documentation hors ligne doit rester lisible
- Performance: Les fonts système chargent instantanément

**Philosophie de la stack:**
1. Choix primaire (Google Fonts)
2. Fonts système modernes (`-apple-system`, `BlinkMacSystemFont`, `Segoe UI`)
3. Fallbacks legacy (`Arial`, `sans-serif`)

**Tester les fallbacks:**
```css
/* Charger Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Inter:wght@400&family=JetBrains+Mono:wght@400;600&display=swap');

/* Stack fallback (critique pour docs hors ligne) */
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```

---

## Versionnage

| Version | Date | Changements |
|---------|------|-------------|
| 1.0 | 2026-07-24 | Release initiale. Display Montserrat, body Inter, code JetBrains Mono. Orange #FF6B00 primaire. |

---

## Fichiers

```
docs/branding/
├── BRANDING.md                      (ce fichier)
├── labomatics-logo-primary.svg      (800×200, logo complet)
├── labomatics-logo-icon.svg         (200×200, icône/favicon)
```

---

## Questions & Contributions

Pour questions branding, consulter ce guide. Si quelque chose n'est pas clair, ouvrir une issue GitHub avec label `branding`.

---

**Dernière mise à jour:** 2026-07-24  
**Statut:** Actif

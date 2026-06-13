# Anobis Frontend | Banking Investigation Workspace

The professional frontend for the **Anobis** document fraud detection platform, built with **Astro 6.4** and **Tailwind CSS v4**.

## 🚀 Overview

This frontend is designed as a high-density, enterprise-grade workspace for banking auditors and underwriters. It prioritizes forensic clarity, evidence presentation, and cross-document validation.

## 🛠️ Tech Stack

- **Framework**: [Astro 6.4](https://astro.build/)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/) (Vite Plugin)
- **Icons**: [Lucide Astro](https://lucide.dev/guide/astro)
- **Type Safety**: TypeScript

## 📂 Project Structure

```text
src/
├── components/        # Reusable Astro components (MetricsCard, etc.)
├── layouts/           # Main Anobis layout shell with sidebar
├── pages/             # Route handlers
│   ├── index.astro    # Dashboard
│   ├── investigations.astro # Audit trail
│   ├── new-investigation.astro # Upload flow
│   └── investigate/   # Forensic workspace
└── styles/            # Tailwind v4 entry point
```

## 🧞 Commands

| Command | Action |
| :--- | :--- |
| `npm install` | Installs dependencies |
| `npm run dev` | Starts local dev server at `localhost:4321` |
| `npm run build` | Build for production to `./dist/` |
| `npm run preview` | Preview production build locally |

## 🎨 Design Principles

- **Professionalism**: Uses a clean "Banking Blue" and Slate palette.
- **Density**: High information density for efficient forensic review.
- **Clarity**: Status-coded findings (🟢 Verified, 🟡 Suspicious, 🔴 Fraudulent).
- **Evidence-First**: Every UI element is tied to specific forensic indicators.

## 🔗 Backend Integration

The frontend expects a FastAPI backend running at `http://localhost:8000`. You can configure the API endpoint in your `.env` file (see `.env.example`).

---

**Anobis | Professional Banking Forensics**

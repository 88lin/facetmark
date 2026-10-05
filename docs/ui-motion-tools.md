# UI and motion tools

Prepared on 2026-10-05. This setup adds tooling and a component registry; it does
not change the workbench's appearance or import an animation engine at runtime.

## Rare UI

`frontend/components.json` registers `@rare-ui` for this React/Vite application.
The TypeScript and Vite `@/` aliases both resolve to `frontend/src`.

After selecting a component for a concrete design, run from `frontend`:

```powershell
npx -y shadcn@latest add @rare-ui/component-name
```

Replace `component-name` with a verified name from
[the component catalog](https://rareui.com/components). Registry components and
their dependencies are added on demand; none has been selected or copied into
Facetmark yet. The configured `utils` alias is the future destination for the
component registry's utility dependency, not an existing application import.
Do not install the upstream Next.js demo application into this Vite project.

Inspect component dependencies and imports before adding them. Preserve the
existing design tokens and adapt copied components to the workbench. Components
using Motion can keep Motion; GSAP skills do not require converting them.

Rare UI uses **MIT + Commons Clause + attribution**, not unrestricted MIT.
When shipping a component, retain its copyright/license notices and add a visible
Rare UI link in the application credits or project README. The license prohibits
selling or redistributing the components as a component library or bundle.
See [the upstream license](https://github.com/swamimalode07/rare-ui/blob/main/LICENSE).

## GSAP skills

The user's global tool installation contains the eight official GSAP skills.
They provide implementation guidance; `gsap` and `@gsap/react` are separate npm
runtime packages and have not been added to this application just for installing
skills. Add runtime dependencies only when a chosen interaction needs them.

Use the core skill and the relevant specialist skill as needed. Generic visual
redesign continues through Impeccable. Simple transitions can use CSS, and
existing animation engines should be preserved. Respect reduced-motion settings
and clean up animations on navigation or component unmount.

## Oil Motion

Oil Motion is available globally for converting generated or existing videos and
frame sequences into interactive web assets. It is intended for subject motion,
product transformations and scene transitions. Ordinary workbench panels and
button feedback do not require this media pipeline.

Local media processing has a separate Python environment and uses the installed
FFmpeg tools. AI image/video generation requires a ZenMux key configured through
the skill's local credential page at first use; installation does not call the
generation service.

The machine-specific entry points and maintenance commands are documented at
`C:\Users\Computer\.agents\external\UI-MOTION-TOOLS.md`.

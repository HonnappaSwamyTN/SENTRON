# SENTRON Official Presentation Website

Production-quality static presentation website for **SENTRON** (Local-First AI-Agent Action Governance and Windows Stability Monitoring), ready for deployment on **GitHub Pages**.

---

## 1. Directory Structure

```
website/
├── index.html                  # Semantic, accessible HTML5 single-page site with all 10 sections
├── css/
│   └── style.css               # Vanilla CSS design system (Charcoal, Warm White, Gold Accents)
├── js/
│   └── main.js                 # GitHub Releases API checker, interactive simulations, accessible UI
├── assets/
│   ├── sentron.png             # High-resolution raster brand mark (256x256)
│   └── icons/
│       ├── shield.svg          # Precision vector SVG brand mark with gold glow
│       └── sentron.ico         # Multi-resolution Windows icon (16-256px)
└── README.md                   # This deployment & maintenance guide
```

---

## 2. Local Preview Instructions

You can preview the website locally using any standard HTTP static server:

### Option A: Python Built-In HTTP Server (Recommended)
From the repository root:
```powershell
python -m http.server 8000 --directory website
```
Then open your browser to [http://localhost:8000](http://localhost:8000).

### Option B: Node.js / npx
```powershell
npx -y serve website
```

All asset and script links use relative paths (`./css/style.css`, `./js/main.js`, `./assets/...`), ensuring identical behavior across `localhost`, custom domains, and GitHub Pages subpaths (`https://<username>.github.io/<repo>/`).

---

## 3. GitHub Pages Deployment Setup

A dedicated GitHub Actions workflow is provided at [`.github/workflows/deploy-pages.yml`](../.github/workflows/deploy-pages.yml).

### Step-by-Step Setup:
1. Push your repository to GitHub:
   ```powershell
   git push origin main
   ```
2. Navigate to your repository settings on GitHub:
   `https://github.com/HonnappaSwamyTN/SENTRON/settings/pages`
3. Under **Build and deployment**:
   - **Source**: Select **GitHub Actions**.
4. The deployment workflow triggers automatically whenever changes are pushed to `website/**` or when manually triggered via **Actions → Deploy SENTRON Website to GitHub Pages → Run workflow**.
5. Once complete, your site will be live at:
   `https://honnappaswamytn.github.io/SENTRON/`

---

## 4. Release Publishing & Installer Download Target

The website is configured to deliver the official Windows installer named **`SENTRON_Setup.exe`**.

### How Dynamic Asset Detection Works:
`website/js/main.js` checks the GitHub Releases API (`https://api.github.com/repos/HonnappaSwamyTN/SENTRON/releases/latest`) on page load:
- **When a published release asset exists:** The "Download for Windows" button automatically binds to the direct asset URL (`.../releases/latest/download/SENTRON_Setup.exe`), turns the status badge green, and displays verified size and version tags.
- **Before the release is published:** The download button displays `"Installer Coming Soon"` / `"View GitHub Releases"` and links safely to `https://github.com/HonnappaSwamyTN/SENTRON/releases` with an honest note explaining that publication is in progress. **It never links to a 404 or nonexistent file.**

### How to Publish the Release on GitHub:
1. Build the installer locally:
   ```powershell
   python packaging/build_installer.py
   ```
   This generates `dist/installer/SENTRON_Setup.exe` and outputs its SHA-256 hash.
2. In your GitHub repository:
   - Go to **Releases → Draft a new release**.
   - Create a tag: `v1.0.0` (matching `MyAppVersion` in `installer.iss`).
   - Title: `SENTRON v1.0.0 — Production Release`.
   - Attach file: Drag and drop `dist/installer/SENTRON_Setup.exe`.
   - Add the SHA-256 verification hash to the release notes:
     ```
     SHA-256: E3B64FB91389C6BACEB427B0F6F34AC5C4B61CD7D8879F585899272F293482A4
     ```
   - Click **Publish release**.
3. Refresh your live website: the download button will immediately detect the live asset!

---

## 5. Architectural Boundaries & Safe Practice (WEBSITE_SCOPE.md)

In accordance with [`WEBSITE_SCOPE.md`](../SENTRON_Developer_Starter/WEBSITE_SCOPE.md):
- The website is strictly an educational presentation layer.
- It contains **zero remote telemetry scripts** and **zero advertising trackers**.
- All interactive policy demonstrations are explicitly labeled as `SYNTHETIC DEMO SIMULATION`.
- The website never claims to inspect or control the visitor's hardware.

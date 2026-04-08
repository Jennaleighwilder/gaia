# How to Create the PDF Manual from `MANUAL.html`

The full manual is **`MANUAL.html`**, styled for print and screen. To produce a **high-quality PDF** suitable for binding or archival:

## Option A — Google Chrome or Microsoft Edge (recommended)

1. Copy **`MANUAL.html`** to the target computer (it loads fonts from Google Fonts when online; for fully offline use, open once while connected so fonts cache, or print with fallback fonts).  
2. Open **`MANUAL.html`** in **Chrome** or **Edge**.  
3. Press **Ctrl+P** (Windows) or **Cmd+P** (Mac).  
4. Destination: **Save as PDF**.  
5. Set **Margins** to **Default** or **Minimum**; enable **Background graphics** so headings and borders print.  
6. Paper size: **Letter** (US) or **A4** per your standard.  
7. Save as e.g. `Ferry_County_Field_System_Manual.pdf`.

## Option B — macOS Safari

1. Open **`MANUAL.html`** in Safari.  
2. **File → Export as PDF…**

## Option C — Automated (developers)

If `wkhtmltopdf` or `weasyprint` is installed in your environment, you can script conversion; the HTML uses `@media print` rules for page breaks. The browser method above is preferred for font fidelity.

---

**Tip:** For a formal handoff, print double-sided, punch three holes, and store with **DEPLOYMENT.md** and **SPECIFICATION.md** in a labeled county binder.

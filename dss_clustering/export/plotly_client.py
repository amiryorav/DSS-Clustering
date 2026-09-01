"""Browser-side Plotly PNG/PDF download — no image bytes through Reflex state."""

from __future__ import annotations

import json

# Plotly.toImage runs in the page. 3D PDF is a JPEG wrapped in a one-page PDF
# because plotly.js cannot export gl3d to PDF. 2D (dendrogram) uses native PDF.
DSS_EXPORT_PLOTLY_JS = r"""
window.dssExportPlotly = async function (rootId, fmt, stem) {
  const root = document.getElementById(rootId);
  const gd = (root || document).querySelector('.js-plotly-plot, .plotly-graph-div');
  if (!gd || typeof Plotly === 'undefined' || typeof Plotly.toImage !== 'function') {
    console.error('Plot export: plot is not ready.');
    return;
  }
  const wantPdf = String(fmt).toLowerCase() === 'pdf';
  const width = Math.max(
    Math.round((gd._fullLayout && gd._fullLayout.width) || gd.clientWidth || 1200),
    400
  );
  const height = Math.max(
    Math.round((gd._fullLayout && gd._fullLayout.height) || gd.clientHeight || 800),
    300
  );
  const stamp = (() => {
    const d = new Date();
    const p = (n) => String(n).padStart(2, '0');
    return (
      `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_` +
      `${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
    );
  })();
  const filename = `${stem}_${stamp}.${wantPdf ? 'pdf' : 'png'}`;
  const is3d = !!(gd._fullLayout && gd._fullLayout.scene);

  const pageIsDark = () => {
    const html = document.documentElement;
    const radix = document.querySelector('.radix-themes');
    const themed = radix || html;
    if (themed.classList.contains('light')) return false;
    if (themed.classList.contains('dark')) return true;
    const theme = html.getAttribute('data-theme') || html.getAttribute('data-appearance') || '';
    if (theme === 'light') return false;
    if (theme === 'dark') return true;
    let node = gd;
    while (node && node !== document.documentElement) {
      const bg = getComputedStyle(node).backgroundColor || '';
      const m = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([.\d]+))?/);
      if (m && (m[4] === undefined || Number(m[4]) > 0.05)) {
        const lum = 0.2126 * +m[1] + 0.7152 * +m[2] + 0.0722 * +m[3];
        return lum < 140;
      }
      node = node.parentElement;
    }
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  };

  const themedFigure = () => {
    const layout = JSON.parse(JSON.stringify(gd.layout || {}));
    if (is3d && gd._fullLayout && gd._fullLayout.scene && gd._fullLayout.scene.camera) {
      layout.scene = layout.scene || {};
      layout.scene.camera = JSON.parse(JSON.stringify(gd._fullLayout.scene.camera));
    }
    const dark = pageIsDark();
    const paper = dark ? '#111113' : '#ffffff';
    const ink = dark ? '#e4e4e7' : '#1f1f1f';
    const grid = dark ? '#3f3f46' : '#e4e4e7';
    layout.paper_bgcolor = paper;
    layout.plot_bgcolor = paper;
    layout.font = Object.assign({}, layout.font || {}, { color: ink });
    const patchAxis = (axis) => {
      if (!axis || typeof axis !== 'object') return;
      axis.gridcolor = grid;
      axis.zerolinecolor = grid;
      axis.linecolor = ink;
      axis.tickfont = Object.assign({}, axis.tickfont || {}, { color: ink });
      if (axis.title && typeof axis.title === 'object') {
        axis.title.font = Object.assign({}, axis.title.font || {}, { color: ink });
      }
      axis.color = ink;
    };
    patchAxis(layout.xaxis);
    patchAxis(layout.yaxis);
    if (layout.scene) {
      layout.scene.bgcolor = paper;
      ['xaxis', 'yaxis', 'zaxis'].forEach((key) => {
        layout.scene[key] = layout.scene[key] || {};
        patchAxis(layout.scene[key]);
        layout.scene[key].backgroundcolor = paper;
        layout.scene[key].showbackground = true;
      });
    }
    return { data: gd.data, layout: layout };
  };

  const downloadUrl = (url, name, revoke) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    a.remove();
    if (revoke) {
      setTimeout(() => URL.revokeObjectURL(url), 1500);
    }
  };

  const jpegToPdfObjectUrl = (jpegBytes, imgW, imgH) => {
    const encoder = new TextEncoder();
    const chunks = [];
    const offsets = [0];
    let pos = 0;
    const addText = (text) => {
      const part = encoder.encode(text);
      chunks.push(part);
      pos += part.length;
    };
    const addBytes = (bytes) => {
      chunks.push(bytes);
      pos += bytes.length;
    };
    const maxSide = 792;
    const scale = Math.min(1, maxSide / Math.max(imgW, imgH));
    const pageW = Math.max(1, Math.round(imgW * scale));
    const pageH = Math.max(1, Math.round(imgH * scale));
    addText('%PDF-1.4\n');
    offsets[1] = pos;
    addText('1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n');
    offsets[2] = pos;
    addText('2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n');
    offsets[3] = pos;
    addText(
      `3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageW} ${pageH}] ` +
        `/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >> endobj\n`
    );
    offsets[4] = pos;
    addText(
      `4 0 obj << /Type /XObject /Subtype /Image /Width ${imgW} /Height ${imgH} ` +
        `/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode ` +
        `/Length ${jpegBytes.length} >> stream\n`
    );
    addBytes(jpegBytes);
    addText('\nendstream endobj\n');
    offsets[5] = pos;
    const content = `q ${pageW} 0 0 ${pageH} 0 0 cm /Im0 Do Q\n`;
    addText(`5 0 obj << /Length ${content.length} >> stream\n${content}endstream endobj\n`);
    const xrefPos = pos;
    addText('xref\n0 6\n0000000000 65535 f \n');
    for (let i = 1; i <= 5; i++) {
      addText(`${String(offsets[i]).padStart(10, '0')} 00000 n \n`);
    }
    addText(`trailer << /Size 6 /Root 1 0 R >>\nstartxref\n${xrefPos}\n%%EOF`);
    const total = chunks.reduce((n, c) => n + c.length, 0);
    const out = new Uint8Array(total);
    let o = 0;
    for (const c of chunks) {
      out.set(c, o);
      o += c.length;
    }
    return URL.createObjectURL(new Blob([out], { type: 'application/pdf' }));
  };

  try {
    const fig = themedFigure();
    if (!wantPdf) {
      const url = await Plotly.toImage(fig, {
        format: 'png',
        width: width,
        height: height,
        scale: 2,
      });
      downloadUrl(url, filename, false);
      return;
    }
    if (!is3d) {
      const url = await Plotly.toImage(fig, {
        format: 'pdf',
        width: width,
        height: height,
      });
      downloadUrl(url, filename, false);
      return;
    }
    const jpegUrl = await Plotly.toImage(fig, {
      format: 'jpeg',
      width: width,
      height: height,
      scale: 2,
    });
    const raw = atob(jpegUrl.split(',')[1]);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) {
      bytes[i] = raw.charCodeAt(i);
    }
    const imgW = Math.round(width * 2);
    const imgH = Math.round(height * 2);
    const pdfUrl = jpegToPdfObjectUrl(bytes, imgW, imgH);
    downloadUrl(pdfUrl, filename, true);
  } catch (err) {
    console.error('Plot export failed', err);
  }
};
"""


def export_plot_script(root_id: str, fmt: str, stem: str) -> str:
    """JS that downloads one on-screen Plotly figure without a backend round-trip."""
    return (
        DSS_EXPORT_PLOTLY_JS
        + "\nvoid window.dssExportPlotly("
        + json.dumps(root_id)
        + ", "
        + json.dumps(fmt)
        + ", "
        + json.dumps(stem)
        + ");"
    )

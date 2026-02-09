// canvas-utils.js — Quadtree hit-testing, shape drawing helpers, DPR handling

import { MAX_DPR } from './constants.js';

/**
 * Setup a canvas for high-DPI rendering.
 * Returns the 2D context and effective DPR used.
 */
export function setupCanvas(canvas, width, height) {
  const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return { ctx, dpr };
}

/**
 * Install a ResizeObserver on a container element to keep the canvas sized.
 * Returns a cleanup function.
 */
export function observeResize(container, canvas, onResize) {
  const ro = new ResizeObserver(entries => {
    for (const entry of entries) {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        const { ctx, dpr } = setupCanvas(canvas, width, height);
        onResize(width, height, ctx, dpr);
      }
    }
  });
  ro.observe(container);
  return () => ro.disconnect();
}

/**
 * Find the closest node to a point using d3.quadtree.
 * Accounts for zoom transform.
 */
export function findNodeAtPoint(quadtree, x, y, radius) {
  if (!quadtree) return null;
  return quadtree.find(x, y, radius) || null;
}

/**
 * Draw a circle on canvas.
 */
export function drawCircle(ctx, x, y, r, fillColor, strokeColor, lineWidth) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  if (fillColor) {
    ctx.fillStyle = fillColor;
    ctx.fill();
  }
  if (strokeColor) {
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = lineWidth || 1;
    ctx.stroke();
  }
}

/**
 * Draw a rounded rectangle on canvas (for EIP nodes).
 */
export function drawRoundedRect(ctx, x, y, w, h, r, fillColor, strokeColor, lineWidth) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
  if (fillColor) {
    ctx.fillStyle = fillColor;
    ctx.fill();
  }
  if (strokeColor) {
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = lineWidth || 1;
    ctx.stroke();
  }
}

/**
 * Draw a diamond shape on canvas (for fork nodes).
 */
export function drawDiamond(ctx, x, y, size, fillColor, strokeColor, lineWidth) {
  const half = size / 2;
  ctx.beginPath();
  ctx.moveTo(x, y - half);
  ctx.lineTo(x + half, y);
  ctx.lineTo(x, y + half);
  ctx.lineTo(x - half, y);
  ctx.closePath();
  if (fillColor) {
    ctx.fillStyle = fillColor;
    ctx.fill();
  }
  if (strokeColor) {
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = lineWidth || 1;
    ctx.stroke();
  }
}

/**
 * Draw a triangle shape on canvas (for magicians nodes).
 */
export function drawTriangle(ctx, x, y, size, fillColor, strokeColor, lineWidth) {
  const half = size / 2;
  const h = size * 0.866; // equilateral triangle height
  ctx.beginPath();
  ctx.moveTo(x, y - h * 0.6);
  ctx.lineTo(x + half, y + h * 0.4);
  ctx.lineTo(x - half, y + h * 0.4);
  ctx.closePath();
  if (fillColor) {
    ctx.fillStyle = fillColor;
    ctx.fill();
  }
  if (strokeColor) {
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = lineWidth || 1;
    ctx.stroke();
  }
}

/**
 * Draw an arrowhead at the end of a line segment.
 */
export function drawArrow(ctx, fromX, fromY, toX, toY, headSize, color) {
  const dx = toX - fromX;
  const dy = toY - fromY;
  const angle = Math.atan2(dy, dx);
  ctx.beginPath();
  ctx.moveTo(toX, toY);
  ctx.lineTo(
    toX - headSize * Math.cos(angle - Math.PI / 6),
    toY - headSize * Math.sin(angle - Math.PI / 6),
  );
  ctx.lineTo(
    toX - headSize * Math.cos(angle + Math.PI / 6),
    toY - headSize * Math.sin(angle + Math.PI / 6),
  );
  ctx.closePath();
  ctx.fillStyle = color || '#88aaff';
  ctx.fill();
}

/**
 * Check if a point (in world coordinates) is within viewport bounds.
 */
export function isInViewport(x, y, transform, width, height, margin) {
  const m = margin || 50;
  const sx = transform.applyX(x);
  const sy = transform.applyY(y);
  return sx >= -m && sx <= width + m && sy >= -m && sy <= height + m;
}

/**
 * Get visible nodes from a set of all nodes given a viewport transform.
 */
export function getVisibleNodes(nodes, transform, width, height, margin) {
  const m = margin || 50;
  // Invert transform to get world-space viewport bounds
  const x0 = transform.invertX(-m);
  const x1 = transform.invertX(width + m);
  const y0 = transform.invertY(-m);
  const y1 = transform.invertY(height + m);

  const visible = [];
  for (const node of nodes) {
    if (node.x >= x0 && node.x <= x1 && node.y >= y0 && node.y <= y1) {
      visible.push(node);
    }
  }
  return visible;
}

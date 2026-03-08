/* ═══════════════════════════════════════════════
   BoutikManager — Factures dynamiques v2
   Supporte la création ET la modification
   ═══════════════════════════════════════════════ */

'use strict';

// CURRENCY et EXISTING_ITEMS sont injectés par le template HTML

let productsData = [];
let itemCounter  = 0;

function fmtNum(v) {
  return (parseFloat(v) || 0).toFixed(2).replace('.', ',');
}

function escHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );
}

async function loadProducts() {
  try {
    const res = await fetch('/api/produits');
    productsData = await res.json();
  } catch (e) {
    productsData = [];
  }
}

function updateSubtotal(rowId) {
  const price    = parseFloat((document.getElementById(`price-${rowId}`)?.value || '0').replace(',', '.')) || 0;
  const qty      = parseInt(document.getElementById(`qty-${rowId}`)?.value) || 0;
  const el       = document.getElementById(`subtotal-${rowId}`);
  if (el) el.textContent = fmtNum(price * qty) + ' ' + CURRENCY;
  updateGrandTotal();
}

function updateGrandTotal() {
  let total = 0;
  document.querySelectorAll('[id^="subtotal-"]').forEach(el => {
    total += parseFloat(el.textContent.replace(/[^\d,]/g, '').replace(',', '.')) || 0;
  });
  const el = document.getElementById('grand-total');
  if (el) el.textContent = fmtNum(total) + ' ' + CURRENCY;
}

function onProductSelect(rowId) {
  const select = document.getElementById(`product-select-${rowId}`);
  if (!select) return;
  const id = select.value;
  if (id && id !== 'custom') {
    const p = productsData.find(x => String(x.id) === String(id));
    if (p) {
      document.getElementById(`pid-${rowId}`).value   = p.id;
      document.getElementById(`name-${rowId}`).value  = p.name;
      document.getElementById(`price-${rowId}`).value = parseFloat(p.price).toFixed(2);
      updateSubtotal(rowId);
    }
  } else {
    document.getElementById(`pid-${rowId}`).value = '';
    if (id === 'custom') {
      ['name','price'].forEach(f => { document.getElementById(`${f}-${rowId}`).value = ''; });
      document.getElementById(`name-${rowId}`).focus();
    }
  }
}

function buildOptions() {
  const opts = productsData.map(p =>
    `<option value="${p.id}">${escHtml(p.name)} — ${fmtNum(p.price)} ${CURRENCY}</option>`
  ).join('');
  return `<option value="">— Choisir dans le catalogue —</option>${opts}<option value="custom">✏️  Saisie libre</option>`;
}

function buildRowHTML(rowId) {
  return `
  <div class="card-body py-3 px-4">
    <div class="row g-3 align-items-start">
      <div class="col-lg-3 col-md-6">
        <label class="form-label">Catalogue</label>
        <select class="form-select form-select-sm" id="product-select-${rowId}" onchange="onProductSelect(${rowId})">
          ${buildOptions()}
        </select>
        <input type="hidden" name="item_product_id[]" id="pid-${rowId}" value="">
      </div>
      <div class="col-lg-3 col-md-6">
        <label class="form-label">Désignation <span class="text-danger">*</span></label>
        <input type="text" class="form-control form-control-sm" name="item_name[]" id="name-${rowId}" placeholder="Nom du produit / service" required>
        <input type="hidden" name="item_description[]" id="desc-${rowId}" value="">
      </div>
      <div class="col-lg-2 col-md-4">
        <label class="form-label">Prix U. <span class="text-danger">*</span></label>
        <div class="input-group input-group-sm">
          <input type="number" class="form-control" name="item_price[]" id="price-${rowId}" step="0.01" min="0" placeholder="0.00" required oninput="updateSubtotal(${rowId})">
          <span class="input-group-text fw-semibold">${CURRENCY}</span>
        </div>
      </div>
      <div class="col-lg-1 col-md-2">
        <label class="form-label">Qté <span class="text-danger">*</span></label>
        <input type="number" class="form-control form-control-sm" name="item_quantity[]" id="qty-${rowId}" min="1" value="1" required oninput="updateSubtotal(${rowId})">
      </div>
      <div class="col-lg-2 col-md-4">
        <label class="form-label">Sous-total</label>
        <div class="fw-bold text-primary fs-6 pt-1" id="subtotal-${rowId}">0,00 ${CURRENCY}</div>
      </div>
      <div class="col-lg-1 col-md-2 text-end">
        <label class="form-label d-block">&nbsp;</label>
        <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeItemRow(${rowId})" title="Supprimer">
          <i class="bi bi-trash3-fill"></i>
        </button>
      </div>
    </div>
  </div>`;
}

function addItemRow() { itemCounter++; _createRow(itemCounter, null); }

function addItemRowWithData(data) { itemCounter++; _createRow(itemCounter, data); }

function _createRow(rowId, data) {
  const container = document.getElementById('items-container');
  const noItems   = document.getElementById('no-items-msg');
  if (noItems) noItems.style.display = 'none';
  const row     = document.createElement('div');
  row.className = 'item-row card mb-3';
  row.id        = `row-${rowId}`;
  row.innerHTML = buildRowHTML(rowId);
  container.appendChild(row);
  if (data) {
    if (data.product_id) {
      const sel = document.getElementById(`product-select-${rowId}`);
      if (sel) sel.value = String(data.product_id);
      document.getElementById(`pid-${rowId}`).value = data.product_id;
    }
    document.getElementById(`name-${rowId}`).value  = data.product_name || '';
    document.getElementById(`price-${rowId}`).value = parseFloat(data.unit_price || 0).toFixed(2);
    document.getElementById(`qty-${rowId}`).value   = data.quantity     || 1;
    updateSubtotal(rowId);
  }
}

function removeItemRow(rowId) {
  document.getElementById(`row-${rowId}`)?.remove();
  updateGrandTotal();
  if (document.querySelectorAll('.item-row').length === 0) {
    const noItems = document.getElementById('no-items-msg');
    if (noItems) noItems.style.display = 'block';
  }
}

function validateForm() {
  if (document.querySelectorAll('.item-row').length === 0) {
    alert('Veuillez ajouter au moins un article à la facture.');
    return false;
  }
  return true;
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadProducts();
  if (typeof EXISTING_ITEMS !== 'undefined' && EXISTING_ITEMS.length > 0) {
    EXISTING_ITEMS.forEach(item => addItemRowWithData(item));
  } else {
    addItemRow();
  }
});

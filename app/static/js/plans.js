/**
 * Vista de administración de Planes de Membresía (SCRUM-51).
 * */

const ACTIVE_GYM_KEY = 'active_gym_id';

const planUser = checkAuthRouteProtection();
const isAdmin = planUser && planUser.role === 'ADMIN';


let currentPlans = [];
let editingPlanId = null;


const els = {
    gymSelect: document.getElementById('gym-select'),
    body: document.getElementById('plans-body'),
    empty: document.getElementById('plans-empty'),
    listError: document.getElementById('list-error'),
    listSuccess: document.getElementById('list-success'),
    form: document.getElementById('plan-form'),
    formTitle: document.getElementById('form-title'),
    formError: document.getElementById('form-error'),
    submitBtn: document.getElementById('submit-btn'),
    cancelBtn: document.getElementById('cancel-edit-btn'),
    title: document.getElementById('title'),
    description: document.getElementById('description'),
    cost: document.getElementById('cost'),
    duration: document.getElementById('duration'),
    discount: document.getElementById('discount'),
    preview: document.getElementById('final-price-preview'),
};

const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' });


/*  ------------------------------------------------------------------ */
/* Utilidades                                                          */
/* ------------------------------------------------------------------ */

function showMessage(el, text) {
  el.textContent = text;
  el.style.display = text ? 'block' : 'none';
}

function getActiveGymId() {
  return Number(els.gymSelect.value);
}

function rememberGym(gymId) {
  try { localStorage.setItem(ACTIVE_GYM_KEY, String(gymId)); } catch (e) { /* sin almacenamiento */ }
}

function recallGym() {
  try { return Number(localStorage.getItem(ACTIVE_GYM_KEY)); } catch (e) { return null; }
}

function calculateFinalPrice(cost, discount) {
  if (!(cost > 0)) return 0;
  const pct = discount >= 0 && discount <= 100 ? discount : 0;
  return Math.round(cost * (100 - pct)) / 100;
}

function hasMaxTwoDecimals(raw) {
  return /^\d+(\.\d{1,2})?$/.test(raw);
}

async function apiRequest(path, options = {}) {
  const token = getValidToken();
  if (!token) return null;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    alert('Sesión expirada o no autorizada. Redirigiendo a Login...');
    logoutUser();
    return null;
  }

  let data = null;
  try { data = await response.json(); } catch (e) { /* sin cuerpo */ }
  return { ok: response.ok, status: response.status, data };
}

function errorText(result, fallback) {
  const detail = result && result.data && result.data.detail;
  if (Array.isArray(detail)) {
    return detail.map(err => String(err.msg).replace(/^Value error, /, '')).join('. ');
  }
  if (result && result.status === 403) {
    return `403 Forbidden: ${detail || 'No tiene permisos para realizar esta acción'}`;
  }
  return detail || fallback;
}


async function loadGyms() {
  const gymIds = planUser.gym_ids || [];
  els.gymSelect.innerHTML = '';

  if (gymIds.length === 0) {
    showMessage(els.listError, 'No tienes gimnasios asignados.');
    els.gymSelect.disabled = true;
    return;
  }

  for (const gymId of gymIds) {
    const option = document.createElement('option');
    option.value = gymId;
    option.textContent = `Gimnasio #${gymId}`;
    els.gymSelect.appendChild(option);

    // Nombre real del gimnasio (si responde)
    apiRequest(`/gyms/${gymId}`).then(result => {
      if (result && result.ok) option.textContent = `${result.data.name} (#${gymId})`;
    });
  }

  const saved = recallGym();
  if (saved && gymIds.includes(saved)) els.gymSelect.value = String(saved);
}




/* ------------------------------------------*/
/* Listado                                                             */
/* ------------------------------------------ */

async function loadPlans() {
  const gymId = getActiveGymId();
  if (!gymId) return;

  showMessage(els.listError, '');
  const result = await apiRequest(`/gyms/${gymId}/plans`);
  if (!result) return;

  if (!result.ok) {
    currentPlans = [];
    renderPlans();
    showMessage(els.listError, errorText(result, 'No se pudieron cargar los planes.'));
    return;
  }

  currentPlans = result.data;
  renderPlans();
}

function renderPlans() {
  els.body.innerHTML = '';
  els.empty.style.display = currentPlans.length ? 'none' : 'block';

  for (const plan of currentPlans) {
    const row = document.createElement('tr');

    const titleCell = document.createElement('td');
    const titleStrong = document.createElement('strong');
    titleStrong.textContent = plan.title;
    titleCell.appendChild(titleStrong);
    if (plan.description) {
      const desc = document.createElement('div');
      desc.className = 'cell-subtext';
      desc.textContent = plan.description;
      titleCell.appendChild(desc);
    }
    row.appendChild(titleCell);

    const cells = [
      `${plan.duration_months} ${plan.duration_months === 1 ? 'mes' : 'meses'}`,
      money.format(plan.cost),
      `${plan.discount_percent}%`,
    ];
    for (const text of cells) {
      const td = document.createElement('td');
      td.textContent = text;
      row.appendChild(td);
    }

    const finalCell = document.createElement('td');
    finalCell.className = 'price-cell';
    finalCell.textContent = money.format(plan.final_price);
    row.appendChild(finalCell);

    if (isAdmin) {
      const actionCell = document.createElement('td');
      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'btn-small';
      editBtn.textContent = 'Editar';
      editBtn.addEventListener('click', () => startEdit(plan));
      actionCell.appendChild(editBtn);
      row.appendChild(actionCell);
    }

    els.body.appendChild(row);
  }
}


/* ---------------------------------------- */
/* Formulario crear / editar                                           */
/* ---------------------------- */

function updatePreview() {
  const price = calculateFinalPrice(parseFloat(els.cost.value), parseFloat(els.discount.value || '0'));
  els.preview.textContent = money.format(price);
}

/** CA1 y CA2: validación en el cliente con los mismos mensajes que la API. */
function validateForm() {
  const title = els.title.value.trim();
  const costRaw = els.cost.value.trim();
  const durationRaw = els.duration.value.trim();
  const discountRaw = els.discount.value.trim() || '0';

  if (!title) return 'El título es obligatorio';
  if (!costRaw || !(parseFloat(costRaw) > 0)) return 'El costo debe ser mayor a 0';
  if (!hasMaxTwoDecimals(costRaw)) return 'El costo admite máximo 2 decimales';
  if (!/^\d+$/.test(durationRaw) || Number(durationRaw) < 1 || Number(durationRaw) > 12) {
    return 'La duración debe ser un número entero de 1 a 12 meses';
  }
  const discount = parseFloat(discountRaw);
  if (Number.isNaN(discount) || discount < 0 || discount > 100) {
    return 'El descuento debe ser un porcentaje entre 0 y 100';
  }
  if (!hasMaxTwoDecimals(discountRaw)) return 'El descuento admite máximo 2 decimales';
  return null;
}

function resetForm() {
  editingPlanId = null;
  els.form.reset();
  els.discount.value = '0';
  els.formTitle.textContent = 'Nuevo plan';
  els.submitBtn.textContent = 'Crear plan';
  els.cancelBtn.style.display = 'none';
  showMessage(els.formError, '');
  updatePreview();
}

function startEdit(plan) {
  editingPlanId = plan.id;
  els.title.value = plan.title;
  els.description.value = plan.description || '';
  els.cost.value = plan.cost;
  els.duration.value = plan.duration_months;
  els.discount.value = plan.discount_percent;
  els.formTitle.textContent = `Editar plan: ${plan.title}`;
  els.submitBtn.textContent = 'Guardar cambios';
  els.cancelBtn.style.display = 'block';
  showMessage(els.formError, '');
  updatePreview();
  els.form.scrollIntoView({ behavior: 'smooth' });
}



async function submitPlan(event) {
  event.preventDefault();
  showMessage(els.formError, '');
  showMessage(els.listSuccess, '');

  const validationError = validateForm();
  if (validationError) {
    showMessage(els.formError, validationError);
    return;
  }

  const payload = {
    title: els.title.value.trim(),
    description: els.description.value.trim() || null,
    cost: els.cost.value.trim(),
    duration_months: Number(els.duration.value),
    discount_percent: els.discount.value.trim() || '0',
  };

  const gymId = getActiveGymId();
  const isEdit = editingPlanId !== null;
  const path = isEdit ? `/gyms/${gymId}/plans/${editingPlanId}` : `/gyms/${gymId}/plans`;

  els.submitBtn.disabled = true;
  const result = await apiRequest(path, {
    method: isEdit ? 'PUT' : 'POST',
    body: JSON.stringify(payload),
  });
  els.submitBtn.disabled = false;
  if (!result) return;

  if (!result.ok) {
    showMessage(els.formError, errorText(result, 'No se pudo guardar el plan.'));
    return;
  }

  showMessage(els.listSuccess, isEdit ? 'Plan actualizado correctamente.' : 'Plan creado correctamente.');
  resetForm();
  await loadPlans();
}



/* ----------------------------------------- */
/* Inicio                                                              */
/* ----------------------------------------- */

async function initPlansPage() {
  if (!planUser) return;

  // CA3: ocultar acciones de administración a los Encargados
  if (!isAdmin) {
    document.querySelectorAll('.admin-only').forEach(el => { el.style.display = 'none'; });
    document.getElementById('manager-note').style.display = 'block';
  }

  els.gymSelect.addEventListener('change', () => {
    rememberGym(getActiveGymId());
    showMessage(els.listSuccess, '');
    if (isAdmin) resetForm();
    loadPlans();
  });

  if (isAdmin) {
    els.form.addEventListener('submit', submitPlan);
    els.cancelBtn.addEventListener('click', resetForm);
    [els.cost, els.discount].forEach(input => input.addEventListener('input', updatePreview));
    updatePreview();
  }

  await loadGyms();
  await loadPlans();
}

initPlansPage();
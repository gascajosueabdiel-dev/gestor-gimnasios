/**
 * Pantalla de cobro de membresía
 * - Elegir socio, plan y método de pago (Efectivo / Tarjeta / Transferencia).
 * - Muestra el desglose: plan + inscripción (solo en el primer pago) = total.
 * - El monto real lo calcula el servidor; aquí solo se muestra la vista previa.
 */
const cobroUser = checkAuthRouteProtection();
const $ = (id) => document.getElementById(id);
const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' });
const NOMBRE_METODO = { EFECTIVO: 'Efectivo', TARJETA: 'Tarjeta', TRANSFERENCIA: 'Transferencia' };

let gym = null;
let planes = [];
let pagosDelSocio = [];

/* ------------- */
/* Utilidades                                                          */
/* ------------- */

function mostrar(el, texto) {
  el.textContent = texto;
  el.style.display = texto ? 'block' : 'none';
}

function textoError(result, porDefecto) {
  const data = result && result.data;
  if (data && data.errores) return Object.values(data.errores).join('. ');
  if (data && typeof data.detail === 'string') return data.detail;
  return porDefecto;
}

async function api(path, options = {}) {
  const token = getValidToken();
  if (!token) return null;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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

function formatearFecha(iso) {
  const [anio, mes, dia] = iso.slice(0, 10).split('-');
  return `${dia}/${mes}/${anio}`;
}

/** Mismo algoritmo que el servidor: suma meses y ajusta al último día del mes. */
function calcularVencimiento(inicio, meses) {
  const total = inicio.getMonth() + meses;
  const anio = inicio.getFullYear() + Math.floor(total / 12);
  const mes = total % 12;
  const ultimoDia = new Date(anio, mes + 1, 0).getDate();
  return new Date(anio, mes, Math.min(inicio.getDate(), ultimoDia));
}

/* ----------------- */
/* Carga inicial                                                       */
/* ----------------- */

async function cargarGimnasio() {
  const payload = parseJwt(getValidToken()) || {};
  const gymId = payload.active_gym_id ?? Math.min(...(cobroUser.gym_ids || []));
  const result = await api(`/gyms/${gymId}`);
  if (!result || !result.ok) {
    mostrar($('cobro-error'), 'No se pudo cargar el gimnasio activo.');
    return;
  }
  gym = result.data;
  $('gym-info').textContent =
    `Gimnasio: ${gym.name} · Inscripción base: ${money.format(gym.base_enrollment_fee)} (solo en el primer pago)`;
}

async function cargarPlanes() {
  const result = await api(`/gyms/${gym.id}/plans`);
  planes = result && result.ok ? result.data : [];
  $('plan').innerHTML = '';
  if (planes.length === 0) {
    $('plan').innerHTML = '<option value="">No hay planes en este gimnasio</option>';
    return;
  }
  for (const plan of planes) {
    const option = document.createElement('option');
    option.value = plan.id;
    const meses = plan.duration_months === 1 ? '1 mes' : `${plan.duration_months} meses`;
    option.textContent = `${plan.title} · ${meses} · ${money.format(plan.final_price)}`;
    $('plan').appendChild(option);
  }
}




/* ---------------- */
/* Socio                                                               */
/* ---------------- */

async function buscarSocios() {
  const termino = $('buscar-socio').value.trim();
  const params = new URLSearchParams({ limit: 20 });
  if (termino) params.set('search', termino);
  const result = await api(`/socios?${params}`);
  const socios = result && result.ok ? result.data : [];

  $('socio').innerHTML = '';
  if (socios.length === 0) {
    $('socio').innerHTML = '<option value="">Sin resultados</option>';
  } else {
    for (const socio of socios) {
      const option = document.createElement('option');
      option.value = socio.id;
      option.textContent = `${socio.nombre} (#${socio.num_referencia_unico})`;
      $('socio').appendChild(option);
    }
  }
  await cargarPagosDelSocio();
}

async function cargarPagosDelSocio() {
  const socioId = $('socio').value;
  pagosDelSocio = [];
  if (socioId) {
    const result = await api(`/socios/${socioId}/cobros`);
    pagosDelSocio = result && result.ok ? result.data : [];
  }
  pintarHistorial();
  actualizarDesglose();
}

function pintarHistorial() {
  const body = $('historial-body');
  body.innerHTML = '';
  const vacio = $('historial-vacio');
  if (!$('socio').value) {
    vacio.textContent = 'Selecciona un socio para ver sus pagos.';
    vacio.style.display = 'block';
    return;
  }
  vacio.textContent = 'Este socio todavía no tiene pagos.';
  vacio.style.display = pagosDelSocio.length ? 'none' : 'block';

  for (const pago of pagosDelSocio) {
    const row = document.createElement('tr');
    const celdas = [
      formatearFecha(pago.fecha_pago),
      pago.plan_title,
      NOMBRE_METODO[pago.metodo_pago] || pago.metodo_pago,
      money.format(pago.monto_inscripcion),
      money.format(pago.monto),
      formatearFecha(pago.fecha_vencimiento),
    ];
    for (const texto of celdas) {
      const td = document.createElement('td');
      td.textContent = texto;
      row.appendChild(td);
    }
    body.appendChild(row);
  }
}



/* ------------- */
/* Desglose                                                            */
/* ------------- */

function actualizarDesglose() {
  const plan = planes.find((p) => String(p.id) === $('plan').value);
  const esPrimerPago = pagosDelSocio.length === 0;
  const inscripcion = gym && esPrimerPago ? Number(gym.base_enrollment_fee) : 0;
  const montoPlan = plan ? plan.final_price : 0;

  $('d-plan').textContent = money.format(montoPlan);
  $('d-insc').textContent = money.format(inscripcion);
  $('d-insc-label').textContent = esPrimerPago
    ? 'Inscripción (primer pago)'
    : 'Inscripción (ya pagada antes)';
  $('d-total').textContent = money.format(montoPlan + inscripcion);

  if (plan) {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    let inicio = hoy;
    if (pagosDelSocio.length) {
      const [a, m, d] = pagosDelSocio[0].fecha_vencimiento.split('-').map(Number);
      const ultimo = new Date(a, m - 1, d);
      if (ultimo > hoy) inicio = ultimo;
    }
    const vence = calcularVencimiento(inicio, plan.duration_months);
    $('d-vence').textContent = formatearFecha(
      `${vence.getFullYear()}-${String(vence.getMonth() + 1).padStart(2, '0')}-${String(vence.getDate()).padStart(2, '0')}`
    );
  } else {
    $('d-vence').textContent = '-';
  }
}

/* -------- */
/* Cobrar                                                              */
/* -------- */

async function cobrar(event) {
  event.preventDefault();
  mostrar($('cobro-error'), '');
  mostrar($('cobro-ok'), '');

  const socioId = $('socio').value;
  const planId = $('plan').value;
  if (!socioId) return mostrar($('cobro-error'), 'Selecciona un socio');
  if (!planId) return mostrar($('cobro-error'), 'Selecciona un plan');

  $('btn-cobrar').disabled = true;
  const result = await api(`/socios/${socioId}/cobros`, {
    method: 'POST',
    body: JSON.stringify({ plan_id: Number(planId), metodo_pago: $('metodo').value }),
  });
  $('btn-cobrar').disabled = false;
  if (!result) return;

  if (!result.ok) {
    return mostrar($('cobro-error'), textoError(result, 'No se pudo registrar el cobro.'));
  }

  const r = result.data;
  mostrar(
    $('cobro-ok'),
    `Cobro registrado: ${money.format(r.monto)} (${NOMBRE_METODO[r.metodo_pago]}). ` +
    `Vigente del ${formatearFecha(r.fecha_inicio)} al ${formatearFecha(r.fecha_vencimiento)}.`
  );
  await cargarPagosDelSocio();
}

/* ---- */
/* Inicio                                                              */
/* ---- */

async function initCobros() {
  if (!cobroUser) return;
  await cargarGimnasio();
  if (!gym) return;
  await cargarPlanes();
  actualizarDesglose();

  $('btn-buscar').addEventListener('click', buscarSocios);
  $('buscar-socio').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); buscarSocios(); }
  });
  $('socio').addEventListener('change', cargarPagosDelSocio);
  $('plan').addEventListener('change', actualizarDesglose);
  $('cobro-form').addEventListener('submit', cobrar);
}

initCobros();
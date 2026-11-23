/**
 * Pantalla de socios (SCRUM-14). Usa las funciones de auth.js:
 * checkAuthRouteProtection, getValidToken, parseJwt, logoutUser.
 */
const $ = (id) => document.getElementById(id);
const LIMITE = 50;
const CELULAR_VALIDO = /^[0-9]{10}$/;
const CAMPOS_ALTA = ['nombre', 'celular', 'fecha_nacimiento', 'metas'];

let idSocioAbierto = null;
let busquedaVigente = 0;
let esperaBusqueda;
let cargaMembresia = 0;

class ErrorApi extends Error {
  constructor(estado, cuerpo) {
    super(typeof cuerpo?.detail === 'string' ? cuerpo.detail : 'Error de la API');
    this.estado = estado;
    this.cuerpo = cuerpo;
  }
}

async function api(ruta, { metodo = 'GET', datos } = {}) {
  const token = getValidToken();
  if (!token) throw new ErrorApi(401, null); // getValidToken ya redirige a login

  const cabeceras = { Authorization: `Bearer ${token}` };
  if (datos !== undefined) cabeceras['Content-Type'] = 'application/json';

  const respuesta = await fetch(`${API_BASE_URL}${ruta}`, {
    method: metodo,
    headers: cabeceras,
    body: datos === undefined ? undefined : JSON.stringify(datos),
  });
  const cuerpo = await respuesta.json().catch(() => null);
  if (respuesta.ok) return cuerpo;

  if (respuesta.status === 401) {
    alert('Sesión expirada o no autorizada. Redirigiendo a Login...');
    logoutUser();
  }
  throw new ErrorApi(respuesta.status, cuerpo);
}

function mensajeDe(error) {
  if (error instanceof ErrorApi) return error.message;
  return 'No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.';
}

/* Gimnasio activo */

function gimnasioActivo(usuario) {
  // Igual que el servidor: si el token no trae active_gym_id, usa el primero asignado.
  return usuario.active_gym_id ?? Math.min(...usuario.gym_ids);
}

async function cargarGimnasios(usuario) {
  const selector = $('selector-gimnasio');
  const activo = gimnasioActivo(usuario);
  const gimnasios = await Promise.all(
    usuario.gym_ids.map((id) => api(`/gyms/${id}`).catch(() => ({ id, name: `Gimnasio ${id}` }))),
  );
  selector.replaceChildren(
    ...gimnasios.map((g) => new Option(g.name, g.id, false, g.id === activo)),
  );
  selector.disabled = gimnasios.length < 2;
}

async function cambiarGimnasio() {
  const selector = $('selector-gimnasio');
  selector.disabled = true;
  try {
    const sesion = await api('/auth/active-gym', {
      metodo: 'POST',
      datos: { gym_id: Number(selector.value) },
    });
    localStorage.setItem(TOKEN_KEY, sesion.access_token);
    $('buscador').value = '';
    mostrarPanel('vacio');
    await buscar();
  } catch (error) {
    $('estado-lista').textContent = mensajeDe(error);
    selector.value = gimnasioActivo(getCurrentUserData());
  } finally {
    selector.disabled = false;
  }
}

/* Búsqueda */

async function buscar() {
  const consulta = ++busquedaVigente;
  const termino = $('buscador').value.trim();
  const parametros = new URLSearchParams({ limit: LIMITE });
  if (termino) parametros.set('search', termino);

  try {
    const socios = await api(`/socios?${parametros}`);
    if (consulta === busquedaVigente) pintarLista(socios, termino);
  } catch (error) {
    if (consulta !== busquedaVigente) return;
    $('lista-socios').replaceChildren();
    $('estado-lista').textContent = mensajeDe(error);
  }
}

function pintarLista(socios, termino) {
  $('lista-socios').replaceChildren(...socios.map(crearFila));
  if (socios.length === 0) {
    $('estado-lista').textContent = termino
      ? `Sin resultados para “${termino}”. Revisa el dato o registra al socio.`
      : 'Este gimnasio aún no tiene socios. Registra el primero.';
  } else if (socios.length === LIMITE) {
    $('estado-lista').textContent =
      `Se muestran los primeros ${LIMITE}. Escribe un nombre o número para acotar.`;
  } else {
    $('estado-lista').textContent = socios.length === 1 ? '1 socio' : `${socios.length} socios`;
  }
}

function crearFila(socio) {
  const boton = document.createElement('button');
  boton.type = 'button';
  boton.dataset.id = socio.id;
  if (socio.id === idSocioAbierto) boton.setAttribute('aria-current', 'true');
  boton.addEventListener('click', () => abrirFicha(socio.id));

  const disco = document.createElement('span');
  disco.className = 'lista-disco';
  disco.textContent = socio.num_referencia_unico;
  const nombre = document.createElement('span');
  nombre.className = 'lista-nombre';
  nombre.textContent = socio.nombre;
  const celular = document.createElement('span');
  celular.className = 'lista-celular';
  celular.textContent = socio.celular;
  boton.append(disco, nombre, celular);

  const fila = document.createElement('li');
  fila.append(boton);
  return fila;
}

/* Panel derecho */

function mostrarPanel(cual) {
  $('panel-vacio').hidden = cual !== 'vacio';
  $('ficha').hidden = cual !== 'ficha';
  $('form-alta').hidden = cual !== 'alta';
  if (cual !== 'ficha') marcarSocioAbierto(null);
}

function marcarSocioAbierto(id) {
  idSocioAbierto = id;
  document.querySelectorAll('#lista-socios button').forEach((boton) => {
    if (Number(boton.dataset.id) === id) boton.setAttribute('aria-current', 'true');
    else boton.removeAttribute('aria-current');
  });
}

function formatearFecha(iso) {
  if (!iso) return 'Sin registrar';
  const [anio, mes, dia] = iso.split('-').map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString('es-MX', { dateStyle: 'long' });
}

function pintarFicha(socio, recienRegistrado = false) {
  const numero = String(socio.num_referencia_unico);
  $('ficha-numero').textContent = numero;
  $('ficha-numero').classList.toggle('largo', numero.length > 4);
  $('ficha-nombre').textContent = socio.nombre;
  $('ficha-celular').textContent = socio.celular;
  $('ficha-fecha').textContent = formatearFecha(socio.fecha_nacimiento);
  $('ficha-metas').textContent = socio.metas || 'Sin registrar';
  $('ficha-confirmacion').hidden = !recienRegistrado;
  $('ficha').classList.toggle('recien', recienRegistrado);
  mostrarPanel('ficha');
  marcarSocioAbierto(socio.id);
  $('panel').scrollIntoView({ block: 'nearest' });
  cargarMembresia(socio.id);
}

async function abrirFicha(id) {
  try {
    pintarFicha(await api(`/socios/${id}`));
  } catch (error) {
    $('estado-lista').textContent = mensajeDe(error);
  }
}

/* Alta */

function mostrarErrorCampo(campo, mensaje) {
  $(`error-${campo}`).textContent = mensaje;
  const entrada = $('form-alta').elements[campo];
  if (mensaje) entrada.setAttribute('aria-invalid', 'true');
  else entrada.removeAttribute('aria-invalid');
}

function limpiarErrores() {
  $('alta-aviso').style.display = 'none';
  for (const campo of CAMPOS_ALTA) mostrarErrorCampo(campo, '');
}

function fechaDeAyer() {
  const ayer = new Date();
  ayer.setDate(ayer.getDate() - 1);
  const mes = String(ayer.getMonth() + 1).padStart(2, '0');
  const dia = String(ayer.getDate()).padStart(2, '0');
  return `${ayer.getFullYear()}-${mes}-${dia}`;
}

function abrirAlta() {
  $('form-alta').reset();
  limpiarErrores();
  $('campo-fecha').max = fechaDeAyer();
  mostrarPanel('alta');
  $('panel').scrollIntoView({ block: 'nearest' });
  $('campo-nombre').focus();
}

function validarAlta(datos) {
  const errores = {};
  if (!datos.nombre) errores.nombre = 'Este campo es obligatorio';
  if (!CELULAR_VALIDO.test(datos.celular)) {
    errores.celular = 'El celular debe tener exactamente 10 dígitos numéricos';
  }
  return errores;
}

function pintarErrores(errores) {
  for (const [campo, mensaje] of Object.entries(errores)) {
    if (CAMPOS_ALTA.includes(campo)) mostrarErrorCampo(campo, mensaje);
  }
  const primero = CAMPOS_ALTA.find((campo) => errores[campo]);
  if (primero) $('form-alta').elements[primero].focus();
}

async function guardarSocio(evento) {
  evento.preventDefault();
  limpiarErrores();
  const formulario = $('form-alta').elements;
  const datos = {
    nombre: formulario.nombre.value.trim(),
    celular: formulario.celular.value.trim(),
    fecha_nacimiento: formulario.fecha_nacimiento.value || null,
    metas: formulario.metas.value.trim() || null,
  };

  const errores = validarAlta(datos);
  if (Object.keys(errores).length > 0) {
    pintarErrores(errores);
    return;
  }

  const boton = evento.submitter;
  boton.disabled = true;
  try {
    const socio = await api('/socios', { metodo: 'POST', datos });
    $('buscador').value = '';
    pintarFicha(socio, true);
    await buscar();
  } catch (error) {
    if (error instanceof ErrorApi && error.cuerpo?.errores) {
      pintarErrores(error.cuerpo.errores);
    } else {
      $('alta-aviso').textContent = mensajeDe(error);
      $('alta-aviso').style.display = 'block';
    }
  } finally {
    boton.disabled = false;
  }
}

/* Membresía del socio */

function formatearPrecio(valor) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(valor);
}

function textoDePlan(plan) {
  const meses = plan.duration_months === 1 ? '1 mes' : `${plan.duration_months} meses`;
  return `${plan.title} · ${meses} · ${formatearPrecio(plan.final_price)}`;
}

function mostrarAvisoMembresia(mensaje) {
  $('membresia-aviso').textContent = mensaje;
  $('membresia-aviso').style.display = 'block';
}

function mostrarErrorPlan(mensaje) {
  $('error-plan').textContent = mensaje;
  const selector = $('campo-plan');
  if (mensaje) selector.setAttribute('aria-invalid', 'true');
  else selector.removeAttribute('aria-invalid');
}

function limpiarErroresMembresia() {
  $('membresia-aviso').style.display = 'none';
  mostrarErrorPlan('');
}

function cerrarFormularioMembresia() {
  $('form-membresia').hidden = true;
  $('abrir-asignar').hidden = false;
  $('abrir-asignar').disabled = false;
  limpiarErroresMembresia();
}

function pintarEstadoMembresia(membresias) {
  // La API las entrega de la que termina más tarde a la más antigua.
  const vigente = membresias.find((m) => m.vigente);
  const ultima = membresias[0];
  const estado = $('membresia-estado');
  estado.className = 'estado';

  if (vigente) {
    let texto = `Vigente hasta el ${formatearFecha(vigente.end_date)} · ${vigente.plan_title}.`;
    if (ultima.end_date > vigente.end_date) {
      texto += ` Renovada hasta el ${formatearFecha(ultima.end_date)}.`;
    }
    estado.textContent = texto;
    estado.classList.add('membresia-vigente');
  } else {
    estado.textContent = ultima
      ? `Sin membresía vigente. La última (${ultima.plan_title}) venció el ${formatearFecha(ultima.end_date)}.`
      : 'Sin membresía vigente.';
    estado.classList.add('membresia-sin');
  }
  $('abrir-asignar').textContent = vigente ? 'Renovar plan' : 'Asignar plan';
}

async function cargarMembresia(socioId) {
  const consulta = ++cargaMembresia;
  cerrarFormularioMembresia();
  $('membresia-estado').className = 'estado';
  $('membresia-estado').textContent = 'Consultando membresía…';
  try {
    const membresias = await api(`/socios/${socioId}/membresias`);
    if (consulta === cargaMembresia) pintarEstadoMembresia(membresias);
  } catch (error) {
    if (consulta !== cargaMembresia) return;
    $('membresia-estado').textContent = mensajeDe(error);
  }
}

async function abrirAsignar() {
  limpiarErroresMembresia();
  const boton = $('abrir-asignar');
  boton.disabled = true;
  try {
    const gimnasio = gimnasioActivo(getCurrentUserData());
    const planes = await api(`/gyms/${gimnasio}/plans`);
    if (planes.length === 0) {
      mostrarAvisoMembresia(
        'Este gimnasio aún no tiene planes. El administrador debe crearlos antes de asignar una membresía.',
      );
      boton.disabled = false;
      return;
    }
    const placeholder = new Option('Elige un plan', '', true, true);
    placeholder.disabled = true;
    $('campo-plan').replaceChildren(placeholder, ...planes.map((p) => new Option(textoDePlan(p), p.id)));
    $('form-membresia').hidden = false;
    boton.hidden = true;
    $('campo-plan').focus();
  } catch (error) {
    mostrarAvisoMembresia(mensajeDe(error));
    boton.disabled = false;
  }
}

async function asignarMembresia(evento) {
  evento.preventDefault();
  limpiarErroresMembresia();
  if (idSocioAbierto === null) return;

  const planId = Number($('campo-plan').value);
  if (!planId) {
    mostrarErrorPlan('Elige un plan');
    $('campo-plan').focus();
    return;
  }

  const boton = evento.submitter;
  boton.disabled = true;
  try {
    await api(`/socios/${idSocioAbierto}/membresias`, {
      metodo: 'POST',
      datos: { plan_id: planId },
    });
    await cargarMembresia(idSocioAbierto);
  } catch (error) {
    mostrarAvisoMembresia(mensajeDe(error));
  } finally {
    boton.disabled = false;
  }
}

/* Arranque */

const usuarioActual = checkAuthRouteProtection();

if (usuarioActual) {
  $('selector-gimnasio').addEventListener('change', cambiarGimnasio);
  $('abrir-alta').addEventListener('click', abrirAlta);
  $('cancelar-alta').addEventListener('click', () => mostrarPanel('vacio'));
  $('form-alta').addEventListener('submit', guardarSocio);
  $('abrir-asignar').addEventListener('click', abrirAsignar);
  $('cancelar-membresia').addEventListener('click', cerrarFormularioMembresia);
  $('form-membresia').addEventListener('submit', asignarMembresia);
  $('buscador').addEventListener('input', () => {
    clearTimeout(esperaBusqueda);
    esperaBusqueda = setTimeout(buscar, 250);
  });

  mostrarPanel('vacio');
  cargarGimnasios(usuarioActual).catch(() => {});
  buscar();
}
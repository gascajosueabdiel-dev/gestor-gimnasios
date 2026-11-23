/**
 * Pantalla de Recepción (registro de asistencias). Usa las funciones de auth.js:
 * checkAuthRouteProtection, getValidToken, getCurrentUserData, logoutUser.
 *
 * Endpoints (relativos a API_BASE_URL):
 *   POST /attendance         registra la entrada (CA1, CA2, CA3)
 *   GET  /attendance/recent  últimas entradas del gimnasio activo
 * TODO: confirmar en main.py que el router de asistencias queda montado de modo
 * que estas rutas existan tal cual (sin duplicar el prefijo "/attendance").
 */
const $ = (id) => document.getElementById(id);
const REFERENCIA_VALIDA = /^[0-9]{1,9}$/;
const ENTRADAS_RECIENTES = 10;

let cargaVigente = 0;
let numeroPendiente = null; // número en espera de que el Encargado decida (CA2)

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

/* Gimnasio activo (misma lógica que socios.js) */

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
    numeroPendiente = null;
    mostrarErrorReferencia('');
    mostrarPanel('vacio');
    liberarFormulario();
    await cargarEntradas();
  } catch (error) {
    mostrarError('No se pudo cambiar de gimnasio', mensajeDe(error));
    selector.value = gimnasioActivo(getCurrentUserData());
  } finally {
    selector.disabled = false;
  }
}

/* Panel derecho */

function mostrarPanel(cual) {
  $('panel-vacio').hidden = cual !== 'vacio';
  $('resultado').hidden = cual !== 'resultado';
  $('aviso-error').style.display = cual === 'error' ? 'block' : 'none';
}

function mostrarError(titulo, detalle) {
  $('aviso-error-titulo').textContent = titulo;
  $('aviso-error-detalle').textContent = detalle;
  mostrarPanel('error');
}

function pintarResultado(numero, nombre, { confirmacion = '', vencida = false } = {}) {
  const texto = String(numero);
  $('resultado-numero').textContent = texto;
  $('resultado-numero').classList.toggle('largo', texto.length > 4);
  $('resultado-nombre').textContent = nombre;
  $('resultado-confirmacion').textContent = confirmacion;
  $('resultado-confirmacion').hidden = !confirmacion;
  $('resultado-vencida').hidden = !vencida;

  // Reinicia la animación del disco en cada entrada registrada
  const ficha = $('resultado');
  ficha.classList.remove('recien');
  if (confirmacion) {
    void ficha.offsetWidth;
    ficha.classList.add('recien');
  }
  mostrarPanel('resultado');
}

/* Formulario */

function mostrarErrorReferencia(mensaje) {
  $('error-referencia').textContent = mensaje;
  const entrada = $('campo-referencia');
  if (mensaje) entrada.setAttribute('aria-invalid', 'true');
  else entrada.removeAttribute('aria-invalid');
}

function bloquearFormulario(bloqueado) {
  $('campo-referencia').disabled = bloqueado;
  $('registrar').disabled = bloqueado;
}

function liberarFormulario(limpiar = true) {
  bloquearFormulario(false);
  if (limpiar) $('campo-referencia').value = '';
  $('campo-referencia').focus();
}

function enviarEntrada(evento) {
  evento.preventDefault();
  mostrarErrorReferencia('');

  const texto = $('campo-referencia').value.trim();
  if (!REFERENCIA_VALIDA.test(texto) || Number(texto) < 1) {
    mostrarErrorReferencia('Escribe el número de referencia del socio (solo dígitos).');
    $('campo-referencia').focus();
    return;
  }
  registrar(Number(texto));
}

/* Registro de entrada */

async function registrar(numero, permitirVencida = false) {
  bloquearFormulario(true);
  try {
    const entrada = await api('/attendance', {
      metodo: 'POST',
      datos: { num_referencia: numero, permitir_membresia_vencida: permitirVencida },
    });
    // CA1: nombre del socio y hora de entrada
    numeroPendiente = null;
    pintarResultado(entrada.num_referencia_unico, entrada.socio_nombre, {
      confirmacion: `Entrada registrada a las ${horaDe(entrada.date_time)}.`,
    });
    liberarFormulario();
    await cargarEntradas();
  } catch (error) {
    manejarErrorRegistro(error, numero);
  }
}

function manejarErrorRegistro(error, numero) {
  const detalle = error instanceof ErrorApi ? error.cuerpo?.detail : null;

  if (error instanceof ErrorApi && error.estado === 409 && detalle?.codigo === 'MEMBRESIA_VENCIDA') {
    // CA2: el Encargado decide. El campo sigue bloqueado hasta que elija.
    numeroPendiente = numero;
    pintarResultado(numero, detalle.socio_nombre, { vencida: true });
    botonesDecision(false);
    // El foco va a la opción segura: un Enter de más no debe dejar pasar a nadie
    $('rechazar-entrada').focus();
    return;
  }

  numeroPendiente = null;
  if (error instanceof ErrorApi && error.estado === 404) {
    // CA3: no se guardó ningún registro
    mostrarError('Socio no encontrado', `No existe el número ${numero} en este gimnasio.`);
    liberarFormulario();
    return;
  }

  mostrarError('No se pudo registrar la entrada', mensajeDe(error));
  liberarFormulario(false);
}

function botonesDecision(deshabilitados) {
  $('permitir-entrada').disabled = deshabilitados;
  $('rechazar-entrada').disabled = deshabilitados;
}

function decidirMembresiaVencida(permitir) {
  const numero = numeroPendiente;
  if (numero === null) return;
  // Un solo clic: evita registrar dos veces la misma entrada
  botonesDecision(true);
  if (permitir) {
    registrar(numero, true);
  } else {
    numeroPendiente = null;
    mostrarPanel('vacio');
    liberarFormulario();
  }
}

/* Entradas recientes */

// La API devuelve la fecha sin zona horaria (UTC); sin la "Z" el navegador la
// leería como hora local y mostraría la hora corrida.
function aFecha(iso) {
  const conZona = /[zZ]$|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`;
  return new Date(conZona);
}

function horaDe(iso) {
  return aFecha(iso).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
}

function momentoDe(iso) {
  const fecha = aFecha(iso);
  if (fecha.toDateString() === new Date().toDateString()) return horaDe(iso);
  return fecha.toLocaleString('es-MX', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

async function cargarEntradas() {
  const consulta = ++cargaVigente;
  try {
    const entradas = await api(`/attendance/recent?limit=${ENTRADAS_RECIENTES}`);
    if (consulta === cargaVigente) pintarEntradas(entradas);
  } catch (error) {
    if (consulta !== cargaVigente) return;
    $('lista-entradas').replaceChildren();
    $('estado-entradas').textContent = mensajeDe(error);
  }
}

function pintarEntradas(entradas) {
  $('lista-entradas').replaceChildren(...entradas.map(crearEntrada));
  $('estado-entradas').textContent =
    entradas.length === 0 ? 'Aún no hay entradas en este gimnasio.' : '';
}

function crearEntrada(entrada) {
  const disco = document.createElement('span');
  disco.className = 'lista-disco';
  disco.textContent = entrada.num_referencia_unico;
  const nombre = document.createElement('span');
  nombre.className = 'lista-nombre';
  nombre.textContent = entrada.socio_nombre;
  const hora = document.createElement('span');
  hora.className = 'entrada-hora';
  hora.textContent = momentoDe(entrada.date_time);

  const fila = document.createElement('li');
  fila.className = 'entrada';
  fila.append(disco, nombre, hora);
  return fila;
}

/* Arranque */

// Solo los Encargados registran entradas (el endpoint exige rol MANAGER).
const usuarioActual = checkAuthRouteProtection(['MANAGER']);

if (usuarioActual) {
  $('selector-gimnasio').addEventListener('change', cambiarGimnasio);
  $('form-entrada').addEventListener('submit', enviarEntrada);
  $('permitir-entrada').addEventListener('click', () => decidirMembresiaVencida(true));
  $('rechazar-entrada').addEventListener('click', () => decidirMembresiaVencida(false));

  mostrarPanel('vacio');
  cargarGimnasios(usuarioActual).catch(() => {});
  cargarEntradas();
  $('campo-referencia').focus();
}
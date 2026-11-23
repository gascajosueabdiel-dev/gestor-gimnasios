/**
 * Servicio de Autenticación en Vanilla JS para consumo de FastAPI.
 */
const API_BASE_URL = '/api/v1';
const TOKEN_KEY = 'jwt_access_token';

/**
 * Realiza el inicio de sesión contra el endpoint /api/v1/auth/login.
 * @param {string} email 
 * @param {string} password 
 */
async function loginUser(email, password) {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Error al iniciar sesión');
    }

    // Almacenamiento seguro en LocalStorage
    localStorage.setItem(TOKEN_KEY, data.access_token);
    return { success: true };

  } catch (error) {
    return { success: false, message: error.message };
  }
}

/**
 * Decodifica el payload de un JWT codificado en Base64 URL.
 * @param {string} token 
 */
function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

/**
 * Obtiene el token activo de LocalStorage.
 * Valida la expiración del token en cliente antes de enviarlo.
 */
function getValidToken() {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return null;

  const payload = parseJwt(token);
  if (!payload || !payload.exp) {
    logoutUser();
    return null;
  }

  // Compara fecha de expiración en segundos con el tiempo actual
  const currentTime = Math.floor(Date.now() / 1000);
  if (payload.exp < currentTime) {
    logoutUser();
    return null;
  }

  return token;
}

/**
 * Obtiene los datos del usuario logueado almacenados en el token.
 */
function getCurrentUserData() {
  const token = getValidToken();
  return token ? parseJwt(token) : null;
}

/**
 * Cierra la sesión activa borrando el almacenamiento local.
 */
function logoutUser() {
  localStorage.removeItem(TOKEN_KEY);
  window.location.href = '/login.html';
}

/**
 * Protege una ruta verificando si hay token válido y roles permitidos.
 * @param {Array<string>} allowedRoles 
 */
function checkAuthRouteProtection(allowedRoles = []) {
  const user = getCurrentUserData();
  if (!user) {
    window.location.href = '/login.html';
    return null;
  }

  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    alert('No tiene permisos para acceder a esta sección.');
    window.location.href = '/dashboard.html';
    return null;
  }

  return user;
}
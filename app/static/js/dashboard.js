// Verificar autenticación al cargar la página
const currentUser = checkAuthRouteProtection();

if (currentUser) {
  document.getElementById('user-id').textContent = currentUser.user_id;
  document.getElementById('user-role').textContent = currentUser.role;
  document.getElementById('user-gyms').textContent = currentUser.gym_ids.join(', ') || 'Ninguno';
}

/**
 * Consulta un gimnasio específico agregando el Bearer Token en los encabezados.
 * Maneja los códigos 401 y 403 según las reglas RBAC.
 */
async function fetchGymData(gymId) {
  const token = getValidToken();
  const resultContainer = document.getElementById('api-result');

  try {
    const response = await fetch(`/api/v1/gyms/${gymId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const data = await response.json();

    if (response.status === 401) {
      alert('Sesión expirada o no autorizada. Redirigiendo a Login...');
      logoutUser();
      return;
    }

    if (response.status === 403) {
      resultContainer.textContent = `Error 403 Forbidden: ${data.detail}`;
      return;
    }

    resultContainer.textContent = JSON.stringify(data, null, 2);

  } catch (error) {
    resultContainer.textContent = `Error de red: ${error.message}`;
  }
}
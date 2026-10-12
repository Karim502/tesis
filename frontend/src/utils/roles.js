// Única fuente de verdad de roles y rutas en el frontend.
export const ROLES = {
  DUENO_MYPE: "DUENO_MYPE",
  AUDITOR: "AUDITOR",
  ADMIN: "ADMIN",
};

// Ruta de inicio por rol. La redirección post-login usa SIEMPRE este mapa
// (nunca una URL enviada por el servidor o por query string => sin "open redirect").
export const ROLE_HOME = {
  [ROLES.DUENO_MYPE]: "/dashboard-mype",
  [ROLES.AUDITOR]: "/dashboard-auditor",
  [ROLES.ADMIN]: "/admin-panel",
};

export const ROLE_LABEL = {
  [ROLES.DUENO_MYPE]: "Dueño de MYPE",
  [ROLES.AUDITOR]: "Auditor",
  [ROLES.ADMIN]: "Administrador",
};

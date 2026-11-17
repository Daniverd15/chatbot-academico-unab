// Inyecta la URL y la API key de la app desde variables de entorno al compilar,
// para no dejar la clave en el repositorio:
//   APP_API_KEY=... API_URL=https://n8n.<ip>.sslip.io/webhook npx expo prebuild
module.exports = ({ config }) => ({
  ...config,
  extra: {
    ...config.extra,
    apiUrl: process.env.API_URL || config.extra?.apiUrl,
    apiKey: process.env.APP_API_KEY || config.extra?.apiKey,
  },
});

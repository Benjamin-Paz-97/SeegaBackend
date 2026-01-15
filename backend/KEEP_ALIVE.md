# Mantener el Backend Activo en Render (Free Tier)

Render en el plan gratuito "duerme" los servicios después de 15 minutos de inactividad. Para mantenerlo activo, usa un servicio de ping periódico.

## Opción 1: UptimeRobot (Recomendado - Gratis)

1. **Crear cuenta en UptimeRobot**
   - Ve a https://uptimerobot.com
   - Regístrate (gratis, hasta 50 monitores)

2. **Crear un monitor**
   - Click en "Add New Monitor"
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Seega Backend
   - **URL**: `https://seegabackend.onrender.com/health`
   - **Monitoring Interval**: 5 minutes (mínimo en plan gratis)
   - Click en "Create Monitor"

3. **Listo**
   - UptimeRobot hará ping cada 5 minutos
   - Esto mantendrá el backend activo

## Opción 2: cron-job.org (Gratis)

1. **Crear cuenta**
   - Ve a https://cron-job.org
   - Regístrate (gratis)

2. **Crear un cron job**
   - Click en "Create cronjob"
   - **Title**: Keep Render Alive
   - **Address**: `https://seegabackend.onrender.com/health`
   - **Schedule**: Cada 10 minutos (`*/10 * * * *`)
   - Click en "Create"

## Opción 3: GitHub Actions (Automático)

Puedo crear un workflow de GitHub Actions que haga ping cada 10 minutos.

## Opción 4: Pingdom (Gratis - Limitado)

1. Ve a https://www.pingdom.com
2. Crea un check HTTP cada 5 minutos

## Recomendación

**Usa UptimeRobot** porque:
- ✅ Gratis
- ✅ Fácil de configurar
- ✅ Dashboard para ver el estado
- ✅ Notificaciones si el servicio cae
- ✅ Ping cada 5 minutos (suficiente para mantener activo)

## Nota Importante

El endpoint `/health` es perfecto para esto porque:
- Es ligero (no consume recursos)
- Responde rápido
- No afecta el rendimiento del juego

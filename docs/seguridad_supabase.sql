-- =====================================================================
-- Seguridad de la tabla transferencias_panel (ejecutar en Supabase > SQL Editor)
-- Debe ejecutarlo quien administre el proyecto en Supabase.
--
-- ANTES de ejecutarlo:
--   1. Copiar la clave "service_role" (Project Settings > API) en el .env
--      del equipo que hace la carga, como:  SUPABASE_SERVICE_KEY=...
--      (esa clave NUNCA se comparte ni se sube a Git).
--   2. Dejar SUPABASE_KEY con la clave "anon" (solo lectura para el panel).
-- Si se ejecuta sin el paso 1, el cargador dejará de poder escribir.
-- =====================================================================

-- Activar seguridad por filas
alter table public.transferencias_panel enable row level security;

-- Permitir solo LECTURA con la clave anon (panel)
drop policy if exists "lectura_panel" on public.transferencias_panel;
create policy "lectura_panel"
  on public.transferencias_panel
  for select
  to anon, authenticated
  using (true);

-- No se crean políticas de insert/update/delete: con RLS activo quedan
-- bloqueadas para anon. La clave service_role (cargador) no se ve afectada.

# Test01 - Pruebas funcionales completas

## Pre-requisitos
- Entorno activo con `botConfigurable.bat` o `docker compose up -d`
- API: http://localhost:8000
- Frontend: http://localhost:5173
- DB/Postgres, Redis, MinIO levantados
- Migraciones aplicadas: `alembic upgrade head`
- `.env` configurado

## 1. Salud del sistema
| Test | Acción | Esperado |
|---|---|---|
| 1.1 Health | `GET http://localhost:8000/healthz` | `{"status":"ok"}` |
| 1.2 Ready | `GET http://localhost:8000/readyz` | `{"status":"ready"}` |
| 1.3 Métricas | `GET http://localhost:8000/metrics` | Texto Prometheus con métricas |

## 2. Webhook WhatsApp
| Test | Acción | Esperado |
|---|---|---|
| 2.1 Verificación | `GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=<TOKEN>&hub.challenge=12345` | Respuesta 200 con `12345` |
| 2.2 Firma inválida | `POST /webhook/whatsapp` con firma incorrecta | 403 |
| 2.3 Mensaje entrante | `POST /webhook/whatsapp` con payload JSON válido (sin firma si `WHATSAPP_APP_SECRET` vacío) | 200 `{"status":"ok"}` |
| 2.4 Idempotencia | Reenviar mismo `messages[0].id` | No duplica mensaje en `message` |

Payload ejemplo:
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{"id": "wamid.TEST123", "from": "5215512345678", "type": "text", "text": {"body": "Hola"}}]
      }
    }]
  }]
}
```

## 3. Multiinquilino + RLS
| Test | Acción | Esperado |
|---|---|---|
| 3.1 Tenant Session | Llamar con header `X-Tenant-ID: demo` usando `get_tenant_session` | `SET LOCAL app.tenant_id` aplicado |
| 3.2 Aislamiento | Crear datos con tenant A, consultar con tenant B | Sin resultados cruzados |
| 3.3 RLS activo | Verificar políticas en migración `0002_rls` | Todas las tablas con tenant_id tienen RLS |

## 4. Bandeja (Inbox)
| Test | Acción | Esperado |
|---|---|---|
| 4.1 Listado | `GET http://localhost:8000/inbox` | `{"items":[]}` (estructura correcta) |
| 4.2 Conversación directa | Tras webhook, verificar `conversation` con `kind=direct` | Creada correctamente |
| 4.3 Mensaje guardado | Verificar tabla `message` | `direction=inbound` guardado |

## 5. Outbox + Cola + SendPolicy
| Test | Acción | Esperado |
|---|---|---|
| 5.1 Encolar | Tras webhook, revisar `outbox_message` | Registro con `status=pending`, `idempotency_key` único |
| 5.1a SendPolicy allow | Evaluar sin bloqueos | `allowed: true` |
| 5.1b SendPolicy block | Payload con bloqueo/ventana cerrada | `blocked_reason` y `status=blocked` |
| 5.2 SKIP LOCKED | Ejecutar worker con 2 instancias simultáneas | Sin doble procesamiento |
| 5.3 Dead Letter | Forzar error tras reintentos | Movido a `dead_letter` |

## 6. Auth (JWT + RBAC)
| Test | Acción | Esperado |
|---|---|---|
| 6.1 Login | `POST http://localhost:8000/auth/login` | Tokens JWT/refresh |
| 6.2 Argon2 | Verificar hash con `argon2-cffi` | Verificación correcta |
| 6.2a RBAC | Acceso a rutas protegidas por rol | Denegado/Permitido según rol |
| 6.3 Audit Log | Acción sensible | Registro en `audit_log` |

## 7. Packs (Motor de packs)
| Test | Acción | Esperado |
|---|---|---|
| 7.1 Loader/Validator/Registry | Cargar manifiestos de `packs/*/manifest.yaml` | Validados correctamente |
| 7.2 Draft→Validate→Publish | Flujo completo | Estados correctos |
| 9.3 Golden Transcripts | Ejecutar `GoldenRunner` con transcripciones | `true` si pasan |
| 7.4 Tenant binding | Vincular tenant → pack_version | Activo correcto |
| 7.5 Rollback | Cambiar binding a versión anterior | Funciona |

## 8. Catálogo (Refacciones)
| Test | Acción | Esperado |
|---|---|---|
| 8.1 Búsqueda normalizada | Buscar `ABC-123` | Normalizado a `ABC123` |
| 8.tag Cascada completa | Buscar por NPC/OEM/alias/prefijo/trigram/fam/fitment | Orden correcto según cascada |
| 8.3 ItemIdentifier/ItemFitment | Verificar modelado estructurado | Datos correctado (marca/modelo/año) |
| 8.4 Imagen + caption | Respuesta con plantilla (sin LLM inventando SKU/precio) | Caption con SKU, marca, descripción, aplicación en negrita |
| 8.5 Importador CSV/XLSX | Importar archivo con errores | Reporte de errores claro |
| 8.6 Grounding gate | Intentar responder con SKU inventado | Bloqueado/registrado |
| 8.7 precision@1 | Medición sobre 50 consultas reales | Métrica calculable |

## 9. Agenda (Clínica/Servicios)
| Test | Acción | Esperado |
|---|---->|---|
| 9.1 Crear cita por conversación | Flujo de agendado | `appointment` creada |
| 9.2 Disponibilidad | Verificar solapamiento, horas, zonas horarias UTC | Sin doble reserva |
| 9.3 CalendarAdapter Google/Microsoft | Sincronización con `external_event_id` + `sync_token`/`etag` | Sincronizado correctamente |
| 9.4 Recordatorios duraderos | Programar recordatorio con `scheduled_task` | Sobrevive reinicio |
| 9.5 Cancelar/Reprogramar | Cambios por WhatsApp | Sincronizados |
| 9.6 Solicitud reseña | Tras cita completada con opt-in | Enlace generado vía `ReviewAdapter` (no publicar) |

## 10. Leads (Seguros)
| Test | Acción | Esperado |
|---|---|---|
| 10.1 Atribución UTM | Click-to-WhatsApp/QR con UTM | `lead.source` y `utm` guardados |
| 10.2 Calificación 3-5 preguntas | Flujo configurable | `lead.score` actualizado |
| 10.3 Round-robin persistido | Asignar con múltiples agentes | Equitativo y auditable, skip por horario/capacidad |
| 10.4 GoHighLevel vía outbox | Crear/Actualizar contacto, etiquetas, pipeline, automatismos | Sincronizado |
| 10.5 Panel embudo | Reporte leads por fuente/estado/citas | Métrica correcta |

## 11. Campañas
| Test | Acción | Esperado |
|---|---|---|
| 11.1 Segmentos versionados | Crear segmento | Versionado |
| 11.2 Dispatcher por lotes | Campaña a lista | Respeta rate-limit por WABA |
| 11.3 Límite marketing por usuario | Exceder límite | Detenido/bloqueado por destinatario |
| 11.4 Opt-in/Opt-out | Respuesta de opt-out | Agregado a `suppression_list` |
| 11.5 Quiet hours + zona horaria | Programar fuera/ dentro de horas | Respeta zona horaria del destinatario |
| 11.6 Métricas por destinatario | Estado entrega/lectura/respuesta/conversión/citas | Reportado correctamente |

## 12. Grupos (WhatsApp OBA + Telegram)
| Test | Acción | Esperado |
|---|---|---|
| 12.1 Webhook por group_id | Mensaje en grupo WhatsApp OBA | Detectado por `group_id` |
| 12.2 Envío con recipient_type:group | Enviar respuesta | Correcto |
| 12.3 Reglas por grupo | Solo si me mencionan/palabras clave/horarios/límites | Cumple reglas |
| 12.4 Gestión grupo OBA | Crear/borrar/enlace/invitación/expulsar participantes | Acciones correctas |
| 12.5 Telegram grupos | Mensaje en grupo Telegram | Respuesta correcta |
| 12.6 Límites OBA | Verificar 8 participantes max, ingreso por invitación, sin métricas plantillas | Documentado/cumplido |
| 12.7 Contexto grupo + auditoría | Historial respuestas bot en grupos | Registrado |

## 13. Canal Instagram
| Test | Acción | Esperado |
|---|---|---|
| 13.1 capabilities() | Verificar adaptador Instagram | `templates:false, window_24h:false` |
| 13.2 Sin plantillas | Intentar enviar plantilla | Bloqueado/gestionado por SendPolicy |
| 13.2a Human agent tag 7 días | Gestión ventana 7 días | Aplicado correctamente |
| 13.3 Handoff bot↔humano | Tomar control desde panel | Funciona desde bandeja |

## 14. Frontend (Panel)
| Test | Acción | Esperado |
|---|---|---|
| 14.1 Login panel | Acceder a http://localhost:5173 | Formulario login |
| 14.2 Bandeja unificada | Ver conversaciones directas/grupos/Instagram | Listado correcto |
| 14.3 Handoff | Bot/Humano, asignación, notas internas, etiquetas | Funcional |
| 14.4 Catálogo CRUD | Alta/editar productos, import CSV/XLSX | Funcional |
| 14.5 Agenda panel | Vista calendario, agendar/modificar/cancelar | Funcional |
| 14.6 Leads/Embudo | Pipeline, asignación, filtros | Funcional |
| 14.7 Campañas | Crear segmento, lanzar campaña, métricas | Funcional |
| 14.8 Packs admin | Listado, validar, publish/rollback (Fase 8 base) | Funcional |
| 14.9 Auditoría | Ver `audit_log` | Accesible según rol |

## 15. Pruebas de arquitectura y calidad
| Test | Acción | Esperado |
|---|---|---|
| 15.1 Tests unitarios | `pytest tests/unit -q -o addopts=""` | PASSED |
| 15.2 Tests integración | `pytest tests/integration -q -o addopts=""` | PASSED |
| 15.3 Tests arquitectura | `pytest tests/architecture -q -o addopts=""` | PASSED (routers thin, no direct SessionLocal, RLS) |
| 15.4 Lint | `ruff check .` | Sin errores |
| 15.5 Type check | `mypy apps` | Sin errores (strict) |
| 15.6 Cobertura críticos | Revisar módulos messaging/flows/catalog/scheduling/leads | >= 80% objetivo |

## 16. End-to-End completo (según plan maestro)
Ejecutar los 4 guiones de `docs/HUMAN_TEST_PLAN.md`:
1. **Consulta número de parte** → imagen + caption (plantilla, sin inventar SKU/precio)
2. **Agendar/reprogramar/cancelar cita** → sincronizado con Google Calendar, recordatorio
3. **Lead click-to-WhatsApp** → calificación → cita → GoHighLevel con etiqueta/agente
4. **Campaña segmentada** → opt-out y bloqueo por límite de marketing
5. **Grupos (OBA)** → crear grupo, invitación, mensaje → respuesta bot

## Checklist final
- [ ] Salud OK
- [ ] Webhook verificado
- [ ] RLS y multiinquilino OK
- [ ] Outbox/cola funcionando
- [ ] Auth/RBAC OK
- [ ] Packs validados
- [ ] Todos los verticales probados
- [ ] Grupos probados (si OBA disponible)
- [ ] Tests arquitectura OK
- [ ] Frontend operativo
- [ ] Documentación actualizada

## Notas
- Siempre usar body crudo para verificación de firma
- Nunca instanciar dependencias directamente (usar DI)
- Grounding gate obligatorio
- SendPolicy obligatorio
- Todos eventos de consentimiento deben registrarse
- URLs de medios Meta expiran - reingestar
- Grupos limitados a 8 participantes
- No publicar reseñas por API
- voz no implementado
- n8n no en ruta crítica
- Editor visual de packs fase 8
- Base vectorial dedicada no necesaria (pgvector)
- Columna queue no broker - Postgres SKIP LOCKED
- Redestribuir mediante tenant_session + RLS
- Debounce 2.5s + lock por conversación
- flow_instance persistido (no Redis)
- pack_version guardado por conversación
- campaign_recipient por destinatario
- item_identifier/item_fitment estructurados
- external_event_id + sync_token evitar doble reserva
- consent_event append-only
- outbox_message.idempotency_key
- webhook_event unique(provider_message_id)

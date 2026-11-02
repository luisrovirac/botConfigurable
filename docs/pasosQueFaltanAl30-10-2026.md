
Te faltan 6 pasos. Del 1 al 4 hacen que el bot funcione con el número de prueba; el 5 y el 6 lo dejan listo para clientes
  reales.

  ---

  Paso 1. Verificar que los mensajes llegan (sin token)

  Objetivo: confirmar que Meta → Cloudflare → el bot funciona. Un mensaje tuyo debe verse en el panel. En el teléfono todavía
  no te llegará respuesta.

  1. Desde tu teléfono, escribe "Hola" al número de prueba de Meta. Tu número tiene que estar en la lista de destinatarios del
     Paso 1 del asistente de Meta.
  2. En el servidor, revisa los logs:
  # Entrar a la carpeta del proyecto
  cd ~/projects/botconfigurable

  # Alias para no repetir el comando completo de docker compose
  alias botc='docker compose --env-file .env.production -f infra/docker-compose.prod.yml'

  # Ver los últimos logs del api (recibe el webhook) y del worker (procesa y "envía")
  botc logs --tail 50 api worker
  3. Abre https://botwhatsapp.devsax.site: la conversación debe aparecer con la respuesta del bot.

  Lo logras si:
  - En el panel aparece tu mensaje con la respuesta del bot.
  - En el log del worker aparece fake_message_sent con el texto del menú.

  Si falla:

  ┌─────────────────────────┬────────────────────────────┬─────────────────────────────────────────────────────────────────┐
  │    En el log aparece    │           Causa            │                             Arreglo                             │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Invalid signature (403) │ WHATSAPP_APP_SECRET        │ Cópialo de nuevo desde Meta → Configuración → Básica y ejecuta  │
  │                         │ incorrecto                 │ sh scripts/deploy.sh                                            │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ webhook_unknown_channel │ SEED_PHONE_NUMBER_ID no    │ Copia el Identificador del número de teléfono (no el de la      │
  │                         │ coincide                   │ cuenta) y ejecuta sh scripts/deploy.sh                          │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Nada                    │ El webhook no llega        │ Revisa que en Webhooks esté suscrito el campo messages. Si      │
  │                         │                            │ sigue sin llegar, publica la app de Meta (paso 6)               │
  └─────────────────────────┴────────────────────────────┴─────────────────────────────────────────────────────────────────┘

  ---

  Paso 2. Conseguir un token de acceso (temporal)

  Objetivo: tener la credencial que permite al bot enviar mensajes por la API de Meta.

  1. En Meta for Developers → tu app → WhatsApp → Configuración de la API.
  2. Pulsa Generar token de acceso y cópialo. Empieza con EAA....

  Lo logras si: tienes el token copiado. Dura 24 horas, suficiente para probar; el paso 5 lo cambia por uno permanente.

  ---

  Paso 3. Activar el envío real

  Objetivo: que el bot deje de simular y envíe las respuestas por WhatsApp.

  # Ir al proyecto
  cd ~/projects/botconfigurable

  # Editar la configuración de producción
  nano .env.production

  # Dentro del archivo, cambia estas dos líneas:
  #   WHATSAPP_SEND_MODE=real
  #   WHATSAPP_ACCESS_TOKEN=EAA...el token del paso 2...
  # Guarda con Ctrl+O, Enter, y sal con Ctrl+X

  # Aplicar el cambio (reconstruye y reinicia; termina mostrando "ready")
  sh scripts/deploy.sh

  Lo logras si: deploy.sh termina con {"status":"ready","database":"ok"}.

  ---

  Paso 4. Prueba completa desde el teléfono

  Objetivo: confirmar que funciona todo el ciclo: escribes, el bot responde en tu teléfono y el panel muestra los estados.

  Escribe al número de prueba, uno por uno:

  ┌─────┬─────────────┬───────────────────────────────────────────────────────┐
  │  #  │   Escribe   │                      Debe pasar                       │
  ├─────┼─────────────┼───────────────────────────────────────────────────────┤
  │ 1   │ Hola        │ Te llega el menú del bot                              │
  ├─────┼─────────────┼───────────────────────────────────────────────────────┤
  │ 2   │ 1           │ Te llega el horario y el menú otra vez                │
  ├─────┼─────────────┼───────────────────────────────────────────────────────┤
  │ 3   │ quiero algo │ El bot dice que no entendió y repite el menú          │
  ├─────┼─────────────┼───────────────────────────────────────────────────────┤
  │ 4   │ BAJA        │ El bot confirma la baja                               │
  ├─────┼─────────────┼───────────────────────────────────────────────────────┤
  │ 5   │ 2           │ No te llega nada; en el panel sale en rojo: Bloqueado │
  ├─────┼─────────────┼───────────────────────────────────────────────────────┤
  │ 6   │ ALTA        │ El bot confirma el alta y vuelve a responder          │
  └─────┴─────────────┴───────────────────────────────────────────────────────┘

  En el panel, las respuestas deben pasar a Entregado y luego a Leído cuando las abras.

  # Si no te llegan las respuestas, busca errores de envío en el worker
  botc logs --tail 100 worker | grep -E "outbox_retry|outbox_failed"

  Si falla:

  ┌────────────┬─────────────────────────────────┬─────────────────────────────────────────────────────────────────────────┐
  │ Error de   │              Causa              │                                 Arreglo                                 │
  │    Meta    │                                 │                                                                         │
  ├────────────┼─────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 401 /      │ Token vencido o mal copiado     │ Genera otro (paso 2), cámbialo en .env.production y ejecuta deploy.sh   │
  │ código 190 │                                 │                                                                         │
  ├────────────┼─────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ código     │ Tu número no está en la lista   │ Agrégalo en Configuración de la API. Si eres de México: Meta puede      │
  │ 131030     │ de destinatarios permitidos     │ enviar tu número como 521... y la lista lo tiene como 52...; agrégalo   │
  │            │                                 │ de las dos formas                                                       │
  └────────────┴─────────────────────────────────┴─────────────────────────────────────────────────────────────────────────┘

  Lo logras si: los 6 pasos se comportan como en la tabla.

  ---

  Paso 5. Token permanente

  Objetivo: que el bot no deje de enviar cada 24 horas cuando vence el token temporal.

  1. Entra a business.facebook.com → Configuración del negocio → Usuarios → Usuarios del sistema.
  2. Agregar, ponle un nombre (ej. bot-whatsapp) y el rol Administrador.
  3. Asignar activos: elige tu app (control total) y tu cuenta de WhatsApp (control total).
  4. Generar token:
     - Elige tu app.
     - Caducidad: Nunca.
     - Permisos: whatsapp_business_messaging y whatsapp_business_management.
  5. Copia el token. Solo se muestra una vez.

  # Reemplazar el token temporal por el permanente
  cd ~/projects/botconfigurable
  nano .env.production
  #   WHATSAPP_ACCESS_TOKEN=EAA...token permanente...

  # Aplicar
  sh scripts/deploy.sh

  Lo logras si: al día siguiente el bot sigue respondiendo sin que hayas tocado nada.

  ---

  Paso 6. Pasar a producción (número real y clientes reales)

  Objetivo: que cualquier cliente pueda escribirle al bot, no solo los números de prueba. Corresponde al Paso 2 y Paso 3 del
  asistente de Meta de tu captura.

  1. Publicar la app de Meta.
     - En Configuración → Básica, pon una URL de política de privacidad (puede ser una página simple en devsax.site).
     - Cambia la app a modo Activo / Publicado.
  2. Paso 2 de Meta: Configuración de producción.
     - Agrega el número real del negocio. No puede estar usando la app normal de WhatsApp.
     - Verifícalo con el código SMS o la llamada.
     - Agrega un método de pago.
  3. Actualizar el bot con el número nuevo, porque cambia el phone_number_id:
  cd ~/projects/botconfigurable
  nano .env.production
  #   SEED_PHONE_NUMBER_ID=<identificador del número real>

  # Aplicar (el seed registra el número nuevo)
  sh scripts/deploy.sh
  4. Paso 3 de Meta: Verificación del negocio. Sube los documentos de la empresa. Sin esto, Meta limita cuántos clientes nuevos
     puedes contactar al día.

  Lo logras si: alguien que no está en la lista de prueba escribe al número real y el bot le responde.

  ---

  Mi recomendación es hacer los pasos 1 a 4 hoy, el 5 apenas confirmes que todo funciona, y el 6 cuando quieras abrirlo a
  clientes
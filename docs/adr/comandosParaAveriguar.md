
luis@serversax:~/projects/botConfigurable$   # Alias para no repetir el comando completo de docker compose
  alias botc='docker compose --env-file .env.production -f infra/docker-compose.prod.yml'

  # == 2. Configuracion: muestra el modo de envio, la version de la API y el ID del numero
  grep -E '^(ENVIRONMENT|WHATSAPP_SEND_MODE|META_API_VERSION|SEED_PHONE_NUMBER_ID)=' .env.production

  # == 2b. Claves secretas: solo muestra cuantos caracteres tiene cada una (0 = vacia)
  for k in WHATSAPP_APP_SECRET WHATSAPP_ACCESS_TOKEN WHATSAPP_VERIFY_TOKEN; do v=$(grep -E "^$k=" .env.production | cut -d= -f2-); echo "$k: largo=${#v}"; done

  # == 3. Salud: local y por internet; ambos deben decir "status":"ready"
  curl -s http://127.0.0.1:8030/readyz; echo; curl -s https://botwhatsapp.devsax.site/readyz; echo

  # == 4. Logs de los ultimos 4 dias: mensajes recibidos, firma, envios y errores
  botc logs --since 96h --no-log-prefix api worker 2>&1 | grep -iE "webhook|signature|unknown_channel|fake_message_sent|outbox|error" | tail -40

  # == 5a. Numeros de WhatsApp registrados en el bot
  botc exec -T db psql -U botowner -d botconfigurable -c "select phone_number_id, created_at from channel_account;"

  # == 5b. Mensajes que llegaron de Meta, por estado
  botc exec -T db psql -U botowner -d botconfigurable -c "select status, count(*) from webhook_event group by 1;"

  # == 5c. Mensajes recibidos (inbound) y enviados (outbound), por estado
  botc exec -T db psql -U botowner -d botconfigurable -c "select direction, status, count(*), max(created_at) from message group by 1,2 order by 1,2;"

  # == 5d. Cola de envios, por estado
  botc exec -T db psql -U botowner -d botconfigurable -c "select status, count(*) from outbox_message group by 1;"

  # == 5e. Ultimos envios que fallaron del todo
  botc exec -T db psql -U botowner -d botconfigurable -c "select left(error,200) as error, created_at from dead_letter order by created_at desc limit 5;"
SEED_PHONE_NUMBER_ID=1399286213261545
WHATSAPP_SEND_MODE=fake
META_API_VERSION=v26.0
WHATSAPP_APP_SECRET: largo=32
WHATSAPP_ACCESS_TOKEN: largo=0
WHATSAPP_VERIFY_TOKEN: largo=32
{"status":"ready","database":"ok"}
{"status":"ready","database":"ok"}
INFO:     172.24.0.5:56134 - "GET /api/v1/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=3dd98a8ee261ebb86b277d6c4bc1a59a&hub.challenge=funciona HTTP/1.1" 200 OK
INFO:     172.24.0.5:41476 - "GET /api/v1/webhook/whatsapp?hub.mode=subscribe&hub.challenge=708015803&hub.verify_token=3dd98a8ee261ebb86b277d6c4bc1a59a&hub_mode=subscribe&hub_challenge=708015803&hub_verify_token=3dd98a8ee261ebb86b277d6c4bc1a59a HTTP/1.1" 200 OK
{"phone_number_ids": ["123456123"], "event": "webhook_unknown_channel", "level": "warning", "logger": "api.v1.webhook", "timestamp": "2026-10-30T18:41:45.449555Z"}
INFO:     172.24.0.5:56436 - "POST /api/v1/webhook/whatsapp HTTP/1.1" 200 OK
 phone_number_id  |          created_at
------------------+-------------------------------
 1399286213261545 | 2026-10-30 18:07:40.807429+00
(1 row)

 status | count
--------+-------
(0 rows)

 direction | status | count | max
-----------+--------+-------+-----
(0 rows)

 status | count
--------+-------
(0 rows)

 error | created_at
-------+------------
(0 rows)

#***

# Alias para docker compose
alias botc='docker compose --env-file .env.production -f infra/docker-compose.prod.yml'

# Logs de los ultimos 10 minutos: mensaje recibido, envio y errores
botc logs --since 10m --no-log-prefix api worker 2>&1 | grep -iE "webhook|signature|unknown_channel|outbox|error" | tail -20

# Mensajes guardados, por direccion y estado
botc exec -T db psql -U botowner -d botconfigurable -c "select direction, status, count(*), max(created_at) from message group by 1,2 order by 1,2;"

#***
# Cargar el token en una variable (no lo muestra en pantalla)
TOKEN=$(grep -E '^WHATSAPP_ACCESS_TOKEN=' .env.production | cut -d= -f2-)

# Conectar tu app (Nexosax) a la cuenta de mensajes. Debe responder {"success":true}
curl -s -X POST -H "Authorization: Bearer $TOKEN" "https://graph.facebook.com/v26.0/2230785787702270/subscribed_apps"; echo

# Comprobar: ahora debe aparecer tambien Nexosax en la lista
curl -s -H "Authorization: Bearer $TOKEN" "https://graph.facebook.com/v26.0/2230785787702270/subscribed_apps"; echo

#Si sale {"success":true}, escríbele de nuevo Hola al bot desde tu WhatsApp. Espera unos 10 segundos y ejecuta:

# Logs de los ultimos 10 minutos: mensaje recibido, envio y errores
botc logs --since 10m --no-log-prefix api worker 2>&1 | grep -iE "webhook|signature|unknown_channel|outbox|error" | tail -20

# Mensajes guardados, por direccion y estado
botc exec -T db psql -U botowner -d botconfigurable -c "select direction, status, count(*), max(created_at) from message group by 1,2 order by 1,2;"


# Ultimos mensajes: entrada/salida, texto (recortado) y estado
botc exec -T db psql -U botowner -d botconfigurable -c "select direction, left(body,40) as texto, status, created_at from message order by created_at desc limit 15;"

#***

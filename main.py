from flask import Flask, request, jsonify
from heyoo import WhatsApp
import random, redis, json
import datetime,os
from google.cloud import vision
from dotenv import load_dotenv


app = Flask(__name__)

load_dotenv()
token_facebook = os.getenv("VERIFY_TOKEN")
id_numero = os.getenv("ID_NUMERO")


# Configuración de Redis local
r = redis.Redis(host='localhost', port=6379, decode_responses=True)


# Funciones para manejar sesión por usuario
def cargar_sesion(telefono):
    datos = r.get(f"chatbot:{telefono}")
    return json.loads(datos) if datos else None

def guardar_sesion(telefono, datos):
    r.set(f"chatbot:{telefono}", json.dumps(datos), ex=86400)  # expira en 1 día

def eliminar_sesion(telefono):
    r.delete(f"chatbot:{telefono}")

wa = WhatsApp(token_facebook, id_numero)

# Preguntas del flujo
flujo = [
    "Por favor escribe tu nombre completo.",
    "¿En qué tienda hiciste tu compra?",
    "¿Cuál fue el monto total de tu compra?",
    "¿Cuál es tu ocupación?\n1. Contratista\n2. Electricista\n3. Otro",
    "¿Qué festeja Indiana en el mes de Junio?\n1. El mes del cable\n2. El día del niño\n3. 14 Feb",
    "¿Por qué medio te enteraste de la promoción?\n\n1. Radio\n2. Cartel publicitario\n3. En tienda\n4. Correo electrónico",
    "Por favor envía una foto clara de tu ticket de compra participante."
]
premios = [
    "Cinemex ticket doble tradicional",
    "Certificado Amazon $500",
    "Bolsa con clip para herramientas",
    "Juego de alicates 8 piezas",
    "Peiono 25 en 1",
    "Audifonos inalambricos",
    "Maleta Organizador de herramientas",
    "Pantalla 32",
    "Subwoofer con microfono",
    "Kit Milwaukee",
    "Kit Grill"
    ]

WEBHOOK_VERIFY_TOKEN = "indiana123"  # Mismo que colocas en el panel de Meta

# ✅ UNIFICADO PARA ACEPTAR /webhook Y /webhook/
@app.route("/webhook", methods=["GET", "POST"])
@app.route("/webhook/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
            print("✅ Webhook verificado exitosamente")
            return challenge, 200
        else:
            return "❌ Token inválido", 403

    if request.method == "POST":
        data = request.get_json()
        #print("📩 MENSAJE RECIBIDO:", data)

        try:
            mensaje = data['entry'][0]['changes'][0]['value']['messages'][0]
            print("📩 MENSAJE RECIBIDO:", mensaje)
            telefono = mensaje['from']
            tipo = mensaje['type']
            usuario = cargar_sesion(telefono)

            texto = ""

            if "interactive" in mensaje and mensaje["interactive"].get("type") == "button_reply":
                texto = mensaje["interactive"]["button_reply"]["title"].strip()
                tipo = "text"
            elif "text" in mensaje and "body" in mensaje["text"]:
                texto = mensaje["text"]["body"].strip()
                tipo = "text"

            # INICIO DEL CAMBIO 1: Flujo ya terminado - preguntar monto
            if texto.upper() == "PARTICIPAR":
                if not usuario:
                    usuario = {"paso": 0, "respuestas": {}, "tickets": []}
                    guardar_sesion(telefono, usuario)
                    wa.send_message(f"Hola 👋 Bienvenido...\n\n{flujo[0]}", telefono)
                    return jsonify({"status": "ok"})
                elif usuario["paso"] == -1:
                    usuario["paso"] = 98  # Paso especial para validar monto nuevo
                    guardar_sesion(telefono, usuario)
                    wa.send_message("💵 ¿Cuál fue el monto total del ticket que deseas registrar?", telefono)
                    return jsonify({"status": "preguntando monto nuevo ticket"})
            # FIN DEL CAMBIO 1

            if not usuario:
                wa.send_message("Por favor escribe la palabra: PARTICIPAR para iniciar.", telefono)
                return jsonify({"status": "esperando PARTICIPAR"})
            
            # <-- BLOQUES REORDENADOS INICIAN AQUÍ -->

            if texto.upper() == "SALIR":
                usuario["paso"] = -1
                guardar_sesion(telefono, usuario)
                wa.send_message("✅ Gracias. Puedes volver a participar más tarde escribiendo *PARTICIPAR*.", telefono)
                return jsonify({"status": "salida voluntaria"})

            if texto.upper() == "PARTICIPAR" and usuario["paso"] == -1:
                usuario["paso"] = 98
                guardar_sesion(telefono, usuario)
                wa.send_message("💵 ¿Cuál fue el monto total del ticket que deseas registrar?\n(O escribe SALIR para terminar)", telefono)
                return jsonify({"status": "reentrada tras PARTICIPAR"})

            if usuario["paso"] == -1:
                usuario["paso"] = 98
                guardar_sesion(telefono, usuario)
                wa.send_message("💵 ¡Vemos que ya has registrado tickets!\n¿Cuál fue el monto total del nuevo ticket que deseas registrar?\n(O escribe SALIR para terminar)", telefono)
                return jsonify({"status": "retomando paso -1"})

            # <-- BLOQUES REORDENADOS TERMINAN AQUÍ -->

            # NUEVO BLOQUE - MANEJAR paso 98 (monto para nuevo ticket)
            if usuario["paso"] == 98:
                if texto.upper() in ["SALIR", "NO"]:
                    usuario["paso"] = -1
                    guardar_sesion(telefono, usuario)
                    wa.send_message("✅ Gracias. Puedes volver a participar más tarde escribiendo PARTICIPAR.", telefono)
                    return jsonify({"status": "salida del intento de nuevo ticket"})

                try:
                    monto = float(texto.replace(",", "").replace("$", ""))
                    if monto < 5000:
                        wa.send_message("❌ El ticket debe ser mayor a $5,000 para registrarse en la promoción.", telefono)
                        return jsonify({"status": "monto insuficiente nuevo ticket"})
                    else:
                        usuario["paso"] = 6
                        guardar_sesion(telefono, usuario)
                        wa.send_message("✅ Monto válido. Por favor envía la foto de tu ticket.", telefono)
                        return jsonify({"status": "esperando imagen nuevo ticket"})
                except ValueError:
                    wa.send_message("⚠️ Ingresa el monto como un número. Ejemplo: 5300", telefono)
                    return jsonify({"status": "monto inválido nuevo ticket"})

            # Usuario ya en flujo
            if usuario["paso"] == 99:
                if texto.lower() in ["sí", "si"]:
                    usuario["paso"] = 98
                    guardar_sesion(telefono, usuario)
                    wa.send_message("💵 ¿Cuál fue el monto total del ticket que deseas registrar?", telefono)
                    return jsonify({"status": "reentrada para nuevo ticket"})
                else:
                    total = len(usuario["tickets"])
                    wa.send_message(
                        f"¡Gracias por participar en El Mes del Cable!\n"
                        f"Registraste un total de *{total} ticket(s)*. 🧾\n"
                        "Recuerda que puedes seguir enviando tickets durante todo el mes para seguir ganando.\n\n"
                        "📣 Síguenos en redes sociales para conocer a los ganadores y nuevas promociones.",
                        telefono
                    )
                    usuario["paso"] = -1
                    guardar_sesion(telefono, usuario)
                    return jsonify({"status": "flujo reiniciado o terminado"})

            # Flujo normal (respondiendo preguntas)
            campos = ["nombre", "tienda", "monto", "ocupacion", "pregunta_festejo", "medio"]
            if usuario["paso"] < len(campos):
                campo_actual = campos[usuario["paso"]]

                if campo_actual == "monto":
                    try:
                        monto = float(texto.replace(",", "").replace("$", ""))
                        if monto < 5000:
                            wa.send_message(
                                "Gracias por participar. 💵 Tu ticket debe ser de al menos *$5,000* para participar en la promoción\n\n Regresa a participar con un ticket de compra mayor a $5000",
                                telefono
                            )
                            eliminar_sesion(telefono)
                            usuario["paso"] = -1
                            return jsonify({"status": "monto insuficiente"})
                        else:
                            usuario["respuestas"]["monto"] = monto
                            usuario["paso"] += 1
                    except ValueError:
                        wa.send_message(
                            "⚠️ Por favor ingresa el monto como un número. Ejemplo: 5200",
                            telefono
                        )
                        return jsonify({"status": "monto inválido"})

                elif campo_actual == "medio":
                    if texto not in ["1", "2", "3", "4"]:
                        wa.send_message("⚠️ Ingresa un número del 1 al 4:\n1. Radio\n2. Cartel\n3. En tienda\n4. Correo", telefono)
                        return jsonify({"status": "medio inválido"})
                    opciones_medio = {"1": "Radio", "2": "Cartel publicitario", "3": "En tienda", "4": "Correo electrónico"}
                    usuario["respuestas"]["medio"] = opciones_medio[texto]
                    usuario["paso"] += 1
                    guardar_sesion(telefono, usuario)
                    wa.send_message(flujo[usuario["paso"]], telefono)
                    return jsonify({"status": "respuesta guardada"})
                else:
                    usuario["respuestas"][campo_actual] = texto
                    usuario["paso"] += 1

                if campo_actual == "nombre":
                    wa.send_message(f"¡Gracias, {texto}! 🙌", telefono)

                # Botones
                if usuario["paso"] == 3:
                    wa.send_reply_button(
                        recipient_id=telefono,
                        button={
                            "type": "button",
                            "body": {"text": "¿Cuál es tu ocupación?"},
                            "action": {
                                "buttons": [
                                    {"type": "reply", "reply": {"id": "1", "title": "Contratista"}},
                                    {"type": "reply", "reply": {"id": "2", "title": "Electricista"}},
                                    {"type": "reply", "reply": {"id": "3", "title": "Otro"}},
                                ]
                            }
                        }
                    )
                elif usuario["paso"] == 4:
                    wa.send_reply_button(
                        recipient_id=telefono,
                        button={
                            "type": "button",
                            "body": {"text": "¿Qué festeja Indiana en Junio?"},
                            "action": {
                                "buttons": [
                                    {"type": "reply", "reply": {"id": "1", "title": "El mes del cable"}},
                                    {"type": "reply", "reply": {"id": "2", "title": "El día del niño"}},
                                    {"type": "reply", "reply": {"id": "3", "title": "14 Feb"}},
                                ]
                            }
                        }
                    )
                elif usuario["paso"] < len(flujo):
                    wa.send_message(flujo[usuario["paso"]], telefono)

                guardar_sesion(telefono, usuario)
                return jsonify({"status": "respuesta guardada"})

            # Si es imagen
            if tipo == "image" and usuario and usuario["paso"] in [6]:
                media_id = mensaje["image"]["id"]
                usuario["respuestas"]["ticket_photo"] = f"media:{media_id}"
                usuario["respuestas"]["timestamp"] = datetime.datetime.now().isoformat()

                usuario["tickets"].append(usuario["respuestas"].copy())
                usuario["respuestas"].clear()

                wa.send_message("⏳ Estamos validando tu ticket... Esto puede tomar unos segundos.", telefono)
                premio = random.choice(premios)
                wa.send_message(
                    f"🎉 ¡Tu ticket ha sido validado con éxito!\n\n🎁 ¡Felicidades! Ganaste: *{premio}*\n\n📦 En breve recibirás instrucciones para recibir tu premio en casa.",
                    telefono
                )

                wa.send_message("¿Tienes otro ticket? (Sí / No)", telefono)
                usuario["paso"] = 99
                guardar_sesion(telefono, usuario)
                return jsonify({"status": "ticket recibido"})

            return jsonify({"status": "sin cambios"})

        except Exception as e:
            print("❌ Error procesando el mensaje:", e)
            return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return "Chatbot Indiana funcionando", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
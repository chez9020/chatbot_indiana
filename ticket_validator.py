import os
import uuid
import requests
import io
import re
from google.cloud import vision
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Inicializar cliente de Vision
client = vision.ImageAnnotatorClient()

# Directorios
DIR_TO_PROCESS = "images_to_process"
DIR_PROCESSED = "images_processed"
os.makedirs(DIR_TO_PROCESS, exist_ok=True)
os.makedirs(DIR_PROCESSED, exist_ok=True)

# Función para obtener la URL temporal del medio
def obtener_media_url(media_id, token):
    url = f"https://graph.facebook.com/v20.0/{media_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('url')
    else:
        print(f"Error al obtener la URL del medio: {response.status_code} - {response.text}")
        return None

# Descargar imagen y guardarla localmente
def descargar_imagen_local(media_id, token, telefono):
    media_url = obtener_media_url(media_id, token)
    if media_url:
        response = requests.get(media_url, headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            nombre_archivo = f"{uuid.uuid4()}_{telefono}.jpg"
            ruta = os.path.join(DIR_TO_PROCESS, nombre_archivo)
            with open(ruta, 'wb') as f:
                f.write(response.content)
            return ruta
        else:
            print(f"Error al descargar imagen: {response.status_code}")
    return None

# OCR usando Google Vision
def detectar_texto(ruta_imagen):
    with io.open(ruta_imagen, "rb") as img:
        content = img.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    return response.text_annotations[0].description if response.text_annotations else ""

# Buscar total en el texto
def extraer_total_por_palabra_clave(texto):
    for linea in reversed(texto.splitlines()):
        if any(palabra in linea.upper() for palabra in ["TOTAL", "IMPORTE", "GRAN TOTAL", "SUBTOTAL"]):
            match = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})", linea)
            if match:
                try:
                    return float(match.group(0).replace(",", ""))
                except ValueError:
                    continue
    return None

# Buscar número más grande

def extraer_numero_mas_grande(texto):
    numeros = re.findall(r"(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})", texto)
    if numeros:
        try:
            return max([float(n.replace(",", "")) for n in numeros])
        except ValueError:
            return None
    return None

def validar_ticket_desde_media(media_id, token, telefono):
    media_url = obtener_media_url(media_id, token)
    if not media_url:
        return {"valido": False, "motivo": "No se pudo obtener la imagen"}

    ruta_imagen = descargar_imagen_local(media_id, token, telefono)
    if not ruta_imagen:
        return {"valido": False, "motivo": "No se pudo descargar la imagen"}

    texto_detectado = detectar_texto(ruta_imagen)

    total_palabra = extraer_total_por_palabra_clave(texto_detectado)
    total_mayor = extraer_numero_mas_grande(texto_detectado)

    os.makedirs("images_processed", exist_ok=True)
    os.rename(ruta_imagen, os.path.join("images_processed", os.path.basename(ruta_imagen)))

    if not texto_detectado or not total_palabra and not total_mayor:
        return {"valido": False, "motivo": "La imagen no parece un ticket"}

    monto = total_palabra or total_mayor

    if monto >= 5000:
        return {"valido": True, "monto": monto}
    else:
        return {"valido": False, "motivo": f"El monto detectado es menor a $5,000: ${monto:.2f}"}
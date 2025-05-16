import os
import re
import io
from google.cloud import vision
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credential_path

client = vision.ImageAnnotatorClient()
folder_path = "./img_to_process"

def detect_text_from_image(image_path):
    with io.open(image_path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description if texts else ""

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

def extraer_numero_mas_grande(texto):
    numeros = re.findall(r"(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})", texto)
    if numeros:
        try:
            numeros_float = [float(n.replace(",", "")) for n in numeros]
            return max(numeros_float)
        except ValueError:
            return None
    return None

# Procesar cada imagen
for file_name in os.listdir(folder_path):
    if file_name.lower().endswith((".png", ".jpg", ".jpeg")):
        full_path = os.path.join(folder_path, file_name)
        texto = detect_text_from_image(full_path)
        total_palabra_clave = extraer_total_por_palabra_clave(texto)
        numero_mas_grande = extraer_numero_mas_grande(texto)
        
        print(f"\n🧾 Ticket: {file_name}")
        print("-" * 50)
        print(texto[:300] + "..." if len(texto) > 300 else texto)
        print(f"📌 Monto por palabra clave: {'$' + str(total_palabra_clave) if total_palabra_clave else 'No encontrado'}")
        print(f"📊 Número más grande: {'$' + str(numero_mas_grande) if numero_mas_grande else 'No encontrado'}")
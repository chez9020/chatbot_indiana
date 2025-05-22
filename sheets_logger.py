import os
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Cargar variables de entorno
load_dotenv()

# Ruta al archivo de credenciales y ID de la hoja de cálculo
cred_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
sheet_id = os.getenv("GOOGLE_SHEETS_ID")

# Autenticación moderna
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials = Credentials.from_service_account_file(cred_path, scopes=scope)
client = gspread.authorize(credentials)
worksheet = client.open_by_key(sheet_id).sheet1

# Función para registrar un ticket
def registrar_ticket_en_sheets(datos_generales, ticket):
    fila = [
        datos_generales.get("telefono", ""),
        datos_generales.get("nombre", ""),
        datos_generales.get("tienda", ""),
        datos_generales.get("ocupacion", ""),
        datos_generales.get("medio", ""),
        ticket.get("nombre_archivo", ""),
        ticket.get("timestamp", ""),
        ticket.get("monto", "")
    ]
    worksheet.append_row(fila)
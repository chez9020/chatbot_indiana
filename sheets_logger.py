import os
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Cargar variables de entorno
load_dotenv()

# Ruta al archivo de credenciales y ID de la hoja de cálculo
cred_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
sheet_id = os.getenv("GOOGLE_SHEETS_ID")

# Autenticación con las credenciales del Service Account
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_file(cred_path, scopes=scopes)
client = gspread.authorize(credentials)

# Abrir la hoja
spreadsheet = client.open_by_key(sheet_id)
worksheet = spreadsheet.sheet1  # usa la primera hoja

# Buscar la primera columna vacía en la columna 'saludo'
# Si la hoja está vacía, escribimos encabezado
if worksheet.cell(1, 1).value != "saludo":
    worksheet.update("A1", "saludo")

# Agrega "Hola mundo" en la siguiente fila vacía
next_row = len(worksheet.col_values(1)) + 1
worksheet.update(f"A{next_row}", [["Hola mundo"]])

print(f"✅ Escrito en A{next_row}: Hola mundo")
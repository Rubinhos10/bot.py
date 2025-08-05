import requests
from bs4 import BeautifulSoup
from datetime import datetime
import yfinance as yf
import schedule
import time
import re
from flask import Flask
import threading

print("Hora del sistema:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# --- Configuración del bot de Telegram ---
TOKEN = "7600771185:AAFYO9DGU2YcSZgmMB6g3A6bCFPp3D1zaIU"
CHAT_ID = "225671791"

# --- Fondos y sus URLs en Investing ---
fondos = {
    "ES0175414012": {
        "nombre": "Dunas Valor Equilibrado R FI",
        "url": "https://es.investing.com/funds/es0175414012"
    },
    "IE00BD0NCM55": {
        "nombre": "iShares Developed World Index Fund (IE) D Acc Eur",
        "url": "https://es.investing.com/funds/ie00bd0ncm55"
    },
    "ES0140794001": {
        "nombre": "Gamma Global A FI",
        "url": "https://es.investing.com/funds/es0140794001"
    },
    "LU1508158430": {
        "nombre": "ASIAPF DV EQ ABS RT A2 AC EURH",
        "url": "https://es.investing.com/funds/lu1508158430"
    },
    "ES0175437005": {
        "nombre": "Dunas Valor Prudente R FI",
        "url": "https://es.investing.com/funds/es0175437005"
    }
}

acciones = {
    "GB0001500809": {
        "nombre": "Tullow Oil",
        "ticker": "TLW.L"
    },
    "ES0126962069": {
        "nombre": "Nueva Expresion Textil SA",
        "ticker": "NXT.MC"
    },
    "ES0109260531": {
        "nombre": "Amper",
        "ticker": "AMP"
    }
}

# Valores iniciales para primera ejecución (simulados)
valores_anteriores = {
    "fondos": {
        "ES0175414012": 12.662,
        "IE00BD0NCM55": 22.499,
        "ES0140794001": 12.366,
        "LU1508158430": 171.600,
        "ES0175437005": 114.569
    },
    "acciones": {
        "GB0001500809": 14.8,
        "ES0126962069": 0.450,
        "ES0109260531": 0.146
    }
}

valores_actuales = {}

# --- Enviar mensaje a Telegram ---
def enviar_mensaje(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": texto}
    r = requests.post(url, data=data)
    if r.status_code == 200:
        print("✅ Mensaje enviado correctamente.")
    else:
        print("❌ Error al enviar mensaje:", r.text)

def obtener_fecha_generica(soup):
    div_fecha = soup.find("div", class_="bottom lighterGrayFont arial_11")
    if div_fecha:
        texto = div_fecha.get_text(separator=" ", strip=True)
        # Buscar patrón dd/mm o dd/mm/yyyy
        match = re.search(r"\b(\d{1,2}/\d{1,2}(/\d{2,4})?)\b", texto)
        if match:
            return match.group(1)
    return "N/D"
    
def obtener_precio_fondo_investing(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        print(f"Error al obtener la página {url}: {r.status_code}")
        return None, "N/D"

    soup = BeautifulSoup(r.content, "html.parser")
    precio_span = soup.find("span", id="last_last")
    if precio_span:
        precio_texto = precio_span.text.strip()
        precio_texto = precio_texto.replace(".", "").replace(",", ".")
        try:
            precio_texto = float(precio_texto)
        except Exception as e:
            print(f"Error al convertir precio a float: {precio_texto} ({e})")
            precio_texto =  None
    else:
        print(f"No se encontró el elemento precio en {url}")
        precio_texto = None
        
    # Fecha
    fecha_texto = obtener_fecha_generica(soup)
    print(fecha_texto)

    return precio_texto, fecha_texto

def obtener_datos_accion(ticker):
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="2d")
        if len(hist) < 2:
            return None, None
        ayer = hist["Close"].iloc[-2]
        hoy = hist["Close"].iloc[-1]
        variacion = ((hoy - ayer) / ayer) * 100
        return hoy, variacion
    except Exception as e:
        print("Error yfinance:", e)
        return None, None

def calcular_variacion(ant, actual):
    try:
        variacion = ((actual - ant) / ant) * 100
        return f"{variacion:+.2f}%"
    except Exception:
        return "N/D"

def generar_mensaje(valores_anteriores, valores_actuales, fondos_seleccionados, incluir_acciones):
    mensaje = f"📈 *Actualización* — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    mensaje += "💼 Fondos:\n"
    for isin in fondos_seleccionados:
        datos = fondos[isin]
        ant = valores_anteriores.get("fondos", {}).get(isin)
        actual_tuple = valores_actuales.get("fondos", {}).get(isin)
        if actual_tuple is not None:
            actual, fecha = actual_tuple
        else:
            actual, fecha = None, "N/D"

        if ant is None:
            variacion = "N/D (sin valor previo)"
        else:
            if isinstance(ant, tuple):
                ant_precio = ant[0]
            else:
                ant_precio = ant
            variacion = calcular_variacion(ant_precio, actual) if actual is not None else "N/D"

        precio_str = f"{actual:.3f}" if actual is not None else "N/D"
        mensaje += f"• {isin} - {datos['nombre']}: {precio_str} (Fecha: {fecha}) ({variacion})\n"

    if incluir_acciones:
        mensaje += "\n📊 Acciones:\n"
        for isin, info in acciones.items():
            precio_actual, variacion = obtener_datos_accion(info["ticker"])
            if precio_actual is not None and variacion is not None:
                mensaje += f"• {isin} ({info['nombre']}): {precio_actual:.3f} ({variacion:+.2f}%)\n"
                info["valor_anterior"] = precio_actual
            else:
                mensaje += f"• {isin} ({info['nombre']}): N/D\n"

    return mensaje

def actualizar_valores_fondos(fondos_seleccionados):
    for isin in fondos_seleccionados:
        precio, fecha  = obtener_precio_fondo_investing(fondos[isin]["url"])
        if precio is not None:
            valores_actuales.setdefault("fondos", {})[isin] = (precio, fecha)
        else:
            valores_actuales.setdefault("fondos", {})[isin] = valores_anteriores.get("fondos", {}).get(isin, 0)

def tarea_16_00():
    global valores_anteriores, valores_actuales
    valores_actuales = {"fondos": {}, "acciones": {}}
    fondos_a_consultar = ["ES0175437005", "ES0175414012", "ES0140794001", "IE00BD0NCM55"]
    acciones_a_consultar = True

    actualizar_valores_fondos(fondos_a_consultar)
    mensaje = generar_mensaje(valores_anteriores, valores_actuales, fondos_a_consultar, acciones_a_consultar)
    enviar_mensaje(mensaje)

    # ✅ Copia profunda de solo los fondos consultados
    for isin in fondos_a_consultar:
        valores_anteriores["fondos"][isin] = valores_actuales["fondos"][isin]

    print("Mensaje enviado a las 16:00")

def tarea_00_15():
    global valores_anteriores, valores_actuales
    valores_actuales = {"fondos": {}, "acciones": {}}
    fondos_a_consultar = ["LU1508158430"]
    acciones_a_consultar = False

    actualizar_valores_fondos(fondos_a_consultar)
    mensaje = generar_mensaje(valores_anteriores, valores_actuales, fondos_a_consultar, acciones_a_consultar)
    enviar_mensaje(mensaje)

    # ✅ Copia profunda solo de ese fondo
    for isin in fondos_a_consultar:
        valores_anteriores["fondos"][isin] = valores_actuales["fondos"][isin]

    print("Mensaje enviado a las 00:15")


# --- Lanzar tareas manuales para prueba ---
#tarea_16_00()
#tarea_00_15()

# --- Programar ejecuciones automáticas ---
schedule.every().day.at("14:00").do(tarea_16_00)
schedule.every().day.at("22:15").do(tarea_00_15)

print("⏳ Tareas programadas para las 16:00 y 00:15")
print("📡 Scheduler iniciado. Esperando tareas...")

app = Flask('')

@app.route('/')
def home():
    return "Bot activo ✅", 200

def iniciar_servidor():
    app.run(host='0.0.0.0', port=8080)

# Inicia el servidor Flask en segundo plano
threading.Thread(target=iniciar_servidor).start()

while True:
    schedule.run_pending()
    time.sleep(5)


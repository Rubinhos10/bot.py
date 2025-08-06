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
#CHAT_ID = "225671791"
CHAT_IDS = ["225671791", "6441909"]  # Añade más IDs

# --- Fondos y sus URLs en Investing ---
fondos = {
    "ES0175414012": {
        "nombre": "Dunas Valor Equilibrado R FI",
        "url": "https://es.investing.com/funds/es0175414012",
        "url_hist": "https://www.finect.com/fondos-inversion/ES0175414012-Dunas_valor_equilibrado_r_fi"
    },
    "IE00BD0NCM55": {
        "nombre": "iShares Developed World Index Fund (IE) D Acc Eur",
        "url": "https://es.investing.com/funds/ie00bd0ncm55",
        "url_hist": "https://www.finect.com/fondos-inversion/IE00BD0NCM55-Ishares_dev_wld_idx_ie_d_acc_eur"
    },
    "ES0140794001": {
        "nombre": "Gamma Global A FI",
        "url": "https://es.investing.com/funds/es0140794001",
        "url_hist": "https://www.finect.com/fondos-inversion/ES0140794001-Gamma_global_fi"
    },
    "LU1508158430": {
        "nombre": "ASIAPF DV EQ ABS RT A2 AC EURH",
        "url": "https://es.investing.com/funds/lu1508158430",
        "url_hist": "https://www.finect.com/fondos-inversion/LU1508158430-Bsf_asia_pacific_divers_eq_ar_a2_eur_h"
    },
    "ES0175437005": {
        "nombre": "Dunas Valor Prudente R FI",
        "url": "https://es.investing.com/funds/es0175437005",
        "url_hist": "https://www.finect.com/fondos-inversion/ES0175437005-Dunas_valor_prudente_r_fi"
    }
    ,
    "FR0000989626": {
        "nombre": "Groupama Trésorerie IC",
        "url": "https://es.investing.com/funds/fr0000989626",
        "url_hist": "https://www.finect.com/fondos-inversion/FR0000989626-Groupama_tresorerie_ic"
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
        "ticker": "AMP.MC"
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
    for chat_id in CHAT_IDS:
        data = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
        r = requests.post(url, data=data)
        if r.status_code == 200:
            print(f"✅ Mensaje enviado a {chat_id}")
        else:
            print(f"❌ Error al enviar mensaje a {chat_id}: {r.text}")

def obtener_fecha_generica(soup):
    div_fecha = soup.find("div", class_="bottom lighterGrayFont arial_11")
    if div_fecha:
        texto = div_fecha.get_text(separator=" ", strip=True)
        # Buscar patrón dd/mm o dd/mm/yyyy
        match = re.search(r"\b(\d{1,2}/\d{1,2}(/\d{2,4})?)\b", texto)
        if match:
            return match.group(1)
    return "N/D"
    
def obtener_precio_fondo_investing(url, url_hist):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        print(f"Error al obtener la página {url}: {r.status_code}")
        return None, "N/D", None, None

    r2 = requests.get(url_hist, headers=headers, timeout=10)
    if r.status_code != 200:
        print(f"Error al obtener la página {url}: {r.status_code}")
        return None, "N/D", None, None

    soup = BeautifulSoup(r.content, "html.parser")
    soup2 = BeautifulSoup(r2.content, "html.parser")
    precio_span = soup.find("span", id="last_last")
    variacion_span = soup.find("span", class_=["pcp", "parentheses"])
    variacion_span_ytd = soup2.find("span", class_=["partials__Value-sc-jbvs3z-1", "eHgKAY"])    
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

    if variacion_span:
        variacion_texto = variacion_span.text.strip()
        variacion_texto = variacion_texto.replace(".", "").replace(",", ".")
        #try:
        #variacion_texto = float(variacion_texto)
#except Exception as e:
        #print(f"Error al convertir precio a float: {variacion_texto} ({e})")
        #variacion_texto =  None
    else:
        print(f"No se encontró el elemento precio en {url}")
        variacion_texto = None

    if variacion_span_ytd:
        variacion_texto_ytd = variacion_span_ytd.text.strip()
        variacion_texto_ytd = variacion_texto_ytd.replace(".", "").replace(",", ".")
    else:
        print(f"No se encontró el elemento precio en {url}")
        variacion_texto_ytd = None
        
    # Fecha
    fecha_texto = obtener_fecha_generica(soup)
    print(fecha_texto)

    return precio_texto, fecha_texto, variacion_texto, variacion_texto_ytd

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
    mensaje = f"📈 *Actualización* — {(datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')}\n\n"
    mensaje += "💼 Fondos:\n"
    for isin in fondos_seleccionados:
        datos = fondos[isin]
        ant = valores_anteriores.get("fondos", {}).get(isin)
        actual_tuple = valores_actuales.get("fondos", {}).get(isin)
        if actual_tuple is not None:
            actual, fecha, variacion_actual, variacion_ytd = actual_tuple
        else:
            actual, fecha, variacion_actual, variacion_ytd = None, "N/D", "N/D", None

        if ant is None:
            variacion = "N/D (sin valor previo)"
        else:
            if isinstance(ant, tuple):
                ant_precio = ant[0]
            else:
                ant_precio = ant
            variacion = calcular_variacion(ant_precio, actual) if actual is not None else "N/D"

        precio_str = f"{actual:.3f}" if actual is not None else "N/D"
        if variacion_actual.startswith('+'):
            simbolo = "🟢"
        elif variacion_actual.startswith('-'):
            simbolo = "🔴"
        else:
            simbolo = "⚪️"
        mensaje += f"{simbolo} {isin} - *{datos['nombre']}*: {precio_str} (Fecha: {fecha}) ({variacion}) (Diaria: {variacion_actual}) (YTD: {variacion_ytd})\n"

    if incluir_acciones:
        mensaje += "\n📊 Acciones:\n"
        for isin, info in acciones.items():
            precio_actual, variacion = obtener_datos_accion(info["ticker"])
            
            if precio_actual is not None and variacion is not None:
                variacion_actual_str = f"{variacion:+.2f}%" if isinstance(variacion, (float, int)) else str(variacion)
                print(variacion)
                if variacion_actual_str.startswith('+'):
                    simbolo = "🟢"
                elif variacion_actual_str.startswith('-'):
                    simbolo = "🔴"
                else:
                    simbolo = "⚪️"
                mensaje += f"{simbolo} {isin} ({info['nombre']}): {precio_actual:.3f} ({variacion:+.2f}%)\n"
                info["valor_anterior"] = precio_actual
            else:
                simbolo = "⚪️"
                mensaje += f"{simbolo} {isin} ({info['nombre']}): N/D\n"

    return mensaje

def actualizar_valores_fondos(fondos_seleccionados):
    for isin in fondos_seleccionados:
        precio, fecha, variacion, variacion_ytd  = obtener_precio_fondo_investing(fondos[isin]["url"], fondos[isin]["url_hist"])
        if precio is not None:
            valores_actuales.setdefault("fondos", {})[isin] = (precio, fecha, variacion, variacion_ytd)
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

# --- Función para enviar auto-ping cada 10 minutos ---
def autoping():
    while True:
        try:
            requests.get("https://bot-py-ji2i.onrender.com/")
            print("🔁 Auto-ping enviado")
        except Exception as e:
            print("❌ Error en auto-ping:", e)
        time.sleep(600)

# Lanzar servidor Flask y auto-ping en hilos separados
threading.Thread(target=iniciar_servidor).start()
threading.Thread(target=autoping).start()

# Ejecutar el scheduler
while True:
    schedule.run_pending()
    time.sleep(5)


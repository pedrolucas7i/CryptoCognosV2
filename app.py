import pandas as pd
import pandas_ta as ta
import requests
from flask import Flask, jsonify, request, render_template, redirect
import plotly.graph_objects as go

app = Flask(__name__)

price = 0.000000
volume = 0.000000
error = ""

def get_crypto_data(crypto_id, days):
    
    global price, volume, error
    
    # Fetch cryptocurrency historical data from CoinGecko API
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart?vs_currency=usd&days={days}"
    response = requests.get(url).json()
    
    if 'status' in response and response['status'].get('error_code') == 429:
        error = "Error 429: API request limit exceeded."
        print("Erro 429: Limite de requisições excedido.")
        print("Mensagem:", response['status'].get('error_message'))
        
    df = pd.DataFrame()
    #print("Raw API Response:", response)  # Debugging output to see raw API response

    if 'prices' not in response:
        print("Error: Missing 'prices' data in response.")  # Debugging output
        return df, [], []  # Returning empty lists if data is missing

    prices = response['prices']
    timestamps = [pd.to_datetime(item[0], unit='ms') for item in prices]
    price_values = [item[1] for item in prices]
    
    price = price_values[0]
    
    volumes = response['total_volumes']
    volume_values = [item[1] for item in volumes]
    
    volume = volume_values[0]

    # Create DataFrame for technical analysis
    df = pd.DataFrame({"timestamp": timestamps, "price": price_values})
    
    # Check if the DataFrame is empty
    if df.empty:
        print("Error: DataFrame is empty.")  # Debugging output
        return df, [], []

    # Calculate Technical Indicators
    df["EMA_9"] = ta.ema(df["price"], length=9)
    df["EMA_21"] = ta.ema(df["price"], length=21)
    df["RSI"] = ta.rsi(df["price"], length=14)
    df["MACD"], df["MACD_Signal"], _ = ta.macd(df["price"])

    # Calculate Bollinger Bands
    bb_values = ta.bbands(df["price"], length=20)
    print("Bollinger Bands Output:", bb_values)  # Output for inspection

    # Unpack Bollinger Bands correctly
    df["BB_Upper"] = bb_values["BBU_20_2.0"]
    df["BB_Mid"] = bb_values["BBM_20_2.0"]
    df["BB_Lower"] = bb_values["BBL_20_2.0"]

    # Calculate ADX using price as the close
    adx_values = ta.adx(df["price"], df["price"], df["price"])
    df["ADX"] = adx_values["ADX_14"]
    
    return df, timestamps, price_values


@app.route('/crypto-data', methods=['GET'])
def crypto_data():
    
    crypto_id = request.args.get('crypto', 'bitcoin')
    days = request.args.get('days', 1, type=int)

    df, timestamps, price_values = get_crypto_data(crypto_id, days)

    # Verificar se o DataFrame está vazio
    if df.empty:
        return jsonify({"error": "Failed to fetch or process cryptocurrency data"}), 500

    # Obtendo o preço e volume atuais diretamente da API
    latest_price = price_values[-1] if price_values else 0.0
    latest_volume = df["price"].iloc[-1] if not df.empty else 0.0

    # Retrieve latest indicator values
    try:
        last_rsi = df["RSI"].iloc[-1]
        last_macd = df["MACD"].iloc[-1]
        last_macd_signal = df["MACD_Signal"].iloc[-1]
        last_ema_9 = df["EMA_9"].iloc[-1]
        last_ema_21 = df["EMA_21"].iloc[-1]
        last_bb_upper = df["BB_Upper"].iloc[-1]
        last_bb_lower = df["BB_Lower"].iloc[-1]
        last_price = latest_price
        last_adx = df["ADX"].iloc[-1]
    except IndexError:
        return jsonify({"error": "Insufficient data for analysis"}), 500

    # 🔥 Cálculo do score de recomendação
    score = 0

    # 🔵 EMA → Se EMA 9 > EMA 21 (tendência de alta) → COMPRAR
    ema_signal = 1 if last_ema_9 > last_ema_21 else -1
    score += ema_signal * 0.3

    # 🟢 RSI → Se RSI < 30 (sobrevendido) → COMPRAR | Se RSI > 70 → VENDER
    if last_rsi < 30:
        rsi_signal = 1
    elif last_rsi > 70:
        rsi_signal = -1
    else:
        rsi_signal = 0
    score += rsi_signal * 0.2

    # 🔴 MACD → Se MACD > MACD Signal (momentum positivo) → COMPRAR
    macd_signal = 1 if last_macd > last_macd_signal else -1
    score += macd_signal * 0.2

    # 🟡 Bollinger Bands → Se o preço tocar a banda inferior → COMPRAR | Superior → VENDER
    if last_price < last_bb_lower:
        bb_signal = 1
    elif last_price > last_bb_upper:
        bb_signal = -1
    else:
        bb_signal = 0
    score += bb_signal * 0.15

    # 🟣 ADX → Se ADX > 25, tendência forte, se < 20, reduz impacto
    adx_weight = 1 if last_adx > 25 else 0.5 if last_adx > 20 else 0.2
    score *= adx_weight  # ADX reduz impacto se tendência fraca

    score *= 10

    # 📌 Define Recomendação
    if score > 0.5:
        indication = "BUY 🚀"
        certainty = f"{round(score * 100, 1)}% Certainty"
    elif score < -0.5:
        indication = "SELL 📉"
        certainty = f"{round(abs(score) * 100, 1)}% Certainty"
    else:
        indication = "HOLD 🏁"
        certainty = f"{round((1 - abs(score)) * 100, 1)}% Certainty"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=price_values,
        mode='lines',
        name=crypto_id.capitalize(),
        line=dict(color='#ff0000' if indication == "SELL 📉" else ('#008000' if indication == "BUY 🚀" else '#3498db'), width=1.5),
        text=[f"{val:.2f}" for val in price_values],
        textposition="top center"
    ))
    fig.update_layout(
        title=f"{crypto_id.capitalize()} Price Over the Last {days} Days",
        template="plotly_dark",
        plot_bgcolor="black",
        paper_bgcolor="black",
    )

    graphJSON = fig.to_json()
    return jsonify({
        "graph": graphJSON,
        "indication": indication,
        "certainty": certainty,
        "price": latest_price,
        "volume": latest_volume
    })


@app.route('/')
def index():
    global price, volume, error
    return render_template('index.html', price=price, volume=volume, error=error)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=80)

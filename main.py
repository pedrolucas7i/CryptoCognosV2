import pandas as pd
import pandas_ta as ta
import requests
from flask import Flask, jsonify, request, render_template
import plotly.graph_objects as go

app = Flask(__name__)

def get_crypto_data(crypto_id, days):
    # Fetch cryptocurrency historical data from CoinGecko API
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart?vs_currency=usd&days={days}"
    response = requests.get(url).json()

    #print("Raw API Response:", response)  # Debugging output to see raw API response

    if 'prices' not in response:
        print("Error: Missing 'prices' data in response.")  # Debugging output
        return [], [], []  # Returning empty lists if data is missing

    prices = response['prices']
    timestamps = [pd.to_datetime(item[0], unit='ms') for item in prices]
    price_values = [item[1] for item in prices]

    # Create DataFrame for technical analysis
    df = pd.DataFrame({"timestamp": timestamps, "price": price_values})
    
    # Check if the DataFrame is empty
    if df.empty:
        print("Error: DataFrame is empty.")  # Debugging output
        return [], [], []

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
    days = request.args.get('days', 7, type=int)

    df, timestamps, price_values = get_crypto_data(crypto_id, days)

    # Verificar se o DataFrame está vazio
    if df.empty:
        return jsonify({"error": "Failed to fetch or process cryptocurrency data"}), 500

    # Retrieve latest indicator values
    try:
        last_rsi = df["RSI"].iloc[-1]
        last_macd = df["MACD"].iloc[-1]
        last_macd_signal = df["MACD_Signal"].iloc[-1]
        last_ema_9 = df["EMA_9"].iloc[-1]
        last_ema_21 = df["EMA_21"].iloc[-1]
        last_bb_upper = df["BB_Upper"].iloc[-1]
        last_bb_lower = df["BB_Lower"].iloc[-1]
        last_price = price_values[-1]
        last_adx = df["ADX"].iloc[-1]
    except IndexError:
        return jsonify({"error": "Insufficient data for analysis"}), 500

    # 🔥 Weighted Score Calculation (-1 to +1)
    score = 0

    # 🔵 EMA → If EMA 9 > EMA 21 (short-term uptrend) → BUY
    ema_signal = 1 if last_ema_9 > last_ema_21 else -1
    score += ema_signal * 0.3

    # 🟢 RSI → If RSI < 30 (oversold) → BUY | If RSI > 70 → SELL
    if last_rsi < 30:
        rsi_signal = 1
    elif last_rsi > 70:
        rsi_signal = -1
    else:
        rsi_signal = 0
    score += rsi_signal * 0.2

    # 🔴 MACD → If MACD > MACD Signal (bullish momentum) → BUY
    macd_signal = 1 if last_macd > last_macd_signal else -1
    score += macd_signal * 0.2

    # 🟡 Bollinger Bands → If price touches lower band → BUY | Upper band → SELL
    if last_price < last_bb_lower:
        bb_signal = 1
    elif last_price > last_bb_upper:
        bb_signal = -1
    else:
        bb_signal = 0
    score += bb_signal * 0.15

    # 🟣 ADX → If ADX > 25, strong trend, if < 20, reduce certainty
    adx_weight = 1 if last_adx > 25 else 0.5 if last_adx > 20 else 0.2
    score *= adx_weight  # ADX reduces impact if weak trend

    # 📌 Define Recommendation
    if score > 0.5:
        indication = "BUY 🚀"
        certainty = f"{round(score * 100, 1)}% Certainty"
    elif score < -0.5:
        indication = "SELL 📉"
        certainty = f"{round(abs(score) * 100, 1)}% Certainty"
    else:
        indication = "HOLD 🏁"
        certainty = f"{round((1 - abs(score)) * 100, 1)}% Certainty"

    # Create price chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=price_values, mode='lines', name=crypto_id.capitalize(), line=dict(color='#3498db', width=3)))
    fig.update_layout(
        title=f"{crypto_id.capitalize()} Price Over the Last {days} Days",
        template="plotly_dark",
        plot_bgcolor="black",
        paper_bgcolor="black"
    )

    graphJSON = fig.to_json()

    return jsonify({"graph": graphJSON, "indication": indication, "certainty": certainty})


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)

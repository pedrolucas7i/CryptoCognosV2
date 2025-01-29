from flask import Flask, render_template, jsonify, request
import requests
import pandas as pd
import plotly.graph_objects as go

app = Flask(__name__)

def get_crypto_data(crypto_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart?vs_currency=usd&days={days}"
    response = requests.get(url)
    
    try:
        data = response.json()
        print("API Response:", data)  # 👀 Depuração
        if 'prices' not in data:
            return [], []
        
        prices = data['prices']
        timestamps = [pd.to_datetime(item[0], unit='ms') for item in prices]
        price_values = [item[1] for item in prices]
        return timestamps, price_values
    except Exception as e:
        print(f"Erro ao processar a resposta da API: {e}")
        return [], []


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/crypto-data', methods=['GET'])
def crypto_data():
    crypto_id = request.args.get('crypto', 'bitcoin')
    days = request.args.get('days', 7, type=int)
    timestamps, price_values = get_crypto_data(crypto_id, days)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=price_values, mode='lines', name=crypto_id.capitalize(), line=dict(color='#3498db', width=3)))
    fig.update_layout(
        title=f"Preço do {crypto_id.capitalize()} nos últimos {days} dias",
        template="plotly_dark",
        plot_bgcolor="#34495e",
        paper_bgcolor="#2c3e50"
    )
    
    graphJSON = fig.to_json()
    return jsonify(graphJSON)

if __name__ == '__main__':
    app.run(debug=True)
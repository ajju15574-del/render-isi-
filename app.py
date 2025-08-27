from flask import Flask
import requests
import numpy as np
import time
from datetime import datetime
import threading

app = Flask(__name__)

# टेलीग्राम बॉट सेटअप
BOT_TOKEN = '8261503686:AAFuN0H57q6pn_OgtLjiNWZPnNgNBe6xIiY'
CHAT_ID = '1141123914'

# Telegram message भेजने का function
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, data=data)
        print(f"Message sent: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

# सही RSI calculation function
def calculate_rsi(prices, period=14):
    if len(prices) <= period:
        return 50  # पर्याप्त डेटा नहीं है
    
    deltas = np.diff(prices)
    gains = np.zeros_like(deltas)
    losses = np.zeros_like(deltas)
    
    gains[deltas > 0] = deltas[deltas > 0]
    losses[deltas < 0] = -deltas[deltas < 0]
    
    # पहले period के लिए औसत gain और loss
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    # बाकी periods के लिए
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100  # कोई loss नहीं है
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Binance API से data लाने का function
def get_binance_data(symbol, interval, limit=100):
    url = f'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if isinstance(data, dict) and 'code' in data:
            print(f"API Error: {data}")
            return None
        closes = [float(c[4]) for c in data]  # Closing prices
        return closes
    except Exception as e:
        print(f"Error fetching data for {symbol} {interval}: {e}")
        return None

# RSI monitoring function
def monitor_rsi():
    symbols = ['BTCUSDT', 'ETHUSDT']
    intervals = ['15m', '1h', '4h']
    
    # Startup message
    send_telegram_message("🤖 Bot started on Render! Monitoring BTCUSDT and ETHUSDT.")
    
    last_message_time = {}
    
    while True:
        try:
            current_time = time.time()
            current_datetime = datetime.now()
            
            # Good Morning message (8 AM)
            if current_datetime.hour == 8 and current_datetime.minute < 5:
                send_telegram_message("🌅 Good Morning Ajay Sir! Bot is running smoothly.")
                time.sleep(300)  # 5 minutes wait
            
            # Good Night message (10 PM)
            if current_datetime.hour == 22 and current_datetime.minute < 5:
                send_telegram_message("🌙 Good Night Ajay Sir! Bot will continue monitoring.")
                time.sleep(300)  # 5 minutes wait
            
            # RSI monitoring
            for symbol in symbols:
                for interval in intervals:
                    closes = get_binance_data(symbol, interval, 50)
                    if closes is None or len(closes) <= 14:
                        print(f"{symbol} ({interval}): Not enough data")
                        continue
                    
                    rsi_value = calculate_rsi(closes)
                    print(f"{symbol} ({interval}) RSI: {rsi_value:.2f}")
                    
                    # RSI 70 से अधिक होने पर अलर्ट भेजें
                    if rsi_value >= 70:
                        key = f"{symbol}_{interval}"
                        
                        # अंतिम message के बाद कम से कम 1 hour का interval
                        if key in last_message_time:
                            time_diff = current_time - last_message_time[key]
                            if time_diff < 3600:  # 1 hour
                                continue
                        
                        message = f"""
🚨 RSI Alert for {symbol}
📊 Timeframe: {interval}
📈 RSI Value: {rsi_value:.2f}
💰 Last Price: {closes[-1]}
                        """
                        send_telegram_message(message)
                        last_message_time[key] = current_time
                        time.sleep(1)  # Rate limit के लिए
            
            time.sleep(900)  # 15 minutes wait
            
        except Exception as e:
            print(f"Error in monitoring: {e}")
            time.sleep(60)

# Flask route for uptimerobot
@app.route('/')
def home():
    return "🤖 RSI Bot is running!"

# Health check route for uptimerobot
@app.route('/health')
def health():
    return "✅ Bot is healthy!"

# Start monitoring in a separate thread
@app.before_first_request
def start_monitoring():
    monitor_thread = threading.Thread(target=monitor_rsi)
    monitor_thread.daemon = True
    monitor_thread.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
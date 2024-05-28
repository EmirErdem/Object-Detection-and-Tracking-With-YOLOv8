from flask import Flask,request
from flask_socketio import SocketIO


app = Flask(__name__)      # Flask uygulamasını oluşturur.
socketio = SocketIO(app)   # Socket.IO örneğini Flask uygulamasına bağlar.

@socketio.on('connect')    # Socket.IO üzerinden gelen 'connect' olayını dinler. Bir istemci sunucuya bağlandığında bu fonksiyon çalışır.
def handleconnect():
    print('Client connected')

@socketio.on('message')    # Socket.IO üzerinden gelen 'message' olayını dinler. Bir istemciden bir mesaj alındığında bu fonksiyon çalışır.
def handlemessage(message):
    print('Received message:', message)
    


if __name__ == '__main__':
    socketio.run(app,debug=False,host="192.168.1.12",port=3000) # Uygulamayı çalıştırır.192.168.1.12 IP adresine ve 3000 portuna bağlanır.

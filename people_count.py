import cv2
import time
import numpy as np
import os
from ultralytics import YOLO
import sqlite3
import socketio
import json




sio = socketio.Client() # socketio modülünden bir istemci oluşturur. Bu, sunucuya bağlanmak ve olayları dinlemek için kullanılacak Socket.IO istemcisidir.
@sio.event # Bu, bir olay işleyiciyi (connect olayı için) belirtir. @ dekoratörü connect olayının işleyicisi olarak aşağıdaki fonksiyonu belirtir.
def connect():
    print('Connected to server')  # bu benim etkinlik durumum bağlantı gerçekleşiyor mu gerçekleşmiyor mu kontrol ediyoruz.
sio.connect('http://192.168.1.12:3000') # Belirtilen sunucuya bağlanmak için Socket.IO istemcisini kullanır.
                                        # Bağlantı sağlandığında, connect olayı tetiklenecek ve connect olayını işleyen fonksiyon çağrılacaktır.


model = YOLO("yolov8l.pt")
font = cv2.FONT_HERSHEY_DUPLEX
kamera = cv2.VideoCapture("input.mp4")
w, h, fps = (int(kamera.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))
result = cv2.VideoWriter("output.avi",
                       cv2.VideoWriter_fourcc(*'mp4v'),
                       fps,
                       (w, h))

conn = sqlite3.connect('YOLO.db', check_same_thread=False)
c = conn.cursor() #Veritabanı üzerinde işlem yapmak için bir imleç oluşturur. Veritabanında sorguları çalıştırmak ve sonuçlarını almak için kullanılır.
c.execute('''CREATE TABLE IF NOT EXISTS name (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                object_name TEXT NOT NULL,
                                dir_path TEXT NOT NULL,
                                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                )''')
conn.commit() # çağrısı, SQLite veritabanındaki tüm yapılan değişikliklerin kalıcı olarak uygulanmasını sağlar

region=np.array([(675,450),(1250,450),(1250,800),(675,800)]) # Dikdörtgen oluşturduk
region = region.reshape((-1,1,2))

output_image_path_person='./ss/person'
output_image_path_handbag='./ss/handbag'

person=set()
handbag=set()
previous_handbag=set()
previous_person=set()
flag_handbag=False
flag_person=False

while True:

    ret, frame = kamera.read()
    if not ret:
        break
        
    results = model.track(frame, persist=True, verbose=False) # Bir modelin bir kare üzerinde nesne izleme yapmasını sağlar
    labels=results[0].names # nesnelerin isimleri
    cv2.polylines(frame,[region],True,(0,0,255),4) # frame üzerine koordinatları verilen dikdörtgenin çizimi  yapılır
   
    for i in range(len(results[0].boxes)): # tespit edilen nesne sayısı  kadar döngüye girer 

        x1,y1,x2,y2=results[0].boxes.xyxy[i] # Nesnelerin koordinatları
        score=results[0].boxes.conf[i] # Nesnelerin olasılıkları
        cls=results[0].boxes.cls[i] # Nesnelerin sınıfları 
        ids=results[0].boxes.id[i] # Nesnelerin idleri


        
        x1,y1,x2,y2,score,cls,ids=int(x1),int(y1),int(x2),int(y2),float(score),int(cls),int(ids) # veri tipi dönüşümü yapıldı 

        if score<0.50: # olasılık skoru %50 altında ise sonraki adıma atlar.
            continue      
              
        if cls == 0:
            cx=int(x1/2+x2/2)
            cy=int(y1/2+y2/2)
            cv2.circle(frame,(cx,cy),10,(255,0,0),-1) # Nesnelerin orta noktasına daire koyar
            inside_region=cv2.pointPolygonTest(region,(cx,cy),False) # Daire belirttiğimiz dikdörtgein içinde mi değil mi onu kontrol eder
            if inside_region>0: # inside_region değeri 0 dan büyükse içinde demektir
                if not ids in  previous_person:
                    name=results[0].names[cls]
                    person.add(ids)
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    image_name = f"person_{timestamp}.jpg"
                    image_path = os.path.join(output_image_path_person, image_name) 

                    # Veritabanında tablo oluşturulur
                    c.execute("INSERT INTO name(object_name, dir_path) VALUES (?, ?)", (name, image_path))
                    conn.commit()

                    flag_person=True
                previous_person.add(ids)

                
        if cls == 26:
            cx=int(x1/2+x2/2)
            cy=int(y1/2+y2/2)
            cv2.circle(frame,(cx,cy),10,(0,0,255),-1)
            inside_region=cv2.pointPolygonTest(region,(cx,cy),False)  
            
            if inside_region>0:
                if not ids in   previous_handbag:
                    name=results[0].names[cls]
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    image_name = f"handbag_{timestamp}.jpg"
                    image_path = os.path.join(output_image_path_handbag, image_name) 
                    handbag.add(ids)
                    

                    data={'object_name':name,'dir_path':image_path} 
                    data_str=json.dumps(data) # data sözlüğünü JSON formatında bir dizeye dönüştürür. 
                    sio.emit('message',data_str) # Socket.IO istemcisinden message olayını yayınlar ve JSON formatındaki veri dizesini bu olayla birlikte gönderir

                    flag_handbag=True
                previous_handbag.add(ids)
                       
        person_str='Person: '+str(len(person))
        handbag_str='Handbag: '+str(len(handbag))
        
        frame[0:60,0:270]=(255,255,255)
        cv2.putText(frame,person_str,(0, 40), font, 1.5, (128,0,0), 2,)

        frame[60:120,0:270]=(255,255,255)
        cv2.putText(frame,handbag_str,(0, 80), font, 1.3, (0,0,128), 2,)

        if flag_person:
            cv2.imwrite(image_path, frame)
            flag_person=False
        if flag_handbag:
            cv2.imwrite(image_path, frame)
            flag_handbag=False

    result.write(frame) #  Bu yöntem, belirtilen çerçeveyi (frame) mevcut video dosyasına yazar
    #cv2.imshow("frame", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"): # q tuşuna basılırsa video kapanır
        break


#conn = sqlite3.connect('YOLO.db')
#cursor = conn.cursor()
## Bir tablonun içeriğini görüntüle
#cursor.execute("SELECT * FROM name;")
#print(cursor.fetchall())
#conn.close()

result.release() # Belirtilen video dosyası yazıcısını serbest bırakır.Video dosyasının kaydetme işleminin sona erdiğini ve dosyanın kapatılması gerektiğini belirtir.
kamera.release() # Kameranın kullanımının sona erdiğini ve kaynakların kapatılması gerektiğini belirtir.
cv2.destroyAllWindows() # Ekranda açık olan tüm pencerelerin kapatılmasını sağlar


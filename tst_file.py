import smtplib

server = smtplib.SMTP('localhost', 25)  # Подключаетесь к локальному smtp-серверу
server.sendmail(
    'from@email.com',  # Email отправителя
    ['to@email.com'],  # Email получателя
    "Welcome to Practix!"  # Текст сообщения. Это должна быть строка с символами в диапазоне ASCII или байтовая строка.
)
server.close()  # Закрываете соединение с smtp-сервером
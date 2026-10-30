# Предварительная подгатовка

ssh orangepi@ip -p 2222
psword: orangepi
```
nano sverk-ros2/.env
```

Переменная 	По умолчанию 	Что задаёт
ENABLE_SWARM 	0 	Поднимать ли ноду роя при старте системы
SWARM_ID 	1 в готовом swarm-образе 	Номер дрона в рое, от 1 до 255
SWARM_NETWORK_ID 	42 	Номер сети: разделяет соседние рои
SWARM_CHANNEL 	6 	Радиоканал 2,4 ГГц, от 1 до 13, нумерация как у Wi-Fi
SWARM_UART_PORT 	не задан 	Порт модуля, если автопоиск не подходит. Порт полётного контроллера указывать нельзя


# Проверка обмена сообщениями между дронами через ESP-NOW

Инструкция проверяет цепочку:

```text
ROS 2 на дроне 1 → UART → ESP32-C3 → ESP-NOW → ESP32-C3 → UART → ROS 2 на дроне 3
```

Команды выполняются **внутри контейнера `sverk_ros2`** на соответствующем дроне. В примерах используются:

- дрон 1: `SWARM_ID=1`;
- дрон 2: `SWARM_ID=2`.

На обоих бортах должны совпадать `SWARM_NETWORK_ID` и `SWARM_CHANNEL`, а `handshake_ok` должен быть `true`.


## 1. Проверить локальную связь ROS 2 с ESP

На каждом дроне выполните:

```bash
ros2 topic echo --once /swarm/status
```

Ожидаемый результат содержит:

```text
handshake_ok: true
state: CONNECTED
last_error: ''
```

Также проверьте:

```text
uart_port: /dev/ttyS7
```

для Orange Pi Zero 3W.

Значения `drone_id` должны быть разными:

- на первом борту — `drone_id: 1`;
- на третьем борту — `drone_id: 3`.

Если `handshake_ok: false`, сначала исправьте подключение ESP по UART. Между дронами сообщения в этом состоянии не пройдут.

Поля `frames_rx` и `frames_tx` — счётчики кадров UART. Они проверяют проводную связь ROS ↔ ESP, но не заменяют проверку радиообмена между дронами.

## 3. Читать входящие сообщения

На дроне-получателе оставьте открытым отдельный терминал:

```bash
ros2 topic echo /swarm/rx
```

Эта команда будет выводить все принятые пользовательские сообщения, пока её не остановить через `Ctrl+C`.

Ожидаемые поля сообщения:

```text
source_id: 1
target_id: 3
payload: hello from drone 1
```

## 4. Адресная отправка: дрон 1 → дрон 2

Сначала на дроне 2 запустите чтение:

```bash
ros2 topic echo /swarm/rx
```

Затем на дроне 1 выполните:

```bash
ros2 service call /swarm/send swarm_interfaces/srv/SendMessage \
  "{target_id: 2, payload: 'hello from drone 1', timeout: 1.0, retries: 3}"
```

Успешный ответ на дроне 1:

```text
accepted=True
delivered=True
attempts=1
error=''
```

Значения означают:

- `accepted=True` — локальная нода приняла сообщение к отправке;
- `delivered=True` — от дрона 3 пришёл ACK;
- `attempts` — количество попыток отправки;
- `error=''` — ошибка отсутствует.

На дроне 3 в `/swarm/rx` должно появиться сообщение от источника `1`.


## 7. Широковещательная отправка всем дронам

Широковещательное сообщение отправляется через `/swarm/tx`:

```bash
ros2 topic pub --once /swarm/tx swarm_interfaces/msg/SwarmMessage \
  "{payload: 'broadcast test'}"
```

На каждом другом дроне читать:

```bash
ros2 topic echo /swarm/rx
```

В широковещательном режиме нет адресата и нет ответа `delivered=True`. Для подтверждённой доставки используйте сервис `/swarm/send`.

## 9. Проверить список соседей

На каждом дроне:

```bash
ros2 topic echo /swarm/peers --qos-reliability best_effort
```

У `/swarm/peers` используется QoS `BEST_EFFORT`, поэтому этот флаг нужен для корректного приёма сообщений.

Также можно запросить список один раз:

```bash
ros2 service call /swarm/get_peers swarm_interfaces/srv/GetPeers "{}"
```

На дроне 1 должен появиться сосед с `drone_id: 3`, а на дроне 3 — сосед с `drone_id: 1`.

Важно: список `/swarm/peers` заполняется телеметрией. Для появления соседа нужны:

- работающая локализация;
- топик `/offboard_control/telemetry`;
- `frame_id: aruco_map`;
- `connected: true`;
- общая система координат у дронов.

Обычная отправка сообщений через `/swarm/send` сама по себе не добавляет дрон в `/swarm/peers`.

## 10. Проверить телеметрию

```bash
ros2 topic echo --once /offboard_control/telemetry
```

Проверить частоту публикации:

```bash
ros2 topic hz /offboard_control/telemetry
```

Для передачи положения в рой желательно увидеть:

```text
frame_id: aruco_map
connected: true
```


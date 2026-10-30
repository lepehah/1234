#!/usr/bin/env python3
"""
Универсальный модуль интеграции с Web UI (Сверх.Рой) — v2.
Матрица 5x5 содержит только:
  1  — полет разрешен (можно летать)
 -1  — запретная зона (No-Fly Zone)
Без деления матрицы на зоны дронов в интерфейсе.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import cv2
import base64


class UIConnector:
    """
    Подключается к уже существующей ROS 2 ноде коллеги (передается self ноды),
    чтобы отправлять телеметрию и события зрения на сайт в 1 строчку.
    """
    def __init__(self, node: Node, on_start_callback=None, on_kill_callback=None):
        self.node = node
        self.on_start_callback = on_start_callback
        self.on_kill_callback = on_kill_callback

        self.telemetry_pub = self.node.create_publisher(String, '/ui/telemetry', 10)
        self.vision_pub = self.node.create_publisher(String, '/ui/vision_log', 10)
        self.cmd_sub = self.node.create_subscription(
            String, '/ui/command', self._command_callback, 10
        )

    def _command_callback(self, msg: String):
        try:
            data = json.loads(msg.data)
            action = data.get('action')
            if action == 'start' and self.on_start_callback:
                # Карта 5x5 (1 — летать, -1 — деление) и стартовые клетки дронов
                matrix = data.get('matrix')
                drone1 = data.get('drone1')
                drone2 = data.get('drone2')
                try:
                    self.on_start_callback(matrix, drone1, drone2)
                except TypeError:
                    self.on_start_callback(matrix)
            elif action == 'kill' and self.on_kill_callback:
                self.on_kill_callback()
        except Exception as e:
            self.node.get_logger().error(f'Ошибка чтения команды UI: {e}')

    def send_aruco_and_battery(self, drone_id: int, x: int, y: int, battery: float = None):
        """ВЫЗОВ ДЛЯ СКРИПТА ПОЛЁТА ПО ARUCO: обновляет позицию дрона (x, y) и заряд на сайте."""
        payload = {'drone_id': int(drone_id), 'x': int(x), 'y': int(y)}
        if battery is not None:
            payload['battery'] = round(float(battery), 2)
        msg = String()
        msg.data = json.dumps(payload)
        self.telemetry_pub.publish(msg)

    def send_color_detection(self, drone_id: int, x: int, y: int, z: float,
                             color: str, confidence: float = 0.95,
                             message: str = "Найден квадрат", cv_image=None):
        """
        ВЫЗОВ ДЛЯ СКРИПТА OPENCV: отправляет найденный цветной квадрат и снимок на сайт.
        color: 'red', 'yellow', 'blue' (или 'green' в симуляторе — сайт сам зачтет его).
        """
        img_b64 = None
        if cv_image is not None:
            resized = cv2.resize(cv_image, (120, 120))
            _, buffer = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            img_b64 = base64.b64encode(buffer).decode('utf-8')

        payload = {
            'drone_id': int(drone_id),
            'x': int(x),
            'y': int(y),
            'z': round(float(z), 2),
            'color': color,
            'confidence': round(float(confidence), 2),
            'message': message,
            'image_b64': img_b64
        }
        msg = String()
        msg.data = json.dumps(payload)
        self.vision_pub.publish(msg)



class SwarmUIBridge(Node):
    def __init__(self):
        super().__init__('swarm_ui_bridge')
        self.ui = UIConnector(
            self,
            on_start_callback=self.handle_start,
            on_kill_callback=self.handle_kill
        )
        self.get_logger().info('Swarm UI Bridge v2 готов. Ожидание Web UI...')

    def handle_start(self, matrix, drone1=None, drone2=None):
        self.get_logger().info(
            f'Старт миссии! Карта (1 / -1): {matrix}; drone1={drone1} drone2={drone2}'
        )
        # [ВСТАВИТЬ ВЫЗОВ ЗАПУСКА МИССИИ ЗДЕСЬ]
        # from plan_paths import plan_mission
        # plan = plan_mission(matrix, drone1 or [0, 0], drone2 or [4, 0])

    def handle_kill(self):
        self.get_logger().warn('АВАРИЙНЫЙ СТОП!')
        # [ВСТАВИТЬ ВЫЗОВ ЭКСТРЕННОЙ ПОСАДКИ ОБОИХ ДРОНОВ ЗДЕСЬ]


def main(args=None):
    rclpy.init(args=args)
    node = SwarmUIBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

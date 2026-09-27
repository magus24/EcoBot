import os
import time
import math
import cv2
from ultralytics import YOLO

# ─── Настройки ────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(os.path.dirname(BASE_DIR), "models")

# Путь к модели можно переопределить переменной окружения ECOBOT_YOLO_MODEL.
# Если файла нет — ultralytics сам скачает yolov8n.pt (COCO, 80 классов).
_DEFAULT_MODEL = os.path.join(MODELS_DIR, "yolov8n.pt")
MODEL_PATH = os.environ.get("ECOBOT_YOLO_MODEL") or (
    _DEFAULT_MODEL if os.path.exists(_DEFAULT_MODEL) else "yolov8n.pt"
)
CAPTURE_WIDTH = 640                  # Ширина кадра (уменьшено для скорости)
CAPTURE_HEIGHT = 480                 # Высота кадра
CONFIDENCE_THRESHOLD = 0.40          # Минимальная уверенность детекции
TARGET_FPS = 20                      # Ограничение FPS (15–30 для стабильности)

# Классы COCO, которые считаем «мусором».
# COCO-индексы: bottle=39, cup=41.
# "can" отсутствует как отдельный класс в COCO, но bottle покрывает банки.
TRASH_CLASSES = {"bottle", "cup"}

# Визуальные параметры
BOX_COLOR = (0, 255, 0)             # Зелёный bounding box
NEAREST_COLOR = (255, 255, 0)       # Голубой (BGR) — ближайший объект-цель
CENTER_COLOR = (0, 0, 255)          # Красная точка центра
TEXT_COLOR = (255, 255, 255)        # Белый текст
LABEL_BG_COLOR = (0, 0, 0)          # Черный фон для текста (для контраста)
BOX_THICKNESS = 2
CENTER_RADIUS = 5
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.55
FONT_THICKNESS = 1

# Максимальное количество подряд неудачных чтений кадра, прежде чем выйти
MAX_CONSECUTIVE_FAILURES = 30


def open_camera():
    """
    Пытается открыть камеру, перебирая различные бэкенды и индексы.
    На Windows MSMF часто даёт ошибки — DirectShow (DSHOW) работает надёжнее.
    Возвращает объект VideoCapture или None.
    """
    # Список бэкендов для попытки (DirectShow первым, т.к. MSMF глючит)
    backends = [
        ("DirectShow (DSHOW)", cv2.CAP_DSHOW),
        ("MSMF", cv2.CAP_MSMF),
        ("Default", cv2.CAP_ANY),
    ]
    camera_indices = [0, 1]

    for cam_idx in camera_indices:
        for backend_name, backend_id in backends:
            print(f"[INFO] Попытка открыть камеру {cam_idx} через {backend_name}…")
            cap = cv2.VideoCapture(cam_idx, backend_id)

            if not cap.isOpened():
                print(f"[WARN] Камера {cam_idx} ({backend_name}) — не удалось открыть.")
                cap.release()
                continue

            # Установка разрешения
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)

            # Прогрев камеры — первые кадры часто пустые
            print(f"[INFO] Прогрев камеры {cam_idx} ({backend_name})…")
            warmup_ok = False
            for _ in range(15):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    warmup_ok = True
                    break
                time.sleep(0.1)

            if warmup_ok:
                print(f"[OK] Камера {cam_idx} ({backend_name}) готова!")
                return cap
            else:
                print(f"[WARN] Камера {cam_idx} ({backend_name}) — не отдаёт кадры.")
                cap.release()

    return None


# ─── Функция-заглушка для робот-руки (Arduino / servo) ────────────────────────

def send_to_robot(cx: int, cy: int) -> None:
    """
    Отправляет координаты центра ближайшего мусорного объекта роботу.

    TODO: Заменить заглушку на реальную отправку через Serial (pyserial):
        import serial
        ser = serial.Serial('COM3', 9600)
        ser.write(f"{cx},{cy}\n".encode())

    Args:
        cx: X-координата центра объекта (пиксели).
        cy: Y-координата центра объекта (пиксели).
    """
    print(f"[ROBOT] >> send_to_robot(cx={cx}, cy={cy})")


def find_nearest_to_center(trash_objects: list, frame_w: int, frame_h: int) -> int:
    """
    Находит индекс объекта, ближайшего к центру кадра.

    Args:
        trash_objects: список словарей с ключами 'cx', 'cy', ...
        frame_w: ширина кадра.
        frame_h: высота кадра.

    Returns:
        Индекс ближайшего объекта или -1, если список пуст.
    """
    if not trash_objects:
        return -1

    # Центр кадра
    center_x = frame_w // 2
    center_y = frame_h // 2

    best_idx = 0
    best_dist = float("inf")

    for i, obj in enumerate(trash_objects):
        dist = math.hypot(obj["cx"] - center_x, obj["cy"] - center_y)
        if dist < best_dist:
            best_dist = dist
            best_idx = i

    return best_idx


def main() -> None:
    """Основной цикл приложения."""

    # ── Загрузка модели ───────────────────────────────────────────────────
    print("[INFO] Загрузка модели YOLOv8…")
    model = YOLO(MODEL_PATH)
    print("[INFO] Модель загружена.")

    # ── Инициализация камеры ──────────────────────────────────────────────
    cap = open_camera()

    if cap is None:
        print("=" * 60)
        print("[ERROR] Не удалось открыть веб-камеру ни одним способом.")
        print()
        print("Возможные причины:")
        print("  1. Камера используется другим приложением (Zoom, Teams и т.д.)")
        print("  2. Камера отключена в Диспетчере устройств")
        print("  3. Нет физической камеры")
        print("  4. Антивирус блокирует доступ к камере")
        print()
        print("Решения:")
        print("  - Закройте все приложения, использующие камеру")
        print("  - Проверьте камеру: Пуск → Камера")
        print("  - Проверьте Диспетчер устройств → Камеры")
        print("=" * 60)
        return

    print("[INFO] Нажмите ESC для выхода.")

    fail_count = 0          # Счётчик подряд неудачных кадров
    frame_interval = 1.0 / TARGET_FPS  # Минимальное время между кадрами
    prev_time = 0.0         # Время предыдущего обработанного кадра

    # ── Главный цикл ─────────────────────────────────────────────────────
    while True:

        # ── Ограничение FPS ───────────────────────────────────────────
        now = time.time()
        elapsed = now - prev_time
        if elapsed < frame_interval:
            # Ждём остаток интервала, чтобы не грузить CPU/GPU
            time.sleep(frame_interval - elapsed)
        prev_time = time.time()

        ret, frame = cap.read()
        if not ret or frame is None or frame.size == 0:
            fail_count += 1
            if fail_count >= MAX_CONSECUTIVE_FAILURES:
                print(f"[ERROR] {fail_count} неудачных кадров подряд. Завершаю.")
                break
            time.sleep(0.03)
            continue

        fail_count = 0
        frame_h, frame_w = frame.shape[:2]

        # ── Инференс ──────────────────────────────────────────────────
        results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]

        # ── Сбор всех мусорных объектов ───────────────────────────────
        trash_objects = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]

            if cls_name not in TRASH_CLASSES:
                continue

            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            trash_objects.append({
                "cls_name": cls_name, "conf": conf,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "cx": cx, "cy": cy,
            })

        # ── Выбор ближайшего к центру кадра ───────────────────────────
        nearest_idx = find_nearest_to_center(trash_objects, frame_w, frame_h)

        # ── Отрисовка + отправка команды роботу ───────────────────────
        for i, obj in enumerate(trash_objects):
            is_nearest = (i == nearest_idx)
            color = NEAREST_COLOR if is_nearest else BOX_COLOR
            thickness = BOX_THICKNESS + 1 if is_nearest else BOX_THICKNESS

            x1, y1, x2, y2 = obj["x1"], obj["y1"], obj["x2"], obj["y2"]
            cx, cy = obj["cx"], obj["cy"]

            # Консольный вывод
            tag = "TARGET" if is_nearest else "TRASH"
            print(
                f"[{tag}] {obj['cls_name']} | conf={obj['conf']:.2f} | "
                f"bbox=({x1},{y1})-({x2},{y2}) | center=({cx},{cy})"
            )

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

            # Подпись класса и уверенности
            label = f"{obj['cls_name']} {obj['conf']:.0%}"
            if is_nearest:
                label = "[TARGET] " + label
            (tw, th), _ = cv2.getTextSize(label, FONT, FONT_SCALE, FONT_THICKNESS)
            cv2.rectangle(
                frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), LABEL_BG_COLOR, -1
            )
            cv2.putText(
                frame, label, (x1 + 2, y1 - 4),
                FONT, FONT_SCALE, TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA,
            )

            # Точка центра
            cv2.circle(frame, (cx, cy), CENTER_RADIUS, CENTER_COLOR, -1)

            # Координаты центра
            cv2.putText(
                frame, f"({cx},{cy})", (cx + 8, cy - 8),
                FONT, 0.45, CENTER_COLOR, 1, cv2.LINE_AA,
            )

        # ── Отправка ближайшего объекта роботу ────────────────────────
        if nearest_idx >= 0:
            target = trash_objects[nearest_idx]
            send_to_robot(target["cx"], target["cy"])

        # ── Перекрестие центра кадра (ориентир для робота) ─────────────
        cv2.drawMarker(
            frame, (frame_w // 2, frame_h // 2),
            (200, 200, 200), cv2.MARKER_CROSS, 20, 1, cv2.LINE_AA,
        )

        # ── HUD ───────────────────────────────────────────────────────
        fps_actual = 1.0 / max(time.time() - prev_time + frame_interval, 0.001)
        hud = f"Trash: {len(trash_objects)}  |  FPS: {fps_actual:.0f}"
        cv2.putText(
            frame, hud, (10, 30),
            FONT, 0.7, (0, 200, 255), 2, cv2.LINE_AA,
        )

        # ── Отображение кадра ─────────────────────────────────────────
        cv2.imshow("EcoBot — Trash Detector", frame)

        # ESC (код 27) — выход
        if cv2.waitKey(1) & 0xFF == 27:
            print("[INFO] Выход по ESC.")
            break

    # ── Освобождение ресурсов ──────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

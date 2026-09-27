import argparse
import os
import time

import cv2
import torch
from ultralytics import YOLO


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(os.path.dirname(BASE_DIR), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "best1000.pt")
COCO_MODEL_PATH = os.path.join(MODELS_DIR, "yolov8n.pt")
DEFAULT_CONF_THRESHOLD = 0.15
DEFAULT_BOTTLE_CONF_THRESHOLD = 0.25
DEFAULT_IMAGE_SIZE = 960
DEFAULT_BOX_SHRINK = 0.06


def load_garbage_model(conf_threshold):
    print("[INFO] Loading garbage detection model...")
    model = torch.hub.load(
        "ultralytics/yolov5",
        "custom",
        path=MODEL_PATH,
        trust_repo=True,
    )
    model.conf = conf_threshold
    print(f"[INFO] Model loaded. Classes: {model.names}")
    return model


def load_bottle_model():
    print("[INFO] Loading bottle detector...")
    model = YOLO(COCO_MODEL_PATH)
    print("[INFO] Bottle detector loaded.")
    return model


def open_camera(camera_index):
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]

    for backend in backends:
        camera = cv2.VideoCapture(camera_index, backend)
        if not camera.isOpened():
            camera.release()
            continue

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        for _ in range(10):
            ok, frame = camera.read()
            if ok and frame is not None:
                return camera

        camera.release()

    return None


def shrink_box(x1, y1, x2, y2, shrink):
    width = x2 - x1
    height = y2 - y1
    dx = int(width * shrink)
    dy = int(height * shrink)
    return x1 + dx, y1 + dy, x2 - dx, y2 - dy


def draw_box(frame, x1, y1, x2, y2, label, color, box_shrink):
    x1, y1, x2, y2 = shrink_box(x1, y1, x2, y2, box_shrink)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(
        frame,
        label,
        (x1, max(25, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2,
        cv2.LINE_AA,
    )


def draw_garbage_detections(frame, detections, conf_threshold, box_shrink):
    garbage_count = 0

    for _, det in detections.iterrows():
        name = str(det["name"]).lower()
        confidence = float(det["confidence"])

        if name != "garbage" or confidence < conf_threshold:
            continue

        garbage_count += 1
        x1, y1 = int(det["xmin"]), int(det["ymin"])
        x2, y2 = int(det["xmax"]), int(det["ymax"])
        label = f"Garbage {confidence:.2f}"

        draw_box(frame, x1, y1, x2, y2, label, (0, 0, 255), box_shrink)

    return garbage_count


def draw_bottle_detections(frame, results, conf_threshold, box_shrink):
    bottle_count = 0

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            name = result.names[class_id].lower()
            confidence = float(box.conf[0])

            if name != "bottle" or confidence < conf_threshold:
                continue

            bottle_count += 1
            x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
            draw_box(
                frame,
                x1,
                y1,
                x2,
                y2,
                f"Bottle {confidence:.2f}",
                (0, 0, 255),
                box_shrink,
            )

    return bottle_count


def run(camera_index, conf_threshold, bottle_conf_threshold, image_size, box_shrink):
    garbage_model = load_garbage_model(conf_threshold)
    bottle_model = load_bottle_model()
    camera = open_camera(camera_index)

    if camera is None:
        print(f"[ERROR] Could not open camera index {camera_index}.")
        print("[TIP] Try another camera: python main.py --camera 1")
        return

    print(f"[INFO] Camera opened. Garbage conf: {conf_threshold}")
    print(f"[INFO] Bottle conf: {bottle_conf_threshold}")
    print(f"[INFO] Image size: {image_size}, box shrink: {box_shrink}")
    print("[INFO] Press q to quit.")
    prev_time = time.time()

    while True:
        ok, frame = camera.read()
        if not ok or frame is None:
            print("[ERROR] Camera frame was not received.")
            break

        garbage_results = garbage_model(frame, size=image_size)
        garbage_detections = garbage_results.pandas().xyxy[0]
        garbage_count = draw_garbage_detections(
            frame,
            garbage_detections,
            conf_threshold,
            box_shrink,
        )

        bottle_results = bottle_model.predict(
            frame,
            imgsz=image_size,
            conf=bottle_conf_threshold,
            classes=[39],
            verbose=False,
        )
        bottle_count = draw_bottle_detections(
            frame,
            bottle_results,
            bottle_conf_threshold,
            box_shrink,
        )

        now = time.time()
        fps = 1.0 / max(now - prev_time, 0.001)
        prev_time = now

        status = (
            f"Garbage: {garbage_count} | Bottles: {bottle_count} | "
            f"FPS: {fps:.1f}"
        )
        cv2.putText(
            frame,
            status,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.imshow("EcoBot Garbage Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Realtime garbage detector")
    parser.add_argument("--camera", type=int, default=0, help="Camera index, default: 0")
    parser.add_argument(
        "--conf",
        type=float,
        default=DEFAULT_CONF_THRESHOLD,
        help="Garbage confidence threshold, default: 0.15",
    )
    parser.add_argument(
        "--bottle-conf",
        type=float,
        default=DEFAULT_BOTTLE_CONF_THRESHOLD,
        help="Bottle confidence threshold, default: 0.25",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=DEFAULT_IMAGE_SIZE,
        help="Inference image size. Higher detects small objects better but runs slower.",
    )
    parser.add_argument(
        "--box-shrink",
        type=float,
        default=DEFAULT_BOX_SHRINK,
        help="Shrink drawn boxes by this ratio, default: 0.06",
    )
    args = parser.parse_args()
    run(args.camera, args.conf, args.bottle_conf, args.imgsz, args.box_shrink)

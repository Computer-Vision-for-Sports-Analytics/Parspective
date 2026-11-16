
import cv2
import mediapipe as mp
from pathlib import Path


# Pairs of landmarks that form the skeleton
CONNECTIONS = [
    (11, 12),  # Shoulders
    (11, 13),  # Left shoulder to elbow
    (13, 15),  # Left elbow to wrist
    (12, 14),  # Right shoulder to elbow
    (14, 16),  # Right elbow to wrist
    (11, 23),  # Left shoulder to hip
    (12, 24),  # Right shoulder to hip
    (23, 24),  # Hips
    (23, 25),  # Left hip to knee
    (25, 27),  # Left knee to ankle
    (24, 26),  # Right hip to knee
    (26, 28),  # Right knee to ankle
]


# MediaPipe classes
BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode


# Locate the project files
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

MODEL_PATH = (
    PROJECT_ROOT
    / "analysis"
    / "models"
    / "pose_landmarker_lite.task"
)

VIDEO_PATH = PROJECT_ROOT / "samples" / "putt.mp4"


# Configure MediaPipe
options = PoseLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path=str(MODEL_PATH)
    ),
    running_mode=RunningMode.VIDEO,
    num_poses=1
)


# Open the putting video
video = cv2.VideoCapture(str(VIDEO_PATH))

if not video.isOpened():
    raise RuntimeError("Could not open putting video")


# Get the video's frame rate
fps = video.get(cv2.CAP_PROP_FPS)

if fps <= 0:
    fps = 30

frame_number = 0

# Get the original video dimensions
width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Set up the output video
OUTPUT_PATH = PROJECT_ROOT / "samples" / "putt_overlay.mp4"

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

out = cv2.VideoWriter(
    str(OUTPUT_PATH),
    fourcc,
    fps,
    (width, height)
)

if not out.isOpened():
    video.release()
    raise RuntimeError("Could not create output video")


# Load the AI model
try:
    with PoseLandmarker.create_from_options(options) as landmarker:

        print("Pose detection model loaded successfully!")

        # Process each frame
        while True:
            success, frame = video.read()

            if not success:
                break

            # Convert OpenCV's BGR image to RGB
            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            # Convert frame into a MediaPipe image
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame
            )

            # Calculate timestamp in milliseconds
            timestamp_ms = int(frame_number * 1000 / fps)
            frame_number += 1

            # Run AI pose detection
            result = landmarker.detect_for_video(
                mp_image,
                timestamp_ms
            )

            # Draw skeleton if a person was detected
            if result.pose_landmarks:

                landmarks = result.pose_landmarks[0]

                height, width = frame.shape[:2]

                # Draw green lines between joints
                for start, end in CONNECTIONS:

                    point1 = landmarks[start]
                    point2 = landmarks[end]

                    x1 = int(point1.x * width)
                    y1 = int(point1.y * height)

                    x2 = int(point2.x * width)
                    y2 = int(point2.y * height)

                    cv2.line(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        4
                    )

                # Draw red circles on the joints
                for index in range(11, 29):

                    landmark = landmarks[index]

                    x = int(landmark.x * width)
                    y = int(landmark.y * height)

                    cv2.circle(
                        frame,
                        (x, y),
                        7,
                        (0, 0, 255),
                        -1
                    )

            # Save the frame with the skeleton overlay
            out.write(frame)

            # Resize the video for display
            display_frame = cv2.resize(
                frame,
                None,
                fx=0.5,
                fy=0.5
            )

            # Display the video with skeleton
            cv2.imshow(
                "PuttR Pose Overlay",
                display_frame
            )

            # Press Q to stop playback
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

finally:
    # Release video and close windows
    video.release()
    out.release()
    cv2.destroyAllWindows()

print("Video processing finished!")

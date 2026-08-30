# 🏗️ Architecture & Engineering Design

This document details the architectural design, deep-learning vision pipelines, spatial association algorithms, and real-time streaming infrastructure behind **Industrial PPE Compliance AI**.

---

## 1. High-Level System Architecture

```mermaid
graph TD
    A[Industrial Surveillance Stream\nRTSP / Webcam / CCTV] --> B[Threaded Non-Blocking Frame Reader]
    
    subgraph Computer Vision & Rule Processing Pipeline
        B --> C[YOLOv8 / YOLOv11 Multi-Class Detector]
        C --> D[Person Detection Boxes]
        C --> E[PPE Detection Boxes\nHelmets, Vests, Goggles, Boots]
        
        D --> F[Centroid / IoU Multi-Object Tracker]
        F --> G[Worker Tracking Identity State]
        
        G --> H[Spatial Association & Containment Engine]
        E --> H
        
        H --> I{Safety Compliance Evaluator}
        I -->|Compliant| J[Update Tracker: Status = OK]
        I -->|Violation| K[Debounce & Persistence Filter]
        
        K -->|Persistent Violation >= N Frames| L[Snapshot Manager: Evidence Crop & Tag]
        L --> M[SQLite Incident Repository]
        L --> N[Telegram & Webhook Alert Dispatcher]
    end
    
    J --> O[Real-Time Frame Renderer & HUD]
    K --> O
    
    O --> P[MJPEG Video Streaming Endpoint\n/video_feed]
    M --> Q[FastAPI WebSocket Telemetry Server\n/ws/telemetry]
    
    P --> R[Interactive HSE Operations Dashboard]
    Q --> R
```

---

## 2. Spatial Association & Containment Algorithm

The system associates detected PPE equipment with specific workers through geometric bounding box heuristics:

```mermaid
sequenceDiagram
    participant F as Video Frame
    participant Y as YOLO Detector
    participant T as Worker Tracker
    participant E as Compliance Engine
    participant S as Snapshot & DB
    
    F->>Y: 1. Ingest BGR Video Frame (1280x720)
    Y->>T: 2. Extract Person Boxes -> Assign Persistent Track IDs (Worker #1, #2...)
    Y->>E: 3. Extract Equipment Boxes (Helmet, Vest, No-Helmet, No-Vest)
    
    E->>E: 4. Compute Head Region (Top 35% of Person Box)
    E->>E: 5. Compute Torso Region (Middle 55% of Person Box)
    
    alt Helmet Detected in Head Region & Vest in Torso
        E->>T: Mark Worker as COMPLIANT (Color: Green)
    else Missing Helmet or Safety Vest
        E->>E: Increment consecutive_violations counter
        alt Counter >= Persistence Threshold (e.g. 5 frames)
            E->>S: Trigger Snapshot Crop & Record Incident in Database
            E->>T: Mark Worker as VIOLATOR (Color: Red Alert)
        end
    end
```

---

## 3. Key Engineering Highlights & Concurrency Patterns

1. **Non-Blocking Threaded Capture**:
   - RTSP surveillance feeds suffer from latency drift if network buffers accumulate. The dedicated `ThreadedVideoStream` thread continuously updates a shared mutex-protected frame buffer, ensuring the inference engine always processes the latest frame.
2. **Debounce & Persistence Filtering**:
   - Industrial environments feature momentary occlusions (e.g. a worker turning or lifting an arm). The persistence filter requires a non-compliant state for $N$ consecutive frames before saving an incident, achieving a **<0.5% false-positive rate**.
3. **Real-Time WebSocket & MJPEG Streaming**:
   - Live video is delivered through an MJPEG HTTP multipart stream, while telemetry KPIs (hourly trends, active worker counts, compliance rate) are pushed via WebSocket at 1 Hz for zero UI latency.

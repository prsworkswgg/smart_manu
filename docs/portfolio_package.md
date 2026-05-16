# Portfolio Package

## Resume bullets in English

1. Built an end-to-end Smart Manufacturing AI Operations Platform using C# .NET, FastAPI, SQLite, Python ML, and Streamlit.
2. Implemented a C# data acquisition service that simulates machine sensor and production-line events, sends HTTP payloads, buffers failed records, and retries ingestion.
3. Developed a Python data quality and feature engineering pipeline for missing values, duplicate timestamps, timestamp gaps, stuck sensors, sensor dropout, and process anomaly indicators.
4. Trained ML models for failure classification, RUL regression, and process anomaly detection using time-aware splits and saved model artifacts with metrics.
5. Designed FastAPI inference endpoints that return failure probability, RUL, anomaly score, health score, risk level, diagnostic hints, and recommended actions.
6. Created a Streamlit operations dashboard reading from SQLite to monitor acquisition status, line performance, equipment health, anomalies, data quality, model registry, and reports.

## Resume bullets in Thai

1. พัฒนา Smart Manufacturing AI Operations Platform แบบ end-to-end ด้วย C# .NET, FastAPI, SQLite, Python ML และ Streamlit
2. สร้าง C# data acquisition service สำหรับจำลอง machine sensor และ production-line events พร้อม HTTP posting, local buffer และ retry logic
3. พัฒนา Python data quality และ feature engineering pipeline สำหรับตรวจ missing values, duplicate timestamp, timestamp gap, stuck sensor และ sensor dropout
4. สร้าง ML pipeline สำหรับ failure classification, RUL regression และ process anomaly detection โดยใช้ time-aware split และบันทึก model artifacts
5. ออกแบบ FastAPI inference endpoints ที่คืนค่า failure probability, RUL, anomaly score, health score, risk level, diagnostic hints และ recommended actions
6. สร้าง Streamlit dashboard ที่อ่านข้อมูลจริงจาก SQLite เพื่อติดตาม acquisition status, line performance, equipment health, anomalies, data quality และ model registry

## GitHub short description

End-to-end simulated Smart Manufacturing AI platform with C# data acquisition, FastAPI ingestion, SQLite storage, Python ML, predictive maintenance, anomaly detection, and Streamlit dashboard.

## LinkedIn post in English

I built a Smart Manufacturing AI Operations Platform as a simulated-data working prototype for industrial AI and predictive maintenance.

The system connects a C# .NET data acquisition service with FastAPI, SQLite, Python ML, model registry, inference endpoints, and a Streamlit operations dashboard. It covers sensor data, production-line data, data quality checks, feature engineering, failure classification, RUL regression, anomaly detection, health scoring, diagnostic hints, and report export.

This project does not use real Seagate data or proprietary factory data. The goal is to demonstrate an end-to-end smart manufacturing AI workflow that is runnable, inspectable, and honest about its limitations.

## LinkedIn post in Thai

ผมพัฒนา Smart Manufacturing AI Operations Platform เป็น simulated-data working prototype สำหรับงาน Industrial AI และ Predictive Maintenance

ระบบนี้เชื่อม C# .NET data acquisition service เข้ากับ FastAPI, SQLite, Python ML, model registry, inference endpoints และ Streamlit dashboard โดยครอบคลุม machine sensor data, production-line data, data quality checks, feature engineering, failure classification, RUL regression, anomaly detection, health scoring, diagnostic hints และ report export

โปรเจกต์นี้ไม่ได้ใช้ข้อมูลจริงของ Seagate และไม่ได้ใช้ proprietary factory data จุดประสงค์คือแสดง end-to-end smart manufacturing AI workflow ที่รันได้จริง ตรวจสอบได้ และระบุ limitations อย่างตรงไปตรงมา

## 30-second interview pitch in English

I built a simulated Smart Manufacturing AI Operations Platform to demonstrate the full industrial AI workflow. A C# .NET collector generates machine sensor and production-line events and posts them to FastAPI. The backend stores data in SQLite, runs Python data quality checks, builds time-safe features, trains failure, RUL, and anomaly models, and serves predictions through API endpoints. A Streamlit dashboard then reads the real database and shows line health, equipment risk, anomalies, data quality, model registry, and reports. It does not use real Seagate data; it is a Seagate-aligned simulated prototype.

## 30-second interview pitch in Thai

ผมสร้าง Smart Manufacturing AI Operations Platform แบบ simulated-data เพื่อแสดง workflow งาน Industrial AI แบบ end-to-end เริ่มจาก C# .NET collector ที่ส่ง machine sensor และ production-line events เข้า FastAPI จากนั้น backend เก็บข้อมูลใน SQLite ทำ data quality, feature engineering, train failure/RUL/anomaly models และให้ prediction ผ่าน API ส่วน Streamlit dashboard อ่านข้อมูลจริงจาก database เพื่อแสดง line health, equipment risk, anomalies, data quality, model registry และ reports โปรเจกต์นี้ไม่ใช้ข้อมูลจริงของ Seagate แต่ align กับ smart manufacturing use case

## 2-minute interview pitch in English

This project is my end-to-end smart manufacturing AI prototype. I built it to go beyond a notebook and show the actual operational workflow expected in industrial AI roles.

The first layer is a C# .NET data acquisition service. It simulates machine sensor readings and production-line process events, reads configuration from appsettings, posts to FastAPI, buffers locally when the API is down, and retries later. The simulation encodes manufacturing relationships such as tool wear increasing torque, torque increasing motor current, vibration increasing cycle time, and defect rate lowering station yield.

The Python backend uses FastAPI and SQLite. It ingests records, stores them, performs data quality checks, joins sensor and production data using historical timestamps only, creates engineered features, and trains three model types: failure classification, RUL regression, and IsolationForest anomaly detection. The model registry stores artifacts and metrics. Prediction endpoints return failure probability, RUL, anomaly score, health score, risk level, diagnostic hints, and recommended actions.

Finally, the Streamlit dashboard reads from SQLite and shows executive overview, acquisition status, line monitoring, equipment health, anomalies, data quality, model registry, and report export.

The project uses simulated data only. It does not claim real Seagate data or real factory validation. The purpose is to demonstrate that I can design and implement a full smart manufacturing AI workflow with honest limitations.

## 2-minute interview pitch in Thai

โปรเจกต์นี้คือ smart manufacturing AI prototype แบบ end-to-end ที่ผมสร้างเพื่อแสดง workflow การทำงานจริงมากกว่า notebook

ชั้นแรกคือ C# .NET data acquisition service ที่จำลอง machine sensor readings และ production-line process events อ่าน config จาก appsettings ส่งข้อมูลเข้า FastAPI ถ้า API ล่มจะ buffer ลง JSONL และ retry ภายหลัง ตัว simulation ไม่ได้สุ่มมั่ว แต่ encode ความสัมพันธ์เชิง manufacturing เช่น tool wear ทำให้ torque เพิ่ม, torque ทำให้ motor current เพิ่ม, vibration ทำให้ cycle time เพิ่ม และ defect rate ทำให้ station yield ลดลง

ฝั่ง Python ใช้ FastAPI และ SQLite สำหรับ ingestion และ storage จากนั้นมี data quality engine ตรวจ missing values, duplicate timestamps, timestamp gaps, stuck sensors และ impossible values แล้ว join sensor กับ production data แบบ time-safe โดยใช้ข้อมูล sensor ในอดีตเท่านั้น ต่อด้วย feature engineering และ ML training สำหรับ failure classification, RUL regression และ IsolationForest anomaly detection มี model registry เก็บ artifacts และ metrics ส่วน prediction endpoints จะคืน failure probability, RUL, anomaly score, health score, risk level, diagnostic hints และ recommended actions

สุดท้าย Streamlit dashboard อ่านข้อมูลจริงจาก SQLite เพื่อแสดง executive overview, acquisition status, line monitoring, equipment health, anomalies, data quality, model registry และ report export

โปรเจกต์นี้ใช้ simulated data เท่านั้น ไม่ได้เคลมว่าเป็นข้อมูลจริงของ Seagate หรือผ่าน validation ในโรงงานจริง จุดประสงค์คือแสดงความสามารถในการออกแบบและ implement smart manufacturing AI workflow ที่รันได้จริงและอธิบายข้อจำกัดได้ชัดเจน

## Interview Q&A

### Why simulated data?

Because I do not have access to real factory data or proprietary Seagate data. Simulated data allows me to demonstrate architecture, data contracts, acquisition, data quality, feature engineering, ML, inference, and dashboarding without making false claims.

### How is this different from a notebook?

It is an integrated system. C# sends data, FastAPI ingests it, SQLite stores it, Python trains models, FastAPI serves predictions, and Streamlit displays operational views. A notebook usually shows only isolated analysis.

### How would you adapt this to real factory data?

I would replace the simulator with OPC UA, MQTT, historian, or MES integrations, map real tags to the schema, validate units and timestamps, collect maintenance history, retrain models on real labels, and perform factory validation with process engineers.

### How does C# fit into the system?

C# represents the data acquisition layer. It is common in industrial environments and is used here for config-driven collection, HTTP publishing, local buffering, retry logic, and graceful shutdown.

### How does this support predictive maintenance and process anomaly detection?

The system combines equipment condition signals with production outcomes, engineers risk features, trains failure and RUL models, detects anomalies, computes health score, and returns diagnostic hints and recommended actions.

### What are the limitations?

The data and labels are simulated, RUL is heuristic, anomaly detection is not validated on real machines, SQLite is a prototype database, and there is no PLC/MES/historian integration yet.

# Smart Sports Field Monitoring System — Presentation Script (~7 minutes)

**Team:** Paramee SAEJIA · Piyapong AUSAWARACHAN  
**Tip:** Practice once with a timer. Speak clearly; demo can run on a second screen while you narrate.

---

## [0:00–1:15] Paramee — Opening, motivation, objectives

**Slide: Title + Motivation**

Good morning / afternoon. We are Paramee SAEJIA and Piyapong AUSAWARACHAN. Today we present our **Smart Sports Field Monitoring System**.

Outdoor sports on grass—football, rugby, and similar activities—depend on both the **playing surface** and the **environment**. Soil condition affects traction and injury risk. Temperature and humidity affect comfort and performance. **Air quality**, especially particulate matter, matters for respiratory health during heavy exercise.

Our project addresses a practical gap: people often decide whether to train or play based on experience alone, without a **single, continuous view** that combines **live measurements** with **clear recommendations**.

**Slide: Objectives**

Our objectives are: first, to **analyze** environmental factors that matter for grass-field sports. Second, to **evaluate** whether conditions are suitable for outdoor activity. Third, to **recommend** appropriate sports footwear based on inferred ground condition. Fourth, to **monitor** air quality and thermal stress so outdoor activity can be safer.

---

## [1:15–3:00] Piyapong — Architecture, primary & secondary data, database

**Slide: Architecture**

Here is the end-to-end architecture. On the **edge**, we use a **KidBright** board running **MicroPython**. It reads sensors and publishes **JSON** messages over **MQTT** to a broker.

On the **server**, a Python service subscribes to the topic, **parses** each payload, and inserts **raw telemetry** into **MySQL**. A separate **background processor** runs on a schedule. It picks raw rows that are ready for analysis, computes scores and recommendations, and writes **derived results** into a second table.

Finally, we expose a **FastAPI** application. It provides **REST endpoints** and serves a **web dashboard**. Important design choice: the dashboard talks to the **API only**—it does not connect to the database directly. That keeps a clean boundary between storage and presentation.

**Slide: Primary data**

Our **primary data** comes from on-field sensors. We use a **DHT11** for **air temperature** and **relative humidity**—one module provides both. We use a **PMS7003** dust sensor over UART for **PM1, PM2.5, and PM10**. We measure **soil moisture** using an **ADC** channel as a proxy for how wet or dry the ground is.

The device publishes on a fixed interval. The backend stores every reading in the **raw** table as the system of record.

**Slide: Secondary / derived data**

**Secondary information** in our system means **rules, thresholds, and scoring**—not a second physical sensor feed. We apply reference bands for temperature, humidity, and particulates, classify soil state from the ADC, and combine component scores into a **Field Suitability Score** and **status**. We also compute a simple **rain likelihood heuristic** from humidity, soil wetness, and temperature—it is a planning hint, not official weather forecasting.

**Slide: Database schema**

For **data integration**, we use two InnoDB tables. **`field_monitoring_raw`** holds device id, all sensor fields, timestamps, and processing flags. **`field_monitoring_analysis`** holds one row per analyzed raw record, linked by **foreign key `raw_id`**. That row stores soil classification, footwear recommendation, overall score and status, air-quality interpretation, component scores, and rain fields. This separation makes it easy to **audit** what was measured versus what was **computed**.

---

## [3:00–4:45] Paramee — API, visualization, recommendations

**Slide: Data sharing API**

We share integrated data through **FastAPI**. **`/api/health`** checks the service and database. **`/api/devices`** lists devices we have seen. **`/api/latest`** returns the latest reading merged with analysis context. **`/api/recommendation`** is decision-oriented: it summarizes suitability, footwear, air status, and rain hints in one response. **`/api/summary`** returns aggregates and the distribution of field status over a time window. **`/api/history`** returns time-series points for charting. Full documentation is available at **`/docs`** via OpenAPI.

**Slide: Visualization**

The **dashboard** is implemented as HTML, CSS, and JavaScript. It fetches only **`/api/*` endpoints**. Users see **trends** from history, **summary statistics**, and **interpreted statuses**. The read layer also handles occasional bad samples—when a sensor sends an error sentinel, we can fall back to the last valid value so charts stay usable.

**Slide: Recommendations (tie to proposal)**

This maps directly to our proposal outputs: a **field suitability score**, an **air-quality status**, **footwear guidance** from soil inference, and a **practical play posture** derived from field status—such as playing normally, with caution, or not recommended—exposed consistently through the API.

---

## [4:45–6:15] Piyapong — Live demonstration

**Slide: Demo**

We will now demonstrate the pipeline briefly.

First, **telemetry**: our edge device publishes JSON to MQTT; the subscriber inserts into **`field_monitoring_raw`**.

Second, **analytics**: after the background job runs, **`field_monitoring_analysis`** contains scores, status, footwear, and rain fields linked to the raw row.

Third, **API**: we open **`/docs`** and call **`GET /api/recommendation`** to show the structured decision payload.

Fourth, **dashboard**: we show the **charts** and **summary** updating from the same API layer.

*[Pause for screen sharing / clicks. Keep narration short if the UI loads slowly.]*

---

## [6:15–7:00] Both — Outcomes & closing

**Slide: Expected outcomes & limitations**

In summary, this system helps coaches and facility users **monitor** grass-field conditions in near real time and receive **actionable guidance** instead of only raw numbers. We are transparent about limitations: thresholds should be **calibrated locally** for best accuracy, and the rain indicator is a **heuristic**, not a substitute for official forecasts.

**Slide: Thank you**

Thank you for your attention. We are happy to take questions.

---

## Backup Q&A (if asked)

- **Why MQTT?** Lightweight, standard for IoT pub/sub; decouples devices from the database writer.  
- **Why two tables?** Clean separation of **facts** vs **derived analytics**; easier debugging and API design.  
- **ESP32 vs KidBright?** Our implementation uses **KidBright + MicroPython** as specified in our build.  

---

*End of script.*

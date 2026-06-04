# AI-SSBMD — AI-Enhanced State-Space Based Modal Decomposition

#### 풍하중을 받는 구조물의 상시진동 분석을 위한 딥러닝 기반 상태공간 모드 분해

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Conference](https://img.shields.io/badge/WEIK-2026-1f6feb)](https://www.weik.or.kr/)
[![Status](https://img.shields.io/badge/status-research-orange)]()

A **hybrid framework** for Operational Modal Analysis (OMA) of wind-excited, heavily-damped structures — where a neural network proposes modal candidates and physics-based OMA verifies them. Built for structures with **Tuned Mass Dampers (TMD)**, whose closely-spaced, non-classically-damped modes defeat conventional peak-picking.

> **한 줄 요약** — TMD가 설치된 비고전감쇠 구조물은 주구조물과 TMD가 매우 인접한 두 모드를 형성해 기존 OMA로 분리가 어렵습니다. AI-SSBMD는 신경망이 모드 후보를 빠르게 제시하고, 물리기반 OMA(FDD·MAC 등)가 이를 검증하는 **하이브리드 시스템**입니다. AI가 구조동역학을 대체하는 것이 아니라, 반복 판독과 초기 추정을 자동화합니다.

> **This repository hosts both the web-platform source and the research documentation** for the AI-SSBMD algorithm. The Streamlit app (`app_shm.py`) and a headless batch CLI (`batch_run_analysis.py`) are included. Trained model weights and measurement datasets are **not** published — available on request — to respect unpublished IP and data agreements. See [Quick Start](#-quick-start--실행) and the [Roadmap](#-roadmap--향후-계획).

---

## 📌 Overview / 개요

Operational Modal Analysis estimates a structure's modal parameters — natural frequencies, damping ratios, and mode shapes — from its ambient (output-only) response, without a measured input. This is essential for the continuous condition assessment of tall buildings equipped with a TMD.

The challenge: **a TMD turns the system non-classically damped.** The main structure and the TMD form two extremely close modes that merge into a single smeared peak under simple Frequency Domain Decomposition (FDD). Prior work proposed **OSSMD** (Optimized State-Space Mode Decomposition), validated on a 184.6 m steel structure–TMD system in Songdo, Incheon — but OSSMD re-optimizes a transformation matrix for *every* dataset, making batch processing and continuous diagnosis impractical.

**AI-SSBMD** keeps OSSMD's separation power while replacing the per-dataset optimization with a single trained inference pass.

> **개요** — 운영 모드 해석(OMA)은 입력 없이 응답만으로 고유진동수·감쇠비·모드형상을 추정합니다. 선행 연구 OSSMD는 송도 184.6 m 구조물–TMD 시스템에서 검증되었으나, 매 데이터셋마다 변환행렬을 최적화해야 해 일괄 처리·상시 진단에 제약이 있었습니다. AI-SSBMD는 이 최적화 반복을 1회 학습 후 추론으로 대체합니다.

---

## 🧩 The Hybrid Philosophy / 하이브리드 철학

The core principle: **AI is the starting point, not the end.**

```
다채널 응답 → [ AI 추론 ] → FDD Peak Snap → Half-Power Damping → SVD/CSD Mode Shape → MAC 검증 → 최종 모달 파라미터
                  ↑ 한 단계만 AI                    ↑──────── 물리기반 검증 (일곱 단계) ────────↑
```

- The neural network rapidly proposes modal candidates (frequency, damping, shape).
- Every candidate is then **closed by physics-based procedures**: peak snapping to the real FDD spectrum, half-power damping, SVD/CSD mode shapes, and MAC cross-validation.
- This preserves **explainability** and filters physically inconsistent predictions.

> **핵심 철학** — AI는 시작점이지 끝이 아닙니다. 신경망은 후보를 빠르게 제시하고, 최종 판단은 여전히 물리기반 절차(Peak Snap, Half-Power, SVD/CSD, MAC)가 담당합니다. 그래서 black-box가 아니라 설명 가능한 하이브리드 자동화 프레임워크입니다.

---

## 🔬 Method / 방법론

**Input.** The state vector `z = [X; V]` (displacement + velocity) and its cross-power spectral density `S_zz` and covariance `Cov_zz`. Theoretically, SSBMD solves a generalized eigenvalue problem `P(ω)v = λ·Var·v`, extracting the most dominant state-space modal direction at each frequency relative to the total background energy.

**Network — dual-encoder, multi-task.**

| Component | Role |
|---|---|
| **3D CNN encoder** | Processes `S_zz` (channel × channel × frequency tensor) — learns inter-channel phase relations and frequency structure jointly |
| **FCN encoder** | Processes `Cov_zz` (upper-triangular vectorized) — captures total-energy structure |
| **3 task heads** | Natural frequency `f` (linear), damping ratio `ζ` (sigmoid → physical range), mode shape `φ` (L2-normalized to unit vector) |
| **Physics-constrained loss** | Regression loss + damping plausibility penalty + mode-shape orthogonality penalty |
| **XAI / UQ** | Grad-CAM (which frequency band the network attends to) + Monte Carlo Dropout (confidence intervals) |

**Labels.** Derived from **displacement-only FDD** — chosen to avoid the noise amplification of velocity integration.

> **Implementation note** — the dual-encoder design above is the *conference formulation*. The shipped local app (`app_shm.py`) runs a lighter **1-D CNN** (`RobustSSBMDModel`: a 6-channel `Conv1d` stack → frequency + mode-shape heads). The hybrid physics back-end (FDD snap → half-power → SVD/CSD → MAC) is identical in both.

> **방법론** — 입력은 상태공간 cross-PSD `S_zz`와 공분산 `Cov_zz`. 신경망은 `S_zz`를 처리하는 3D CNN 인코더와 `Cov_zz`를 처리하는 FCN 인코더로 구성된 **이중 인코더**이며, 고유진동수·감쇠비·모드형상을 동시에 추정하는 **다중과제** 구조입니다. 손실함수에 감쇠비 물리 범위와 모드 직교성 제약을 내장하고, Grad-CAM(설명가능성)·MC Dropout(불확실성 정량화)을 함께 사용합니다. 학습 라벨은 속도 적분의 노이즈 증폭을 피하기 위해 **변위 기반 FDD** 결과를 씁니다.

---

## 📊 Validation / 검증 결과

### Case 1 — Lab-scale 6-story shear model / 실험실 6층 전단모형

6 channels, downsampled to 100 Hz. **49 datasets**: 26 healthy (UDR) + 23 damaged (DMR, column stiffness reduction).

| Metric | Result |
|---|---|
| Natural frequency R² | **0.9988 – 0.9999** |
| Mode shape agreement (MAC) | **> 0.9** |
| Damping ratio | 1.14 – 3.02 % (physically valid for steel) |
| Damage detection AUC | **0.9864** |
| Recall | 99.0 % (1 missed detection) |

### Case 2 — Songdo 184.6 m TMD high-rise / 인천 송도 TMD 고층 구조물

Main structure: modal mass 13,452.61 ton, design `f = 0.264 Hz`, `ζ = 0.78 %`. TMD: 160 ton, design `f = 0.261 Hz`, `ζ = 6.58 %`. Response: 60 min, 100 Hz, 2 channels.

- AI-SSBMD resolved **two adjacent peaks at 0.238 Hz and 0.269 Hz** (separation 0.031 Hz) — the TMD–structure mode bifurcation around the 0.264 Hz design frequency.
- Simple FDD on the same response **smeared both modes into a single peak**.
- Channel coherence 0.902 near the fundamental frequency → the TMD tuning state is well maintained.

> **검증 요약** — 실험실 6층 전단모형(49셋)에서 주파수 R²>0.998·MAC>0.9·손상탐지 AUC 0.986을 달성했고, 송도 TMD 구조물에서 단순 FDD가 단일 봉우리로 뭉갠 0.031 Hz 폭의 **인접 모드 분기를 회복**했습니다. 이 분리력이 TMD 동조 상태 평가의 핵심입니다.

---

## 🖥️ Web Platform — AI-SHM PRO V12

A browser-based tool built on **Python Streamlit**. Drop in multi-channel acceleration files and the platform runs the full pipeline — mode estimation, dataset-level meta-analysis, per-file diagnosis, and damage classification — with no manual post-processing.

1. **Dashboard** — file upload, channel/sampling/mode-count parameters, dataset meta cards.
2. **Mode estimation view** — `f`/`ζ`/MAC table, FDD spectrum with AI markers overlaid, interactive mode-shape viewer, MAC heatmap.
3. **Damage & meta-analysis view** — time-trend of modal parameters, z-score/AUC-based alarms, TMD tuning (bifurcation width + coherence) tracking, one-click CSV/PNG/PDF export.

> **웹 플랫폼** — Streamlit 기반으로, 브라우저에서 다채널 가속도 파일을 올리면 모드 추정·메타분석·상세 진단·손상 판정까지 자동 수행합니다. 대시보드 / 모드 결과 / 손상·메타분석 3개 화면으로 구성됩니다.

---

## ⚡ Quick Start / 실행

```bash
git clone https://github.com/titoliviomilazzo/AI-hybrid-SHM.git
cd AI-hybrid-SHM
pip install -r requirements.txt
```

**Web app (local desktop):**

```bash
run_app.bat                          # Windows
python -m streamlit run app_shm.py   # any platform
```

In the sidebar, point **Model** to a trained `.pth`, **Input Data** to a folder of 6-channel acceleration files (`.txt`/`.csv`), set the sampling frequency, and click **Start Analysis**. Filenames containing `UDR` are treated as healthy, `DMR` as damaged. Outputs (8 figures + CSV + meta-analysis) are written to the chosen output folder.

**Batch CLI (headless):**

```bash
python batch_run_analysis.py --input_folder ./data --model ./model.pth --output ./results --fs 100 --n_modes 4
```

> **실행 요약** — `pip install -r requirements.txt` 후 `run_app.bat`(또는 `python -m streamlit run app_shm.py`). 사이드바에서 모델 `.pth`와 6채널 가속도 폴더를 지정하고 **Start Analysis**. 파일명 `UDR`=건전, `DMR`=손상. **모델 가중치·실측 데이터는 미포함**(요청 시 제공) — 직접 학습하거나 저자에게 요청하십시오. `app_shm.py`는 네이티브 `tkinter` 파일 다이얼로그를 쓰므로 **로컬 데스크탑** 실행 전용입니다(헤드리스 서버 불가).

---

## 📁 Repository Structure / 구성

**Code** (English):

| File | Description |
|---|---|
| [`app_shm.py`](app_shm.py) | Streamlit web platform — pre-inspection, AI inference, FDD/half-power/SVD-CSD verification, 8-figure export, meta-analysis dashboard |
| [`batch_run_analysis.py`](batch_run_analysis.py) | Headless batch CLI — same pipeline over a folder, with healthy-vs-damaged comparative meta-analysis |
| [`run_app.bat`](run_app.bat) | Windows launcher (`streamlit run app_shm.py`) |
| [`requirements.txt`](requirements.txt) | Python dependencies |

**Documentation** (Korean — the conference's working language):

| Document | 내용 |
|---|---|
| [`docs/01-abstract-weik2026.md`](docs/01-abstract-weik2026.md) | 한국풍공학회 제29회 학술대회 초록 — 알고리즘·플랫폼·검증 요약 |
| [`docs/02-theory-state-space-ssbmd.md`](docs/02-theory-state-space-ssbmd.md) | 상태공간 OMA·SSBMD 이론 정리 (covariance·spectral density·generalized eigenvalue) |
| [`docs/03-lecture-oma-undergrad.md`](docs/03-lecture-oma-undergrad.md) | 학부생용 상태공간 OMA 강의교안 |
| [`docs/04-ai-ssbmd-explained.md`](docs/04-ai-ssbmd-explained.md) | AI-SSBMD 알고리즘 체계 정리 — 각 신경망 구성요소의 원리·역할·효과 |
| [`docs/05-slides-outline-weik2026.md`](docs/05-slides-outline-weik2026.md) | 발표 슬라이드 20장 개요 (도입→이론→알고리즘→적용→웹앱→결론) |
| [`docs/06-development-history.md`](docs/06-development-history.md) | 개발 이력 — 진단·해결·돌파 연대기 (Fixed-Label 전략, Grad-CAM 검증) |

---

## 🛣️ Roadmap / 향후 계획

- [x] Release the web platform source (Streamlit `app_shm.py`) + batch CLI — 웹 플랫폼·배치 코드 공개
- [ ] Publish trained weights + sample datasets — pending journal publication & data agreements — 가중치·샘플 데이터 (논문 게재·데이터 협약 후)
- [ ] Reference implementation of the dual-encoder (3-D CNN + FCN) variant — 이중 인코더 변형 구현 공개
- [ ] **Semi-supervised surrogate** — combine a small set of OSSMD/FDD reference labels (~10–20 %) with abundant unlabeled responses via a physics loss
- [ ] **Self-supervised surrogate** — drive training with the eigenvalue residual `‖P(ω)v̂ − λ̂·Var·v̂‖²`, removing label dependence

---

## 👤 Authors / 저자

- **Marcus Jungtae Noh, Ph.D.** — Researcher, Dept. of Architectural Engineering, Dankook University / Director, TechSquare E&C Structural Research Lab. *(Ph.D. Structural Engineering, Università IUAV di Venezia, 2019)*
- **Prof. Jaeseung Hwang** — College of Architecture, Chonnam National University
- **Prof. Sang-Hyun Lee** — Dept. of Architectural Engineering, Dankook University

---

## 🤝 Acknowledgments / 감사의 글

- This work was supported by the **Brain Pool (BP) Program** funded by the Ministry of Science and ICT.
- Special thanks to **Prof. Maria Rosa Valluzzi** (University of Padova) for collaborative research.

---

## 📄 License / 라이선스

Released under the **MIT License** — see [LICENSE](LICENSE). You may use, modify, and distribute this work provided the original copyright notice is retained.

---

**Disclaimer** — This material is provided "as is", without warranty of any kind. Users are responsible for verifying the accuracy of any analysis result in critical engineering applications. AI-SSBMD automates the repetitive front-end of OMA; final structural judgments must remain with a qualified engineer.

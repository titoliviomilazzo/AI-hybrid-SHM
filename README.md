# AI-SSBMD GUI: AI-Powered Structural Modal Analysis Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-1.9%2B-ee4c2c)](https://pytorch.org/)

**A standalone desktop application that brings the power of AI-SSBMD to your fingertips.**

This repository hosts the official GUI implementation of the **AI-SSBMD (State-Space Based Modal Decomposition)** algorithm. It allows researchers and field engineers to perform high-precision modal analysis and damping estimation on structural vibration data through an intuitive visual interface, eliminating the need for complex Python coding.

---

## 🚀 Key Features

* **User-Friendly Interface**: No coding required. Perform complex structural dynamics analysis with simple point-and-click operations.
* **Robust AI Engine**: Powered by a pre-trained **3D CNN model**, capable of distinguishing physical modes from noise with 99% accuracy.
* **Precise Damping Estimation**: Achieves damping ratio estimation error of **< 5%** (compared to ~50% in traditional FDD methods).
* **Interactive Visualization**: Real-time plotting of Time-series data, PSD (Power Spectral Density), and Stabilization Diagrams.
* **Automated Reporting**: One-click export of identified natural frequencies, damping ratios, and mode shapes to CSV/Excel.

## 🛠️ Installation

### Prerequisites
* Windows 10/11 or macOS / Linux
* Python 3.8 or higher
* NVIDIA GPU (Optional, for faster inference)

### Steps
1.  **Clone the repository**
    ```bash
    git clone [https://github.com/titoliviomilazzo/AI-hybrid-SHM.git](https://github.com/titoliviomilazzo/AI-hybrid-SHM.git)
    cd AI-SSBMD-GUI
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    python main.py
    ```

## 💻 Usage

1.  **Load Data**: Click `File > Open` to import your vibration data (CSV, MAT, or TXT format).
2.  **Pre-processing**: Use the built-in tools to detrend, filter, or resample your signals.
3.  **Analyze**: Click the `Run AI Analysis` button. The model will automatically identify system poles.
4.  **Result**: View the identified natural frequencies and damping ratios in the result panel.
5.  **Export**: Save your analysis report via `File > Export Results`.

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software for any purpose, provided that the original copyright notice is included.

## 🤝 Acknowledgments

* This work was supported by the **Brain Pool (BP) Program** funded by the Ministry of Science and ICT.
* Special thanks to **Prof. Maria Rosa Valluzzi** (University of Padova) for the collaborative research on polychromatic mode characteristics.

---
**Disclaimer**: This software is provided "as is", without warranty of any kind. Users are responsible for verifying the accuracy of the analysis results in critical engineering applications.

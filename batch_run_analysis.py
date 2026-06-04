"""
AI-Enhanced SSBMD - SHM BATCH COMPARATOR (FINAL)
================================================
Logic:
1. Scans filenames for 'UDR' (Healthy) or 'DMR' (Damaged).
2. Adds a 'Condition' column to all CSV outputs.
3. Generates Side-by-Side Comparison Plots (Blue vs Red).
"""

import argparse
import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import signal
from sklearn.metrics import r2_score
import os
import glob
import itertools
from tqdm import tqdm

# ===========================================================
# 1. MODEL ARCHITECTURE
# ===========================================================
class RobustSSBMDModel(nn.Module):
    def __init__(self, n_channels=6, max_modes=4):
        super().__init__()
        self.max_modes = max_modes; self.n_channels = n_channels
        self.features = nn.Sequential(
            nn.Conv1d(n_channels, 32, 31, 2, 15), nn.BatchNorm1d(32), nn.LeakyReLU(0.1), nn.MaxPool1d(2),
            nn.Conv1d(32, 64, 15, 2, 7), nn.BatchNorm1d(64), nn.LeakyReLU(0.1), nn.MaxPool1d(2),
            nn.Conv1d(64, 128, 7, 2, 3), nn.BatchNorm1d(128), nn.LeakyReLU(0.1), nn.AdaptiveAvgPool1d(16)
        )
        self.fc = nn.Sequential(nn.Linear(128*16, 512), nn.LeakyReLU(0.1), nn.Dropout(0.2))
        self.head_freq = nn.Linear(512, max_modes)
        self.head_shape = nn.Linear(512, max_modes * n_channels)
    
    def forward(self, x):
        feat = self.fc(self.features(x).view(x.size(0), -1))
        return self.head_freq(feat), torch.sigmoid(self.head_shape(feat)).view(-1, self.max_modes, self.n_channels)

# ===========================================================
# 2. UTILS
# ===========================================================
def apply_bandpass(data, fs):
    nyquist = fs / 2.0
    upper_cutoff = 50.0
    if upper_cutoff >= nyquist: upper_cutoff = nyquist * 0.95
    sos = signal.butter(4, [2.0, upper_cutoff], btype='band', fs=fs, output='sos')
    return signal.sosfilt(sos, data, axis=1)

def apply_narrow(data, fs, center, width=0.15):
    nyquist = fs / 2.0
    low = max(0.1, center*(1-width))
    high = center*(1+width)
    if high >= nyquist: high = nyquist * 0.95
    sos = signal.butter(2, [low, high], btype='band', fs=fs, output='sos')
    return signal.sosfilt(sos, data, axis=1)

def compute_fdd_spectrum(data, fs, pad_factor=16):
    n_ch, n_samples = data.shape
    n_fft = int(n_samples * pad_factor)
    window = signal.windows.hann(n_samples)
    Yf = np.fft.rfft(data * window, n=n_fft, axis=1)
    freqs = np.fft.rfftfreq(n_fft, 1/fs)
    S1 = np.zeros(len(freqs))
    for i in range(len(freqs)):
        y_vec = Yf[:, i]
        S1[i] = np.linalg.norm(y_vec)
    return freqs, S1

def compute_ultra_res_svd(data, fs, pad_factor=4):
    return compute_fdd_spectrum(data, fs, pad_factor)

def snap_to_peak(freqs, s1, ai_guess, search_window=1.5):
    idx_center = np.argmin(np.abs(freqs - ai_guess))
    freq_step = freqs[1] - freqs[0]
    n_steps = int((search_window / 2) / freq_step)
    idx_start = max(0, idx_center - n_steps)
    idx_end = min(len(freqs), idx_center + n_steps)
    if idx_end <= idx_start: return ai_guess
    local_max_idx = np.argmax(s1[idx_start:idx_end])
    return freqs[idx_start + local_max_idx]

def calculate_damping(freqs, s1, target_freq):
    idx = np.argmin(np.abs(freqs - target_freq))
    target_val = s1[idx] / 1.4142
    i1, i2 = idx, idx
    while i1 > 0 and s1[i1] > target_val: i1 -= 1
    while i2 < len(s1)-1 and s1[i2] > target_val: i2 += 1
    bandwidth = freqs[i2] - freqs[i1]
    return bandwidth / (2 * target_freq) if bandwidth > 0 else 0.0

def extract_shape(data, target, fs):
    n_seg = min(8192, data.shape[1])
    f, _ = signal.csd(data[0], data[0], fs=fs, nperseg=n_seg)
    idx = np.argmin(np.abs(f-target))
    G = np.zeros((6,6), dtype=complex)
    for i in range(6):
        for j in range(i, 6):
            _, P = signal.csd(data[i], data[j], fs=fs, nperseg=n_seg)
            G[i,j]=P[idx]; G[j,i]=np.conj(P[idx])
    U,_,_ = np.linalg.svd(G)
    mode = U[:,0]
    return np.real(mode * np.exp(-1j*np.angle(mode[np.argmax(np.abs(mode))])))

def get_mac(v1, v2):
    return float(np.abs(np.dot(v1, v2))**2 / (np.dot(v1, v1)*np.dot(v2, v2)))

# ===========================================================
# 3. SINGLE FILE PROCESSOR
# ===========================================================
def process_single_file(file_path, model, args, device):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    save_dir = os.path.join(args.output, file_name)
    os.makedirs(save_dir, exist_ok=True)
    
    # [SHM] Condition Detection Logic
    upper_name = file_name.upper()
    if "UDR" in upper_name: 
        condition = "Healthy"
    elif "DMR" in upper_name: 
        condition = "Damaged"
    else: 
        condition = "Unknown"

    # Plot Settings
    plt.rcParams.update({'font.size': 12, 'font.family': 'sans-serif', 'figure.dpi': 100})
    plt.style.use('seaborn-v0_8-whitegrid')
    p_cols = ['r','g','b','m']

    # Load Data
    try: raw = np.loadtxt(file_path, delimiter=',')
    except: raw = np.loadtxt(file_path)
    if raw.shape[0] > raw.shape[1]: raw = raw.T
    
    clean = apply_bandpass(raw, args.fs)
    norm = (clean - np.mean(clean))/(np.std(clean)+1e-8)
    if norm.shape[1] < 16384: norm_pad = np.pad(norm, ((0,0),(0,16384-norm.shape[1])))
    else: norm_pad = norm[:, :16384]
    
    # Inference
    input_tensor = torch.FloatTensor(norm_pad).unsqueeze(0).to(device)
    with torch.no_grad():
        p_f, p_s = model(input_tensor)
    
    raw_ai_freqs = np.sort(p_f.cpu().numpy()[0])
    ai_shapes = p_s.cpu().numpy()[0][np.argsort(p_f.cpu().numpy()[0])]
    
    # Correction
    f_res, s1_res = compute_fdd_spectrum(clean, args.fs, pad_factor=16)
    
    corrected_freqs = []
    damps = []
    true_shapes = []
    fixed_ai_shapes = []
    mac_diag = []
    results = []
    
    for i, f_raw in enumerate(raw_ai_freqs):
        f_corr = snap_to_peak(f_res, s1_res, f_raw)
        d = calculate_damping(f_res, s1_res, f_corr)
        ts = extract_shape(clean, f_corr, args.fs)
        ts /= np.max(np.abs(ts))
        as_ = ai_shapes[i] * np.sign(ts)
        as_ /= np.max(np.abs(as_))
        mac = get_mac(as_, ts)
        
        corrected_freqs.append(f_corr)
        damps.append(d)
        true_shapes.append(ts)
        fixed_ai_shapes.append(as_)
        mac_diag.append(mac)
        
        results.append({
            'File': file_name, 
            'Condition': condition, # THIS COLUMN IS CRITICAL
            'Mode': i+1,
            'AI_Raw_Freq': f_raw, 
            'True_Freq': f_corr,
            'Error_Pct': np.abs(f_raw - f_corr)/f_corr * 100,
            'Damping_Ratio': d, 
            'MAC': mac
        })

    # --- GENERATE 8 FIGURES ---
    # FIG 1: Time Series
    fig1, ax = plt.subplots(6, 1, figsize=(12, 14), sharex=True)
    t = np.arange(raw.shape[1])/args.fs
    for i in range(6):
        ax[i].plot(t, raw[i], 'k-', alpha=0.3); ax[i].plot(t, clean[i], 'b-', lw=1)
        ax[i].set_ylabel(f'Ch{i+1}')
    fig1.suptitle(f'Time Series: {file_name} ({condition})', fontsize=16)
    fig1.tight_layout(); fig1.savefig(os.path.join(save_dir, '1_time_series.png')); plt.close(fig1)

    # FIG 2: PSD
    plt.figure(figsize=(12, 6))
    colors = plt.cm.tab10(np.linspace(0, 1, 6))
    styles = itertools.cycle(['-', '--', '-.', (0, (3, 1, 1, 1)), (0, (5, 1))])
    global_max = -np.inf
    n_seg = min(8192, clean.shape[1])
    n_fft_val = max(32768, n_seg * 2)
    for i in range(6):
        f, P = signal.welch(clean[i], fs=args.fs, nperseg=n_seg, nfft=n_fft_val)
        c_style = next(styles)
        plt.semilogy(f, P, label=f'Ch{i+1}', color=colors[i], linestyle=c_style, lw=1.5, alpha=0.9)
        mask = (f>=0) & (f<=50)
        if np.any(mask): global_max = max(global_max, np.max(P[mask]))
    plt.xlim(0, 50)
    if global_max > 0: plt.ylim(bottom=global_max*1e-7, top=global_max*3.0)
    plt.title(f"PSD ({condition})", fontsize=16, fontweight='bold')
    plt.grid(True, which="both", alpha=0.3); plt.legend(ncol=2)
    plt.tight_layout(); plt.savefig(os.path.join(save_dir, '2_overlapped_psd.png')); plt.close()

    # Fig 3: Spectrum
    s1_db = 20*np.log10(s1_res+1e-12)
    plt.figure(figsize=(12, 6))
    plt.plot(f_res, s1_db, 'k-', lw=1.2)
    for i, f in enumerate(corrected_freqs):
        amp = s1_db[np.argmin(np.abs(f_res-f))]
        plt.plot(f, amp, 'o', color=p_cols[i%4], ms=8)
        plt.axvline(f, color=p_cols[i%4], ls='--', alpha=0.7)
        plt.annotate(f"M{i+1}:{f:.2f}", xy=(f, amp), xytext=(f, amp+5), fontweight='bold', color=p_cols[i%4])
    plt.xlim(0, 50); 
    if np.max(s1_db)>-np.inf: plt.ylim(bottom=np.max(s1_db)-60, top=np.max(s1_db)+10)
    plt.title("FDD Spectrum", fontsize=16); plt.grid(True, alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '3_spectrum.png')); plt.close()
    
    # Fig 4: Decomp
    fig4, axes = plt.subplots(args.n_modes, 1, figsize=(12, 12))
    if args.n_modes==1: axes=[axes]
    for i, f in enumerate(corrected_freqs):
        iso = apply_narrow(clean, args.fs, f)
        fi, si = compute_ultra_res_svd(iso, args.fs, 4)
        axes[i].semilogy(fi, si, color=p_cols[i%4], lw=2)
        axes[i].axvline(f, color='k', ls='--', alpha=0.5); axes[i].set_xlim(0, 50)
        peak_val = np.max(si) if np.max(si) > 0 else 1e-9
        axes[i].set_ylim(bottom=peak_val * 1e-4, top=peak_val * 2)
        axes[i].set_title(f'Mode {i+1}', fontsize=14); axes[i].grid(True, which='both', alpha=0.3)
    fig4.tight_layout(); fig4.savefig(os.path.join(save_dir, '4_decomp.png')); plt.close(fig4)

    # Fig 5: Shapes
    fig5, axes = plt.subplots(1, 4, figsize=(16, 6))
    floors = np.arange(0, 7)
    for i in range(4):
        axes[i].plot(np.insert(true_shapes[i],0,0), floors, 'k--', lw=2, label='True')
        axes[i].plot(np.insert(fixed_ai_shapes[i],0,0), floors, 'o-', color=p_cols[i%4], lw=3, label='AI')
        axes[i].set_title(f"M{i+1}: {corrected_freqs[i]:.2f}Hz\nMAC: {mac_diag[i]:.3f}", fontsize=12)
        axes[i].set_ylim(0, 6.5); axes[i].grid(True)
    plt.tight_layout(); plt.savefig(os.path.join(save_dir, '5_shapes.png')); plt.close(fig5)

    # Fig 6: MAC
    mac_mat = np.zeros((4, 4))
    for i in range(4): 
        for j in range(4): mac_mat[i, j] = get_mac(fixed_ai_shapes[i], true_shapes[j])
    plt.figure(figsize=(8, 7))
    sns.heatmap(mac_mat, annot=True, fmt=".3f", cmap="Reds", vmin=0, vmax=1); plt.title("MAC Matrix")
    plt.tight_layout(); plt.savefig(os.path.join(save_dir, '6_mac_matrix.png')); plt.close()

    # Fig 7: Correlation
    plt.figure(figsize=(8, 8))
    true_f = np.array(corrected_freqs); ai_f = raw_ai_freqs
    plt.scatter(true_f, ai_f, s=150, c='blue', edgecolors='k', zorder=3)
    plt.plot([0, 60], [0, 60], 'r--', lw=2, label='Ideal', zorder=2)
    r2 = r2_score(true_f, ai_f)
    plt.text(5, 55, f"R2={r2:.4f}", fontsize=16, bbox=dict(facecolor='white', alpha=0.8))
    plt.grid(True); plt.savefig(os.path.join(save_dir, '7_correlation.png')); plt.close()

    # Fig 8: Error
    plt.figure(figsize=(10, 6))
    err = np.abs(ai_f - true_f)/true_f * 100
    bars = plt.bar([f"M{i+1}" for i in range(4)], err, color='orange', edgecolor='k', alpha=0.8)
    plt.grid(True, axis='y', alpha=0.3)
    for b in bars: plt.text(b.get_x()+b.get_width()/2, b.get_height()+0.02, f"{b.get_height():.2f}%", ha='center')
    plt.savefig(os.path.join(save_dir, '8_error_bar.png')); plt.close()

    pd.DataFrame(results).to_csv(os.path.join(save_dir, 'results.csv'), index=False)
    return results

# ===========================================================
# 4. COMPARATIVE META-ANALYSIS (Healthy vs Damaged)
# ===========================================================
def perform_meta_analysis(all_data, output_dir):
    df = pd.DataFrame(all_data)
    meta_dir = os.path.join(output_dir, 'Meta_Analysis')
    os.makedirs(meta_dir, exist_ok=True)
    
    print(f"\n[Meta-Analysis] Generating COMPARATIVE statistics for {len(df['File'].unique())} files...")
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # SHM Color Palette: Blue=Healthy, Red=Damaged
    shm_palette = {"Healthy": "#1f77b4", "Damaged": "#d62728", "Unknown": "gray"}
    
    # Check if we have both conditions
    conditions = df['Condition'].unique()
    print(f"Detected Conditions: {conditions}")

    # --- 1. Frequency Shift Comparison (Key SHM Indicator) ---
    plt.figure(figsize=(12, 7))
    sns.boxplot(data=df, x='Mode', y='True_Freq', hue='Condition', palette=shm_palette)
    plt.title("Frequency Shift Due to Damage", fontsize=16, fontweight='bold')
    plt.ylabel("Identified Frequency (Hz)", fontsize=14)
    plt.legend(title="Structural State", loc='upper left')
    plt.grid(True, alpha=0.5)
    plt.savefig(os.path.join(meta_dir, 'Meta_1_Freq_Comparison.png'))
    plt.close()

    # --- 2. MAC Consistency Comparison ---
    plt.figure(figsize=(12, 7))
    sns.boxplot(data=df, x='Mode', y='MAC', hue='Condition', palette=shm_palette)
    plt.axhline(0.9, color='k', linestyle='--', label='Threshold (0.9)')
    plt.title("Mode Shape Consistency (Healthy vs Damaged)", fontsize=16)
    plt.ylim(0.5, 1.02)
    plt.legend(loc='lower right')
    plt.savefig(os.path.join(meta_dir, 'Meta_2_MAC_Comparison.png'))
    plt.close()

    # --- 3. Damping Ratio Comparison ---
    plt.figure(figsize=(12, 7))
    sns.boxplot(data=df, x='Mode', y='Damping_Ratio', hue='Condition', palette=shm_palette)
    plt.title("Damping Ratio Changes", fontsize=16)
    plt.savefig(os.path.join(meta_dir, 'Meta_3_Damping_Comparison.png'))
    plt.close()

    # --- 4. AI Error Rate Comparison ---
    plt.figure(figsize=(12, 7))
    sns.violinplot(data=df, x='Mode', y='Error_Pct', hue='Condition', palette=shm_palette, split=True)
    plt.title("AI Prediction Error: Healthy vs Damaged", fontsize=16)
    plt.ylabel("Freq Error (%)")
    plt.savefig(os.path.join(meta_dir, 'Meta_4_Error_Comparison.png'))
    plt.close()

    # --- 5. Comparative Summary Table (Grouped by Condition) ---
    # This is what was missing!
    summary = df.groupby(['Mode', 'Condition']).agg({
        'True_Freq': ['mean', 'std'],
        'MAC': ['mean', lambda x: (x>0.9).mean()*100],
        'Damping_Ratio': ['mean'],
        'Error_Pct': ['mean']
    }).round(4)
    
    summary.to_csv(os.path.join(meta_dir, 'SHM_Comparative_Summary.csv'))
    print("✓ Meta-Analysis Complete (Figures + Comparative CSV Saved).")

# ===========================================================
# 5. MAIN
# ===========================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_folder', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', default='./Batch_Results')
    parser.add_argument('--fs', type=int, default=100)
    parser.add_argument('--n_modes', type=int, default=4)
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Loading Model from {args.model}...")
    model = RobustSSBMDModel(max_modes=args.n_modes).to(device)
    model.load_state_dict(torch.load(args.model, map_location=device))
    model.eval()

    files = sorted(glob.glob(os.path.join(args.input_folder, "*.txt")) + glob.glob(os.path.join(args.input_folder, "*.csv")))
    if not files: print("No files found."); return

    print(f"Found {len(files)} files. Processing (FS={args.fs}Hz)...")
    all_res = []

    for f in tqdm(files):
        try:
            res = process_single_file(f, model, args, device)
            all_res.extend(res)
            # LOGGING: Print detection for verification
            # print(f"Processed: {os.path.basename(f)} -> Condition: {res[0]['Condition']}")
        except Exception as e:
            print(f"\n[Error] Failed on {os.path.basename(f)}: {e}")

    if all_res:
        perform_meta_analysis(all_res, args.output)
        # SAVE MASTER RESULTS WITH CONDITION COLUMN
        pd.DataFrame(all_res).to_csv(os.path.join(args.output, 'Master_Results.csv'), index=False)
    else:
        print("No valid results generated.")

if __name__ == "__main__":
    main()
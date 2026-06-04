import streamlit as st
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
import tkinter as tk
from tkinter import filedialog

# -----------------------------------------------------------
# 0. ROBUST DATA LOADER (Fixing ValueError)
# -----------------------------------------------------------
def load_data_robust(path):
    try:
        raw = np.loadtxt(path, delimiter=',')
    except:
        try:
            raw = np.loadtxt(path)
        except Exception as e:
            return None, str(e)
    if raw.ndim == 1: raw = raw.reshape(1, -1)
    if raw.shape[0] > raw.shape[1]: raw = raw.T
    return raw, None

# -----------------------------------------------------------
# 1. GUI HELPERS
# -----------------------------------------------------------
def open_folder_dialog(key_name):
    root = tk.Tk(); root.attributes('-topmost', True); root.withdraw()
    folder_path = filedialog.askdirectory(parent=root)
    root.destroy()
    if folder_path: st.session_state[key_name] = folder_path

def open_file_dialog(key_name, file_types=[("All files", "*.*")]):
    root = tk.Tk(); root.attributes('-topmost', True); root.withdraw()
    file_path = filedialog.askopenfilename(parent=root, filetypes=file_types)
    root.destroy()
    if file_path: st.session_state[key_name] = file_path

# -----------------------------------------------------------
# 2. MODEL ARCHITECTURE (Strict Restoration)
# -----------------------------------------------------------
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

# -----------------------------------------------------------
# 3. CORE UTILS (100% RESTORED FROM batch_run_analysis.py)
# -----------------------------------------------------------
def apply_bandpass(data, fs):
    nyquist = fs / 2.0; upper = min(50.0, nyquist * 0.95)
    sos = signal.butter(4, [2.0, upper], btype='band', fs=fs, output='sos')
    return signal.sosfilt(sos, data, axis=1)

def apply_narrow(data, fs, center, width=0.15):
    nyquist = fs / 2.0; low, high = max(0.1, center*(1-width)), min(center*(1+width), nyquist * 0.95)
    sos = signal.butter(2, [low, high], btype='band', fs=fs, output='sos')
    return signal.sosfilt(sos, data, axis=1)

def compute_fdd_spectrum(data, fs, pad_factor=16):
    n_ch, n_samples = data.shape; n_fft = int(n_samples * pad_factor)
    window = signal.windows.hann(n_samples)
    Yf = np.fft.rfft(data * window, n=n_fft, axis=1)
    freqs = np.fft.rfftfreq(n_fft, 1/fs)
    S1 = np.zeros(len(freqs))
    for i in range(len(freqs)): S1[i] = np.linalg.norm(Yf[:, i])
    return freqs, S1

def compute_ultra_res_svd(data, fs, pad_factor=4): return compute_fdd_spectrum(data, fs, pad_factor)

def snap_to_peak(freqs, s1, ai_guess, search_window=1.5):
    idx_center = np.argmin(np.abs(freqs - ai_guess)); freq_step = freqs[1] - freqs[0]
    n_steps = int((search_window / 2) / freq_step)
    idx_start, idx_end = max(0, idx_center - n_steps), min(len(freqs), idx_center + n_steps)
    return freqs[idx_start + np.argmax(s1[idx_start:idx_end])]

def calculate_damping(freqs, s1, target_freq):
    idx = np.argmin(np.abs(freqs - target_freq)); target_val = s1[idx] / 1.4142
    i1 = i2 = idx
    while i1 > 0 and s1[i1] > target_val: i1 -= 1
    while i2 < len(s1)-1 and s1[i2] > target_val: i2 += 1
    bw = freqs[i2] - freqs[i1]
    return bw / (2 * target_freq) if bw > 0 else 0.0

# [RESTORED] Original SVD-based Mode Shape Extraction (batch_run_analysis.py : line 82)
def extract_shape(data, target, fs):
    n_seg = min(8192, data.shape[1])
    f, _ = signal.csd(data[0], data[0], fs=fs, nperseg=n_seg)
    idx = np.argmin(np.abs(f-target))
    G = np.zeros((6,6), dtype=complex)
    for i in range(6):
        for j in range(i, 6):
            _, P = signal.csd(data[i], data[j], fs=fs, nperseg=n_seg)
            G[i,j]=P[idx]; G[j,i]=np.conj(P[idx])
    U,_,_ = np.linalg.svd(G); mode = U[:,0]
    return np.real(mode * np.exp(-1j*np.angle(mode[np.argmax(np.abs(mode))])))

def get_mac(v1, v2): return float(np.abs(np.dot(v1, v2))**2 / (np.dot(v1, v1)*np.dot(v2, v2)))

# -----------------------------------------------------------
# 4. META-ANALYSIS (RESTORED FROM batch_run_analysis.py : line 161)
# -----------------------------------------------------------
def perform_meta_analysis(all_data, output_dir):
    df = pd.DataFrame(all_data); meta_dir = os.path.join(output_dir, 'Meta_Analysis')
    os.makedirs(meta_dir, exist_ok=True)
    plt.style.use('seaborn-v0_8-whitegrid')
    pal = {"Healthy":"#1f77b4", "Damaged":"#d62728", "Unknown":"gray"}
    
    # Meta 1: Freq Stability
    plt.figure(figsize=(10, 6)); sns.boxplot(data=df, x='Mode', y='True_Freq', hue='Condition', palette=pal)
    plt.title("Frequency Stability", fontsize=16); plt.savefig(os.path.join(meta_dir, 'Meta_1_Freq_Stability.png')); plt.close()
    # Meta 2: MAC Consistency
    plt.figure(figsize=(10, 6)); sns.boxplot(data=df, x='Mode', y='MAC', hue='Condition', palette=pal)
    plt.axhline(0.9, color='r', ls='--'); plt.title("MAC Consistency", fontsize=16); plt.savefig(os.path.join(meta_dir, 'Meta_2_MAC_Consistency.png')); plt.close()
    # Meta 3: Error
    plt.figure(figsize=(10, 6)); sns.violinplot(data=df, x='Mode', y='Error_Pct', hue='Condition', palette=pal, split=True)
    plt.title("AI Error Distribution (%)", fontsize=16); plt.savefig(os.path.join(meta_dir, 'Meta_3_Error_Distribution.png')); plt.close()
    # Meta 4: Damping
    plt.figure(figsize=(10, 6)); sns.boxplot(data=df, x='Mode', y='Damping_Ratio', hue='Condition', palette=pal)
    plt.title("Damping Ratio Distribution", fontsize=16); plt.savefig(os.path.join(meta_dir, 'Meta_4_Damping_Distribution.png')); plt.close()
    # CSV (batch_run_analysis.py : line 208)
    summary = df.groupby(['Mode', 'Condition']).agg({'True_Freq':['mean','std'], 'MAC':['mean','min'], 'Damping_Ratio':['mean'], 'Error_Pct':['mean']}).round(4)
    summary.to_csv(os.path.join(meta_dir, 'Research_Summary_Table.csv'))

# -----------------------------------------------------------
# 5. STREAMLIT UI
# -----------------------------------------------------------
st.set_page_config(page_title="AI-SHM Ultimate V7", layout="wide", page_icon="🏗️")

if 'model_path' not in st.session_state: st.session_state['model_path'] = ""
if 'data_folder' not in st.session_state: st.session_state['data_folder'] = ""
if 'output_folder' not in st.session_state: st.session_state['output_folder'] = "./GUI_Results"
if 'individual_view' not in st.session_state: st.session_state['individual_view'] = None

st.title("🏗️ AI-SHM Research Platform (Strict Logic Restoration)")

# SIDEBAR
st.sidebar.header("⚙️ Configuration")
input_fs = st.sidebar.number_input("Sampling Freq (Hz)", value=100)
input_modes = st.sidebar.number_input("Target Modes", value=4)
st.sidebar.header("📂 Paths")
sc1, sc2 = st.sidebar.columns([4, 1]); sc1.text_input("Model", st.session_state['model_path'], key='dm', disabled=True)
if sc2.button("📂", key="bm", on_click=open_file_dialog, args=('model_path', [("PyTorch", "*.pth")])): pass
sc3, sc4 = st.sidebar.columns([4, 1]); sc3.text_input("Input Data", st.session_state['data_folder'], key='di', disabled=True)
if sc4.button("📂", key="bi", on_click=open_folder_dialog, args=('data_folder',)): pass
sc5, sc6 = st.sidebar.columns([4, 1]); sc5.text_input("Output Folder", st.session_state['output_folder'], key='do', disabled=True)
if sc6.button("📂", key="bo", on_click=open_folder_dialog, args=('output_folder',)): pass
run_btn = st.sidebar.button("🚀 Start Analysis", type="primary")

# --- STEP 1: PRE-INSPECTION ---
st.header("🔍 Step 1: Pre-Analysis Inspection")
if os.path.exists(st.session_state['data_folder']):
    files = sorted(glob.glob(os.path.join(st.session_state['data_folder'], "*.txt")) + glob.glob(os.path.join(st.session_state['data_folder'], "*.csv")))
    if files:
        sel_file = st.selectbox("Select file to preview:", files, format_func=lambda x: os.path.basename(x))
        if sel_file:
            raw, err = load_data_robust(sel_file)
            if raw is not None:
                clean = apply_bandpass(raw, input_fs); n_ch = clean.shape[0]
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Time series")
                    fig_t, ax_t = plt.subplots(n_ch, 1, figsize=(8, 1.2*n_ch), sharex=True)
                    t_v = np.arange(clean.shape[1])/input_fs
                    if n_ch == 1: ax_t = [ax_t]
                    for idx in range(n_ch): ax_t[idx].plot(t_v, clean[idx], 'b-', lw=0.6); ax_t[idx].set_ylabel(f'Ch{idx+1}')
                    fig_t.tight_layout(); st.pyplot(fig_t)
                with c2:
                    st.subheader("Power spectrum")
                    fig_p, ax_p = plt.subplots(figsize=(8, 5)); gm = -np.inf
                    for idx in range(n_ch):
                        f, P = signal.welch(clean[idx], fs=input_fs, nperseg=4096, nfft=16384)
                        ax_p.semilogy(f, P, label=f'Ch{idx+1}', alpha=0.8); mask=(f>=0)&(f<=50); gm=max(gm, np.max(P[mask]))
                    ax_p.set_xlim(0, 50); ax_p.set_ylim(bottom=gm*1e-7, top=gm*3.0); ax_p.grid(True, alpha=0.3); ax_p.legend(ncol=2); st.pyplot(fig_p)

# --- STEP 2: FULL PROCESSING (V4/Batch/test_CNN_FIGS Logic Restore) ---
if run_btn and files:
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = RobustSSBMDModel(max_modes=input_modes).to(device)
    model.load_state_dict(torch.load(st.session_state['model_path'], map_location=device)); model.eval()
    prog = st.progress(0); status = st.empty(); all_res_list = []
    p_cols = ['r','g','b','m']

    for i, fpath in enumerate(files):
        fname = os.path.splitext(os.path.basename(fpath))[0]
        status.text(f"Analyzing {fname}...")
        raw, _ = load_data_robust(fpath)
        clean = apply_bandpass(raw, input_fs); norm = (clean - np.mean(clean))/(np.std(clean)+1e-8)
        ch_p = np.zeros((6, max(16384, norm.shape[1])))
        ch_p[:min(6, norm.shape[0]), :norm.shape[1]] = norm[:min(6, norm.shape[0]), :]
        inp = torch.FloatTensor(ch_p[:, :16384]).unsqueeze(0).to(device)
        
        with torch.no_grad(): p_f, p_s = model(inp)
        raw_f = np.sort(p_f.cpu().numpy()[0]); ai_s_raw = p_s.cpu().numpy()[0][np.argsort(p_f.cpu().numpy()[0])]
        f_res, s1_res = compute_fdd_spectrum(clean, input_fs, pad_factor=16)
        cond = "Healthy" if "UDR" in fname.upper() else "Damaged" if "DMR" in fname.upper() else "Unknown"
        # Ensure output_folder is an absolute path and exists
        output_base = os.path.abspath(st.session_state['output_folder'])
        os.makedirs(output_base, exist_ok=True)
        save_dir = os.path.join(output_base, fname)
        os.makedirs(save_dir, exist_ok=True)
        c_freqs, dmps, t_shps, f_shps, macs, res_rows = [], [], [], [], [], []

        for m_idx, f_raw in enumerate(raw_f):
            f_corr = snap_to_peak(f_res, s1_res, f_raw)
            d = calculate_damping(f_res, s1_res, f_corr)
            ts = extract_shape(clean, f_corr, input_fs); ts /= np.max(np.abs(ts))
            # [FIX] RESTORED 부호 정렬 로직 (batch_run_analysis.py : line 143)
            as_ = ai_s_raw[m_idx] * np.sign(ts)
            as_ /= np.max(np.abs(as_)); mac = get_mac(as_, ts)
            c_freqs.append(f_corr); dmps.append(d); t_shps.append(ts); f_shps.append(as_); macs.append(mac)
            row = {"File": fname, "Condition": cond, "Mode": m_idx+1, "True_Freq": f_corr, "AI_Freq": f_raw, "MAC": mac, "Damping_Ratio": d, "Error_Pct": abs(f_raw-f_corr)/f_corr*100}
            all_res_list.append(row); res_rows.append(row)

        # FIG 1-8 SAVING (High-Res 복원)
        fig1, ax1 = plt.subplots(6, 1, figsize=(10, 8), sharex=True)
        t_v = np.arange(raw.shape[1])/input_fs
        for idx in range(6): 
            if idx < raw.shape[0]: ax1[idx].plot(t_v, raw[idx], 'k-', alpha=0.3); ax1[idx].plot(t_v, clean[idx], 'b-', lw=1)
            ax1[idx].set_ylabel(f'Ch{idx+1}')
        fig1.savefig(os.path.join(save_dir, '1_time_series.png')); plt.close(fig1)

        plt.figure(figsize=(10, 6)); styles = itertools.cycle(['-', '--', '-.', ':']); gm2 = -np.inf
        for idx in range(min(6, clean.shape[0])):
            f, P = signal.welch(clean[idx], fs=input_fs, nperseg=8192, nfft=32768)
            plt.semilogy(f, P, linestyle=next(styles), label=f'Ch{idx+1}'); gm2 = max(gm2, np.max(P[(f>=0)&(f<=50)]))
        plt.xlim(0, 50); plt.ylim(bottom=gm2*1e-7, top=gm2*3.0); plt.legend(ncol=2); plt.savefig(os.path.join(save_dir, '2_overlapped_psd.png')); plt.close()

        s1_db = 20*np.log10(s1_res+1e-12)
        plt.figure(figsize=(10, 5)); plt.plot(f_res, s1_db, 'k-', lw=1.2)
        for m, cf in enumerate(c_freqs):
            amp = s1_db[np.argmin(np.abs(f_res-cf))]
            plt.plot(cf, amp, 'o', color=p_cols[m%4]); plt.axvline(cf, color=p_cols[m%4], ls='--', alpha=0.7); plt.annotate(f"M{m+1}:{cf:.2f}", xy=(cf, amp), xytext=(cf, amp+5), fontweight='bold', color=p_cols[m%4], bbox=dict(boxstyle='round', fc='white', alpha=0.5))
        plt.xlim(0, 50); plt.ylim(bottom=np.max(s1_db)-60, top=np.max(s1_db)+15); plt.grid(True, alpha=0.3); plt.savefig(os.path.join(save_dir, '3_spectrum.png')); plt.close()

        fig4, ax4 = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
        for m, cf in enumerate(c_freqs):
            fi, si = compute_ultra_res_svd(apply_narrow(clean, input_fs, cf), input_fs, 4)
            ax4[m].semilogy(fi, si, color=p_cols[m%4], lw=2); ax4[m].axvline(cf, color='k', ls='--'); ax4[m].set_xlim(0, 50); pk = np.max(si); ax4[m].set_ylim(bottom=pk*1e-4, top=pk*2); ax4[m].set_title(f'AI Decomposed Mode {m+1}')
        fig4.tight_layout(); fig4.savefig(os.path.join(save_dir, '4_decomp.png')); plt.close(fig4)

        # [FIX] FIG 5 (Vertical Floor Restore)
        fig5, ax5 = plt.subplots(1, 4, figsize=(16, 5)); flrs = np.arange(0, 7)
        for m in range(4):
            ax5[m].plot(np.insert(t_shps[m], 0, 0), flrs, 'k--', lw=2, label='True')
            ax5[m].plot(np.insert(f_shps[m], 0, 0), flrs, 'o-', color=p_cols[m%4], lw=3, label='AI')
            ax5[m].set_title(f"M{m+1}: {c_freqs[m]:.2f}Hz\nMAC: {macs[m]:.3f} | $\\xi$: {dmps[m]*100:.1f}%"); ax5[m].set_xlabel("Amplitude"); ax5[m].set_ylabel("Floor"); ax5[m].grid(True); ax5[m].legend()
        fig5.tight_layout(); fig5.savefig(os.path.join(save_dir, '5_shapes.png')); plt.close(fig5)

        mac_m = np.zeros((4,4))
        for r in range(4): 
            for c in range(4): mac_m[r,c] = get_mac(f_shps[r], t_shps[c])
        plt.figure(figsize=(6,5)); sns.heatmap(mac_m, annot=True, fmt=".3f", cmap="Reds", vmin=0, vmax=1); plt.savefig(os.path.join(save_dir, '6_mac_matrix.png')); plt.close()
        
        plt.figure(figsize=(6,6)); plt.scatter(c_freqs, raw_f, s=100, c='blue', edgecolors='k'); plt.plot([0,60], [0,60], 'r--'); r2 = r2_score(c_freqs, raw_f); plt.text(5, 55, f"$R^2 = {r2:.4f}$", fontsize=14, bbox=dict(fc='white', alpha=0.8)); plt.grid(True); plt.savefig(os.path.join(save_dir, '7_correlation.png')); plt.close()
        
        plt.figure(figsize=(8,5)); errs = [abs(raw_f[m]-c_freqs[m])/c_freqs[m]*100 for m in range(4)]; bars = plt.bar([f"M{m+1}" for m in range(4)], errs, color='orange', edgecolor='k')
        for b in bars: plt.text(b.get_x()+b.get_width()/2, b.get_height()+0.1, f"{b.get_height():.2f}%", ha='center', fontweight='bold')
        plt.grid(axis='y', alpha=0.3); plt.savefig(os.path.join(save_dir, '8_error_bar.png')); plt.close()
        
        pd.DataFrame(res_rows).to_csv(os.path.join(save_dir, 'results.csv'), index=False)
        prog.progress((i+1)/len(files))

    st.session_state['master_df'] = pd.DataFrame(all_res_list)
    st.session_state['processed_names'] = [os.path.splitext(os.path.basename(f))[0] for f in files]
    output_base = os.path.abspath(st.session_state['output_folder'])
    st.session_state['master_df'].to_csv(os.path.join(output_base, 'Master_Results.csv'), index=False)
    # [FIX] Meta Analysis Call (Restored)
    perform_meta_analysis(all_res_list, output_base)
    st.success("✅ Analysis Done! Results & Meta_Analysis saved.")

# --- DASHBOARD ---
if 'master_df' in st.session_state:
    st.header("📊 Step 3: Meta-Analysis Results")
    m1, m2 = st.columns(2); pal = {"Healthy": "#1f77b4", "Damaged": "#d62728", "Unknown": "gray"}
    with m1:
        f_m1, a_m1 = plt.subplots(figsize=(8,5)); sns.boxplot(data=st.session_state['master_df'], x='Mode', y='True_Freq', hue='Condition', palette=pal, ax=a_m1); st.pyplot(f_m1)
    with m2:
        f_m2, a_m2 = plt.subplots(figsize=(8,5)); sns.boxplot(data=st.session_state['master_df'], x='Mode', y='MAC', hue='Condition', palette=pal, ax=a_m2); a_m2.axhline(0.9, ls='--', c='k'); st.pyplot(f_m2)
    st.divider(); st.header("📂 Step 4: Individual File Deep-Dive")
    sel_p = st.selectbox("Select file:", st.session_state['processed_names'])
    if sel_p:
        f_dir = os.path.join(os.path.abspath(st.session_state['output_folder']), sel_p)
        bc = st.columns(6)
        if bc[0].button("Fig 3"): st.session_state['individual_view'] = '3_spectrum.png'
        if bc[1].button("Fig 4"): st.session_state['individual_view'] = '4_decomp.png'
        if bc[2].button("Fig 5"): st.session_state['individual_view'] = '5_shapes.png'
        if bc[3].button("Fig 6"): st.session_state['individual_view'] = '6_mac_matrix.png'
        if bc[4].button("Fig 7"): st.session_state['individual_view'] = '7_correlation.png'
        if bc[5].button("Fig 8"): st.session_state['individual_view'] = '8_error_bar.png'
        if st.session_state['individual_view']: st.image(os.path.join(f_dir, st.session_state['individual_view']), width=900)
# Moniteur de latence et de bande passante en temps réel
# Dépendances : ping3, speedtest-cli (ou speedtest), PyQt5, pyqtgraph, requests

import sys
import builtins
import io
# Patch pour compatibilité Speedtest dans l'exécutable (import __builtin__ et fileno)
sys.modules['__builtin__'] = builtins
class _DevNull(io.TextIOBase):
    def fileno(self):
        return 0
# Si stdin/stdout n'ont pas fileno(), on les redirige vers _DevNull
if not hasattr(sys.stdin, 'fileno'):
    sys.stdin = _DevNull()
if not hasattr(sys.stdout, 'fileno'):
    sys.stdout = _DevNull()
import csv
import subprocess
import shutil
from datetime import datetime
from ping3 import ping
from speedtest import Speedtest
from speedtest import SpeedtestBestServerFailure
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import QTimer
import pyqtgraph as pg

LOG_FILE = "network_history.csv"

# Détection du binaire speedtest
CLI_NAME = None
for name in ("speedtest-cli", "speedtest"):
    if shutil.which(name):
        CLI_NAME = name
        break
if not CLI_NAME:
    print("Attention : aucun binaire 'speedtest-cli' ou 'speedtest' trouvé. Le test de débit CLI ne fonctionnera pas.")

class NetworkMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Moniteur de latence et bande passante")
        self.resize(900, 600)

        # Données historiques
        self.ping_timestamps = []
        self.latencies = []
        self.speed_timestamps = []
        self.downloads = []
        self.uploads = []

        # Widget central
        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # Indicateurs
        self.lbl_ping = QLabel("Ping : – ms")
        self.lbl_dl = QLabel("Download : – Mbps")
        self.lbl_ul = QLabel("Upload : – Mbps")
        self.lbl_status = QLabel("Statut : –")
        row = QHBoxLayout()
        row.addWidget(self.lbl_ping)
        row.addWidget(self.lbl_dl)
        row.addWidget(self.lbl_ul)
        row.addWidget(self.lbl_status)
        layout.addLayout(row)

        # Graphiques
        self.graph_ping = pg.PlotWidget(title="Latence (ms)")
        self.graph_dl = pg.PlotWidget(title="Download (Mbps)")
        self.graph_ul = pg.PlotWidget(title="Upload (Mbps)")
        for g in (self.graph_ping, self.graph_dl, self.graph_ul):
            g.showGrid(x=True, y=True)
            layout.addWidget(g)

        # Bouton nettoyage
        btn_clear = QPushButton("Effacer l'historique")
        btn_clear.clicked.connect(self.clear_history)
        layout.addWidget(btn_clear)

        # Timers
        self.timer_ping = QTimer(self)
        self.timer_ping.timeout.connect(self.perform_ping)
        self.timer_ping.start(5000)
        self.timer_speed = QTimer(self)
        self.timer_speed.timeout.connect(self.perform_speedtest)
        self.timer_speed.start(60000)

        # Initialisation CSV
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "ping_ms", "download_mbps", "upload_mbps"])

        # Lancer immédiatement une mesure
        self.perform_ping()
        self.perform_speedtest()

    def perform_ping(self):
        ts = datetime.now()
        try:
            delay = ping("8.8.8.8", unit="ms")
            if delay is None:
                raise Exception("Pas de réponse au ping")
            latency = round(delay, 2)
        except Exception as e:
            latency = None
            print(f"[{ts}] Erreur ping : {e}")

        self.ping_timestamps.append(ts)
        self.latencies.append(latency or 0)
        self.lbl_ping.setText(f"Ping : {latency or '–'} ms")
        self._update_plot(self.graph_ping, self.ping_timestamps, self.latencies)
        self._log_to_csv(ts, latency, None, None)
        self.update_status()

    def perform_speedtest(self):
        ts = datetime.now()
        dl = ul = None
        # 1) Test via bibliothèque Python speedtest
        try:
            st = Speedtest()
            st.get_best_server()
            dl = round(st.download() / 1e6, 2)
            ul = round(st.upload() / 1e6, 2)
        except Exception:
            pass

        # 2) Fallback CLI
        if (dl is None or ul is None) and CLI_NAME:
            try:
                out = subprocess.check_output([CLI_NAME, "--simple"], stderr=subprocess.STDOUT, timeout=30)
                text = out.decode('utf-8')
                for line in text.splitlines():
                    if line.startswith("Download:"):
                        dl = float(line.split()[1])
                    elif line.startswith("Upload:"):
                        ul = float(line.split()[1])
                dl = round(dl, 2) if dl is not None else None
                ul = round(ul, 2) if ul is not None else None
            except Exception:
                pass

        # 3) Fallback HTTP
        if dl is None:
            try:
                url = "http://speedtest.tele2.net/1MB.zip"
                start = datetime.now().timestamp()
                r = requests.get(url, stream=True, timeout=20)
                total = 0
                for chunk in r.iter_content(1024*64):
                    total += len(chunk)
                    if total >= 1024*1024:
                        break
                elapsed = datetime.now().timestamp() - start
                dl = round((total * 8 / 1e6) / elapsed, 2)
            except Exception:
                dl = None
        if ul is None:
            try:
                url = "https://httpbin.org/post"
                data = b"0" * (256 * 1024)
                start = datetime.now().timestamp()
                requests.post(url, data=data, timeout=20)
                elapsed = datetime.now().timestamp() - start
                ul = round((len(data) * 8 / 1e6) / elapsed, 2)
            except Exception:
                ul = None

        self.speed_timestamps.append(ts)
        self.downloads.append(dl or 0)
        self.uploads.append(ul or 0)
        self.lbl_dl.setText(f"Download : {dl or '–'} Mbps")
        self.lbl_ul.setText(f"Upload : {ul or '–'} Mbps")
        self._update_plot(self.graph_dl, self.speed_timestamps, self.downloads)
        self._update_plot(self.graph_ul, self.speed_timestamps, self.uploads)
        self._log_to_csv(ts, None, dl, ul)
        self.update_status()

    def update_status(self):
        ping_ok = bool(self.latencies and self.latencies[-1] > 0)
        if CLI_NAME:
            speed_ok = bool(self.downloads and self.uploads and self.downloads[-1] > 0 and self.uploads[-1] > 0)
        else:
            speed_ok = True
        if ping_ok and speed_ok:
            status, color = "✅ OK", "green"
        elif not ping_ok and not speed_ok:
            status, color = "❌ Ping & Débit HS", "red"
        elif not ping_ok:
            status, color = "⚠️ Ping HS", "red"
        else:
            status, color = "⚠️ Débit HS", "red"
        self.lbl_status.setText(f"Statut : {status}")
        self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold")

    def _update_plot(self, widget, x, y):
        """
        Met à jour le graphique en fonction de l'indice des points.
        """
        widget.clear()
        xs = list(range(len(y)))
        widget.plot(xs, y, pen=pg.mkPen(width=2))
        widget.getViewBox().autoRange()

    def clear_history(self):
        self.ping_timestamps.clear()
        self.latencies.clear()
        self.speed_timestamps.clear()
        self.downloads.clear()
        self.uploads.clear()
        for g in (self.graph_ping, self.graph_dl, self.graph_ul):
            g.clear()
        print("Historique effacé.")
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "ping_ms", "download_mbps", "upload_mbps"])
        self.lbl_status.setText("Statut : –")

    def _log_to_csv(self, ts, ping_ms, dl, ul):
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                ts.isoformat(sep=' '),
                ping_ms if ping_ms is not None else "",
                dl if dl is not None else "",
                ul if ul is not None else ""
            ])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    monitor = NetworkMonitor()
    monitor.show()
    sys.exit(app.exec_())
